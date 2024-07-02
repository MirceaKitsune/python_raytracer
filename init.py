#!/usr/bin/python3
from lib import *

import multiprocessing as mp
import pygame as pg
import math
import random

import data

# Camera: A subset of Window which only stores data needed for rendering and is used by threads, preforms ray tracing and draws tiles which are overlayed to the canvas by the main thread
class Camera:
	def __init__(self):
		self.pos = vec3(0, 0, 0)
		self.rot = vec3(0, 0, 0)
		self.lens = data.settings.fov * math.pi / 8
		self.chunks = {}

	# Get the frame of the chunk touching the given position
	def chunk_get(self, pos: vec3):
		pos_chunk = pos.snapped(data.settings.chunk_size, -1) + data.settings.chunk_radius
		post_chunk = pos_chunk.tuple()
		if post_chunk in self.chunks:
			return self.chunks[post_chunk]
		return None

	# Assign valid chunks based on the positions traversed by rays during the previous trace, enforces occlusion culling and view frustum culling
	def chunk_assign(self, chunks: dict, traversed: list):
		self.chunks = {}
		for post in chunks:
			if not data.settings.culling or post in traversed:
				self.chunks[post] = chunks[post]

	# Trace the pixel based on the given 2D direction which is used to calculate ray velocity from lens distorsion: X = -1 is left, X = +1 is right, Y = -1 is down, Y = +1 is up
	# Returns the ray data after processing is over, the result represents the ray state during the last step it has preformed
	def trace(self, dir_x: float, dir_y: float, detail: float):
		# Randomly offset the ray's angle based on the DOF setting, fetch its direction and use it as the ray velocity
		# Velocity must be normalized as voxels need to be checked at all integer positions, the speed of light is always 1
		# Therefore at least one axis must be precisely -1 or +1 while others can be anything in that range, lower speeds are scaled accordingly based on the largest
		lens_x = (dir_x / data.settings.proportions) * self.lens + rand(data.settings.dof)
		lens_y = (dir_y * data.settings.proportions) * self.lens + rand(data.settings.dof)
		ray_rot = self.rot.rotate(vec3(0, -lens_x, -lens_y))
		ray_dir = ray_rot.dir(True).normalize()
		chunk_pos = chunk_min = chunk_max = vec3(0, 0, 0)
		chunk = None

		# Ray data is kept in a data store so it can be easily delivered to material functions and support custom properties
		ray = store(
			color = rgb(0, 0, 0),
			energy = 0,
			pos = self.pos + ray_dir * data.settings.dist_min,
			vel = ray_dir,
			step = 0,
			life = (data.settings.dist_max - data.settings.dist_min) * detail,
			bounces = 0,
			traversed = [],
		)

		# Each step the ray advances through space by adding the velocity to its position, starting from the minimum distance and going until its lifetime runs out or it's stopped earlier
		# Chunk data is calculated first to reflect the chunk the ray is currently in, the active chunk is changed when the ray enters the area of another chunk
		# If a material is found, its function is called which can modify any of the ray properties, performance optimizations may terminate the ray sooner
		# Note that diagonal steps are allowed and the ray can penetrate 1 voxel thick corners, checking in a stair pattern isn't supported due to performance
		# The ray also returns the positions of chunks it traveled through which is used for occlusion culling
		while ray.step < ray.life:
			if not ray.pos >= chunk_min or not ray.pos <= chunk_max:
				chunk_min = ray.pos.snapped(data.settings.chunk_size, -1)
				chunk_pos = chunk_min + data.settings.chunk_radius
				chunk_max = chunk_pos + data.settings.chunk_radius
				post_chunk = chunk_pos.tuple()
				chunk = self.chunks[post_chunk] if post_chunk in self.chunks else None
				if not post_chunk in ray.traversed:
					ray.traversed.append(post_chunk)

			if chunk:
				pos = math.trunc(ray.pos - ray.pos.snapped(data.settings.chunk_size, -1))
				mat = chunk.get_voxel(pos)
				if mat:
					# Call the material function and obtain the bounce amount, add it to the total number of bounces
					# Normalize ray velocity after any changes to ensure the speed of light remains 1 and voxels aren't skipped or calculated twice
					bounce = mat.function(ray, mat, data.settings)
					ray.bounces += bounce
					ray.life /= 1 + bounce * data.settings.lod_bounces
					ray.vel = ray.vel.normalize()
					if ray.step >= ray.life or ray.energy >= data.settings.max_light or ray.bounces >= data.settings.max_bounces + 1:
						break

					# Reflect the velocity of the ray based on material IOR and the neighbors of this voxel which are used to determine face normals
					# A material considers its neighbors solid if they have the same IOR, otherwise they won't affect the direction of ray reflections
					# If IOR is above 0.5 check the neighbor opposite the ray direction in that axis, otherwise check the neighbor in the ray's direction
					# As neighboring voxels may be located in other chunks, try the local chunk first and fetch from another chunk if not found
					if mat.ior:
						direction = (mat.ior - 0.5) * 2
						ray_pos_x = ray.pos + vec3(1, 0, 0) if ray.vel.x < direction else ray.pos - vec3(1, 0, 0)
						ray_pos_y = ray.pos + vec3(0, 1, 0) if ray.vel.y < direction else ray.pos - vec3(0, 1, 0)
						ray_pos_z = ray.pos + vec3(0, 0, 1) if ray.vel.z < direction else ray.pos - vec3(0, 0, 1)
						pos_x = math.trunc(ray_pos_x - ray_pos_x.snapped(data.settings.chunk_size, -1))
						pos_y = math.trunc(ray_pos_y - ray_pos_y.snapped(data.settings.chunk_size, -1))
						pos_z = math.trunc(ray_pos_z - ray_pos_z.snapped(data.settings.chunk_size, -1))
						chunk_x = chunk if ray_pos_x >= chunk_min and ray_pos_x <= chunk_max else self.chunk_get(ray_pos_x)
						chunk_y = chunk if ray_pos_y >= chunk_min and ray_pos_y <= chunk_max else self.chunk_get(ray_pos_y)
						chunk_z = chunk if ray_pos_z >= chunk_min and ray_pos_z <= chunk_max else self.chunk_get(ray_pos_z)
						mat_x = chunk_x.get_voxel(pos_x) if chunk_x else None
						mat_y = chunk_y.get_voxel(pos_y) if chunk_y else None
						mat_z = chunk_z.get_voxel(pos_z) if chunk_z else None
						if not mat_x or mat_x.ior != mat.ior:
							ray.vel.x -= ray.vel.x * mat.ior * 2
						if not mat_y or mat_y.ior != mat.ior:
							ray.vel.y -= ray.vel.y * mat.ior * 2
						if not mat_z or mat_z.ior != mat.ior:
							ray.vel.z -= ray.vel.z * mat.ior * 2

			# Advance the ray, move by frame LOD if inside a valid chunk or 1 unit if void
			step = chunk.lod if chunk else 1
			ray.step += step
			ray.pos += ray.vel * step

		# Run the background function and return the ray data
		if data.background:
			data.background(ray, data.settings)
		return ray

	# Called by threads with a tile image to paint to, creates a new surface for this thread to paint to which is returned to the main thread as a byte string
	# If static noise is enabled, the random seed is set to an index unique to this pixel and sample so noise in ray calculations is static instead of flickering
	# The batch number decides which group of pixels should be rendered this call using a pattern generated from the 2D position of the pixel
	# The alpha channel is used for motion blur, ray energy is translated to transparency which simulates a shutter making bright pixels stronger
	def tile(self, image: str, thread: int, batch: int):
		tile = pg.image.frombytes(image, data.settings.tile_size, "RGBA")
		traversed = []
		box = data.settings.tile[thread]
		for x in range(box[0], box[2]):
			for y in range(box[1], box[3]):
				if (x ^ y) % data.settings.batches == batch:
					colors = []
					dir_x = -1 + (x / data.settings.width) * 2
					dir_y = -1 + (y / data.settings.height) * 2
					detail = 1 - abs(dir_x * dir_y) * data.settings.lod_edge
					samples = max(1, round(data.settings.samples * detail))
					for sample in range(samples):
						if data.settings.static:
							random.seed((1 + x) * (1 + y) * (1 + sample))

						ray = self.trace(dir_x, dir_y, detail / (1 + sample * data.settings.lod_samples))
						alpha = round(min(1, ray.energy + data.settings.shutter) * 255)
						colors.append(ray.color.array() + [alpha])
						traversed = merge(traversed, ray.traversed)

					color = average(colors)
					tile.set_at((x - box[0], y - box[1]), (color[0], color[1], color[2], color[3]))
					random.seed(None)

		return pg.image.tobytes(tile, "RGBA"), traversed, thread

# Window: Initializes Pygame and starts the main loop, handles all updates and redraws the canvas using a Camera instance
class Window:
	def __init__(self):
		# Configure Pygame and the main screen as well as the camera and thread pool that will be used to update the window
		pg.init()
		pg.display.set_caption("Voxel Tracer")
		self.box = vec2(data.settings.width, data.settings.height)
		self.box_win = self.box * data.settings.scale
		self.screen = pg.display.set_mode(self.box_win.tuple())
		self.canvas = pg.Surface(self.box.tuple(), pg.SRCALPHA)
		self.font = pg.font.SysFont(None, 24)
		self.clock = pg.time.Clock()
		self.pool = mp.Pool(processes = data.settings.threads)
		self.cam = Camera()
		self.chunks = {}
		self.timer = 0
		self.iris = self.iris_target = 0
		self.mouselook = True
		self.running = True

		# Containers for items indexed by thread number
		surface = pg.Surface(data.settings.tile_size, pg.SRCALPHA)
		image = pg.image.tobytes(surface, "RGBA")
		self.tiles = [image] * data.settings.threads
		self.traversed = [[]] * data.settings.threads
		self.batches = [0] * data.settings.threads

		# Main loop limited by FPS
		while self.running:
			self.clock.tick(data.settings.fps)
			self.update()
			if not self.running:
				self.pool.close()
				self.pool.join()
				exit

	# Called by the thread pool on finish, adds the image to the appropriate thread for the main thread to mix
	def draw_tile(self, result):
		tile, traversed, thread = result
		self.tiles[thread] = tile
		self.traversed[thread] = traversed
		self.batches[thread] = (self.batches[thread] + 1) % data.settings.batches

	# Request the camera to draw a new tile for each thread
	def draw(self):
		# If sync is enabled, skip updates until all tiles have finished
		if data.settings.sync:
			for tile in self.tiles:
				if not tile:
					return

		# Add available tiles to the canvas with performance information on top
		tiles = []
		for t in range(len(self.tiles)):
			if self.tiles[t]:
				box = data.settings.tile[t]
				tile = pg.image.frombytes(self.tiles[t], data.settings.tile_size, "RGBA")
				tiles.append((tile, (box[0], box[1])))
				self.pool.apply_async(self.cam.tile, args = (self.tiles[t], t, self.batches[t]), callback = self.draw_tile)
				self.tiles[t] = None
		if tiles:
			self.canvas.blits(tiles)
			canvas = pg.Surface.copy(self.canvas)
			color = pg.transform.average_color(canvas, consider_alpha = True)

			# Color spill: Multiply the canvas with its average color
			if data.settings.spill:
				fac = 255 - round(data.settings.spill * 255)
				color_tint = (min(255, color[0] + fac), min(255, color[1] + fac), min(255, color[2] + fac), min(255, color[3] + fac))
				canvas.fill(color_tint, special_flags = pg.BLEND_RGBA_MULT)

			# Iris adaptation: Brighten or darken the canvas in contrast to its luminosity, a grayscale copy is added or subtracted, the mask is inverted based on the operation
			if data.settings.iris and data.settings.iris_time:
				col = 0 if self.iris > 0 else 255
				mod = pg.BLEND_RGBA_ADD if self.iris > 0 else pg.BLEND_RGBA_SUB
				fac = round(abs(self.iris * 255))
				canvas_gray = pg.transform.grayscale(canvas)
				canvas_mask = pg.Surface(self.box.tuple(), pg.SRCALPHA)
				canvas_mask.fill((col, col, col, col), special_flags = 0)
				canvas_mask.blit(canvas_gray, (0, 0), special_flags = mod)
				canvas_mask.fill((fac, fac, fac, fac), special_flags = pg.BLEND_RGBA_MULT)
				canvas.blit(canvas_mask, (0, 0), special_flags = mod)
				self.iris_target = 1 - (max(color[0], color[1], color[2]) / 255) * 2

			# Bloom: Duplicate the canvas, darken the copy to adjust intensity, downscale then upscale to blur, lighten the canvas with the result
			if data.settings.bloom and data.settings.bloom_blur:
				box = round(self.box / max(1, data.settings.bloom_blur))
				fac = round((1 - data.settings.bloom) * 255)
				canvas_blur = pg.Surface.copy(canvas)
				canvas_blur.fill((fac, fac, fac), special_flags = pg.BLEND_RGBA_SUB)
				canvas_blur = pg.transform.smoothscale(canvas_blur, box.tuple())
				canvas_blur = pg.transform.smoothscale(canvas_blur, self.box.tuple())
				canvas.blit(canvas_blur, (0, 0), special_flags = pg.BLEND_RGBA_ADD)

			canvas = pg.transform.smoothscale(canvas, self.box_win.tuple()) if data.settings.smooth else pg.transform.scale(canvas, self.box_win.tuple())
			text_info = str(data.settings.width) + " x " + str(data.settings.height) + " (" + str(data.settings.width * data.settings.height) + "px) - " + str(math.trunc(self.clock.get_fps())) + " / " + str(data.settings.fps) + " FPS"
			text = self.font.render(text_info, True, (255, 255, 255))
			self.screen.blit(canvas, (0, 0))
			self.screen.blit(text, (0, 0))
			pg.display.flip()

	# Handle keyboard and mouse input, apply object movement for the camera controlled object
	def input(self, obj_cam: data.Object, time: float):
		keys = pg.key.get_pressed()
		mods = pg.key.get_mods()
		units = data.settings.speed_move * time
		units_jump = data.settings.speed_jump / (1 + time)
		units_mouse = data.settings.speed_mouse / (1 + time * 1000)
		d = obj_cam.rot.dir(False)
		dh = vec3(1, 0, 1) if data.settings.max_pitch else vec3(1, 1, 1)
		dv = vec3(0, 1, 0) if data.settings.max_pitch else vec3(1, 1, 1)

		# Mods: Acceleration
		if mods & pg.KMOD_SHIFT:
			units *= 5

		# One time events: Quit, request quit or toggle mouselook, mouse wheel movement, mouse motion
		for e in pg.event.get():
			if e.type == pg.QUIT:
				self.running = False
				return
			if e.type == pg.KEYDOWN:
				if e.key == pg.K_ESCAPE:
					self.running = False
					return
				if e.key == pg.K_TAB:
					self.mouselook = not self.mouselook
			if e.type == pg.MOUSEWHEEL:
				self.cam.lens = max(math.pi, min(math.pi * 48, self.cam.lens - e.y * 10))
			if e.type == pg.MOUSEMOTION and self.mouselook:
				center = self.box_win / 2
				x, y = pg.mouse.get_pos()
				ofs = vec2(center.x - x, center.y - y)
				rot = vec3(0, ofs.x, ofs.y)
				obj_cam.rotate(rot * units_mouse, data.settings.max_pitch)
				pg.mouse.set_pos((center.x, center.y))

		# Ongoing events: Camera movement, camera rotation
		if keys[pg.K_w]:
			obj_cam.impulse(vec3(+d.x, +d.y, +d.z) * dh * units)
		if keys[pg.K_s]:
			obj_cam.impulse(vec3(-d.x, -d.y, -d.z) * dh * units)
		if keys[pg.K_a]:
			obj_cam.impulse(vec3(+d.z, 0, -d.x) * dh * units)
		if keys[pg.K_d]:
			obj_cam.impulse(vec3(-d.z, 0, +d.x) * dh * units)
		if keys[pg.K_r] or keys[pg.K_SPACE]:
			obj_cam.impulse(vec3(0, +1, 0) * dv * units_jump)
		if keys[pg.K_f] or keys[pg.K_LCTRL]:
			obj_cam.impulse(vec3(0, -1, 0) * dv * units_jump)
		if keys[pg.K_UP]:
			obj_cam.rotate(vec3(0, 0, +5) * units, data.settings.max_pitch)
		if keys[pg.K_DOWN]:
			obj_cam.rotate(vec3(0, 0, -5) * units, data.settings.max_pitch)
		if keys[pg.K_LEFT]:
			obj_cam.rotate(vec3(0, +5, 0) * units, data.settings.max_pitch)
		if keys[pg.K_RIGHT]:
			obj_cam.rotate(vec3(0, -5, 0) * units, data.settings.max_pitch)

	# Get the LOD level of a chunk based on its distance to the camera position
	def chunk_lod(self, pos: vec3):
		if data.settings.chunk_lod > 1:
			lod = pos.distance(self.cam.pos) / (data.settings.dist_max / data.settings.chunk_lod)
			return min(1 + math.trunc(lod), data.settings.chunk_lod)
		return 1

	# Create a new frame with this voxel list or delete the chunk if empty
	def chunk_set(self, pos: vec3, voxels: dict, lod: int):
		post = pos.tuple()
		if voxels:
			self.chunks[post] = data.Frame(packed = True, lod = lod)
			self.chunks[post].set_voxels(voxels)
		elif post in self.chunks:
			del self.chunks[post]

	# Compile a new list of chunks to be used by the renderer, chunks are only recalculated based on the update timer
	def chunk_update(self, time: float):
		self.timer += time
		if self.timer >= data.settings.chunk_time:
			self.timer -= max(data.settings.chunk_time, time)

			# Scan existing chunks and check if their LOD changed, force recalculation if so
			for post, frame in self.chunks.items():
				pos = vec3(post[0], post[1], post[2])
				if not pos in data.objects_chunks_update and self.chunk_lod(pos) != frame.lod:
					data.objects_chunks_update.append(pos)

			# Compile a new voxel list for chunks that need to be redrawn, add intersecting voxels for every object touching this chunk
			for pos_center in data.objects_chunks_update:
				pos_min = pos_center - data.settings.chunk_radius
				pos_max = pos_center + data.settings.chunk_radius
				lod = self.chunk_lod(pos_center)
				voxels = {}
				for obj in data.objects:
					if obj.visible and obj.intersects(pos_min, pos_max):
						spr = obj.get_sprite()
						for x in range(pos_min.x, pos_max.x, lod):
							for y in range(pos_min.y, pos_max.y, lod):
								for z in range(pos_min.z, pos_max.z, lod):
									pos = vec3(x, y, z)
									if obj.intersects(pos, pos):
										mat = spr.get_voxel(None, pos - obj.mins, obj.rot)
										if mat:
											pos_chunk = pos - pos_min
											post_chunk = pos_chunk.tuple()
											voxels[post_chunk] = mat
				self.chunk_set(pos_center, voxels, lod)
			data.objects_chunks_update = []
		self.cam.chunk_assign(self.chunks, unpack(self.traversed))

	# Main loop of the Pygame window, apply input then execute the update functions of objects in the scene and request redrawing when the window is focused
	def update(self):
		obj_cam = None
		for obj_cam in data.objects:
			if obj_cam.cam_pos:
				break
		if not obj_cam or not obj_cam.cam_pos:
			print("Error: No camera object found, define at least one object with a camera in the scene.")
			self.running = False
			return

		time = self.clock.get_time() / 1000
		self.input(obj_cam, time)
		for obj in data.objects:
			obj.update(self.cam.pos)

		if pg.mouse.get_focused():
			d = obj_cam.rot.dir(False)
			self.iris = mix(self.iris, self.iris_target * data.settings.iris, data.settings.iris_time * time)
			self.cam.pos = obj_cam.pos + vec3(obj_cam.cam_pos.x * d.x, obj_cam.cam_pos.y, obj_cam.cam_pos.x * d.z)
			self.cam.rot = obj_cam.rot
			self.chunk_update(time)
			self.draw()
			pg.mouse.set_visible(not self.mouselook)

# Create the main window and start Pygame
Window()
