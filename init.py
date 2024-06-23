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

	# Get the LOD level of a chunk based on its distance to the camera position
	def chunk_get_lod(self, pos: vec3):
		if data.settings.chunk_lod > 1:
			lod = pos.distance(self.pos) / (data.settings.dist_max / data.settings.chunk_lod)
			return min(1 + math.trunc(lod), data.settings.chunk_lod)
		return 1

	# Get a chunk's frame from the given global position
	def chunk_get(self, pos: vec3):
		pos_chunk = pos.snapped(data.settings.chunk_size, -1) + data.settings.chunk_radius
		post_chunk = pos_chunk.tuple()
		if post_chunk in self.chunks:
			return self.chunks[post_chunk]
		return None

	# Create a new frame with this voxel list or delete the chunk if empty
	def chunk_set(self, pos: vec3, voxels: dict, lod: int):
		post = pos.tuple()
		if voxels:
			self.chunks[post] = data.Frame(packed = True, lod = lod)
			self.chunks[post].set_voxels(voxels)
		elif post in self.chunks:
			del self.chunks[post]

	# Trace the pixel based on the given 2D direction which is used to calculate ray velocity from lens distorsion: X = -1 is left, X = +1 is right, Y = -1 is down, Y = +1 is up
	def trace(self, dir_x: float, dir_y: float, sample: int):
		# Randomly offset the ray's angle based on the DOF setting, fetch its direction and use it as the ray velocity
		# Velocity must be normalized as voxels need to be checked at all integer positions, the speed of light is always 1
		# Therefore at least one axis must be precisely -1 or +1 while others can be anything in that range, lower speeds are scaled accordingly based on the largest
		lens_x = (dir_x / data.settings.proportions) * self.lens + rand(data.settings.dof)
		lens_y = (dir_y * data.settings.proportions) * self.lens + rand(data.settings.dof)
		ray_rot = self.rot.rotate(vec3(0, -lens_y, +lens_x))
		ray_dir = ray_rot.dir(True).normalize()
		ray_detail = 1 - abs(dir_x * dir_y) * data.settings.lod_edge

		# Ray data is kept in a data store so it can be easily delivered to material functions and support custom properties
		ray = store(
			color = rgb(0, 0, 0),
			energy = 0,
			pos = self.pos + ray_dir * data.settings.dist_min,
			vel = ray_dir,
			step = 0,
			life = (data.settings.dist_max - data.settings.dist_min) * ray_detail,
			bounces = 0,
		)

		# Chunk data relevant to this ray, updated at the beginning of the ray processing cycle
		chunk = store(
			pos = vec3(0, 0, 0),
			mins = vec3(0, 0, 0),
			maxs = vec3(0, 0, 0),
			frame = None,
		)

		# Each step the ray advances through space by adding the velocity to its position, starting from the minimum distance and going until its lifetime runs out or it's stopped earlier
		# Chunk data is calculated first to reflect the chunk the ray is currently in, the active chunk is changed when the ray enters the area of another chunk
		# If a material is found, its function is called which can modify any of the ray properties, performance optimizations may terminate the ray sooner
		# Note that diagonal steps are allowed and the ray can penetrate 1 voxel thick corners, checking in a stair pattern isn't supported due to performance
		while ray.step < ray.life:
			if ray.pos.x < chunk.mins.x or ray.pos.y < chunk.mins.y or ray.pos.z < chunk.mins.z or ray.pos.x > chunk.maxs.x or ray.pos.y > chunk.maxs.y or ray.pos.z > chunk.maxs.z:
				chunk.mins = ray.pos.snapped(data.settings.chunk_size, -1)
				chunk.pos = chunk.mins + data.settings.chunk_radius
				chunk.maxs = chunk.pos + data.settings.chunk_radius
				post_chunk = chunk.pos.tuple()
				chunk.frame = self.chunks[post_chunk] if post_chunk in self.chunks else None

			if chunk.frame:
				pos = math.trunc(ray.pos - ray.pos.snapped(data.settings.chunk_size, -1))
				mat = chunk.frame.get_voxel(pos)
				if mat:
					# Call the material function and obtain the bounce amount, add it to the total number of bounces
					# Normalize ray velocity after any changes to ensure the speed of light remains 1 and voxels aren't skipped or calculated twice
					bounce = mat.function(ray, mat, data.settings)
					ray.life /= 1 + bounce * data.settings.lod_bounces
					ray.bounces += bounce
					ray.vel = ray.vel.normalize()

					# Enforce maximum ray properties and terminate the trace earlier to improve performance
					if ray.bounces >= data.settings.max_bounces + 1:
						break
					elif ray.energy >= data.settings.max_light:
						break

					# Reflect the velocity of the ray based on material IOR and the neighbors of this voxel which are used to determine face normals
					# A material considers its neighbors solid if they have the same IOR, otherwise they won't affect the direction of ray reflections
					# If IOR is above 0.5 check the neighbor opposite the ray direction in that axis, otherwise check the neighbor in the ray's direction
					# As neighboring voxels may be located in other chunks, try the local chunk first and fetch from another chunk if not found
					if mat.ior:
						direction = (mat.ior - 0.5) * 2
						ray_pos_x = ray.pos + vec3(1, 0, 0) if ray.vel.x * direction < 0 else ray.pos - vec3(1, 0, 0)
						ray_pos_y = ray.pos + vec3(0, 1, 0) if ray.vel.y * direction < 0 else ray.pos - vec3(0, 1, 0)
						ray_pos_z = ray.pos + vec3(0, 0, 1) if ray.vel.z * direction < 0 else ray.pos - vec3(0, 0, 1)
						pos_x = math.trunc(ray_pos_x - ray_pos_x.snapped(data.settings.chunk_size, -1))
						pos_y = math.trunc(ray_pos_y - ray_pos_y.snapped(data.settings.chunk_size, -1))
						pos_z = math.trunc(ray_pos_z - ray_pos_z.snapped(data.settings.chunk_size, -1))
						chunk_x = chunk.frame if ray_pos_x >= chunk.mins and ray_pos_x <= chunk.maxs else self.chunk_get(ray_pos_x)
						chunk_y = chunk.frame if ray_pos_y >= chunk.mins and ray_pos_y <= chunk.maxs else self.chunk_get(ray_pos_y)
						chunk_z = chunk.frame if ray_pos_z >= chunk.mins and ray_pos_z <= chunk.maxs else self.chunk_get(ray_pos_z)
						mat_x = chunk_x.get_voxel(pos_x) if chunk_x else None
						mat_y = chunk_y.get_voxel(pos_y) if chunk_y else None
						mat_z = chunk_z.get_voxel(pos_z) if chunk_z else None
						if not (mat_x and mat_x.ior == mat.ior):
							ray.vel.x = mix(+ray.vel.x, -ray.vel.x, mat.ior)
						if not (mat_y and mat_y.ior == mat.ior):
							ray.vel.y = mix(+ray.vel.y, -ray.vel.y, mat.ior)
						if not (mat_z and mat_z.ior == mat.ior):
							ray.vel.z = mix(+ray.vel.z, -ray.vel.z, mat.ior)

			# Advance the ray, move by frame LOD if inside a valid chunk or skip toward the safest possible distance to the nearest chunk if void
			step = chunk.frame.lod if chunk.frame else max(1, data.settings.chunk_radius - ray.pos.distance(chunk.pos))
			ray.step += step
			ray.pos += ray.vel * step

		# Run the background function and return the resulting color, fall back to black if a color wasn't set
		if data.background:
			data.background(ray, data.settings)
		return ray.color

	# Called by threads with a tile image to paint to, creates a new surface for this thread to paint to which is returned to the main thread as a byte string
	# If static noise is enabled, the random seed is set to an index unique to this pixel and sample so noise in ray calculations is static instead of flickering
	# The batch number decides which group of pixels should be rendered this call using a pattern generated from the 2D position of the pixel
	def tile(self, image: str, sample: int, thread: int, batch: int):
		tile = pg.image.frombytes(image, (data.settings.width, data.settings.tiles), "RGB")
		for x in range(data.settings.width):
			for y in range(data.settings.tiles):
				if (x ^ y) % data.settings.batches == batch:
					line_y = y + (data.settings.tiles * thread)
					dir_x = -1 + (x / data.settings.width) * 2
					dir_y = -1 + (line_y / data.settings.height) * 2

					if data.settings.static:
						random.seed((1 + x) * (1 + line_y) * (1 + sample))
					tile.set_at((x, y), self.trace(dir_x, dir_y, sample).tuple())
					random.seed(None)

		return (pg.image.tobytes(tile, "RGB"), sample, thread)

	# Update the position and rotation this camera will shoot rays from followed by chunk frames
	def update(self, cam_pos: vec3, cam_rot: vec3):
		self.pos = cam_pos
		self.rot = cam_rot

		# Scan existing chunks and check if their LOD changed, force recalculation if so
		for post, frame in self.chunks.items():
			pos = vec3(post[0], post[1], post[2])
			if not pos in data.objects_chunks_update and self.chunk_get_lod(pos) != frame.lod:
				data.objects_chunks_update.append(pos)

		# Compile a new voxel list for chunks that need to be redrawn, add intersecting voxels for every object touching this chunk
		for pos_center in data.objects_chunks_update:
			pos_min = pos_center - data.settings.chunk_radius
			pos_max = pos_center + data.settings.chunk_radius
			lod = self.chunk_get_lod(pos_center)
			voxels = {}
			for obj in data.objects:
				if obj.visible and obj.intersects(pos_min, pos_max):
					spr = obj.get_sprite()
					for x in range(pos_min.x, pos_max.x, lod):
						for y in range(pos_min.y, pos_max.y, lod):
							for z in range(pos_min.z, pos_max.z, lod):
								pos = vec3(x, y, z)
								if obj.intersects(pos, pos):
									mat = spr.get_voxel(None, pos - obj.mins)
									if mat:
										pos_chunk = pos - pos_min
										post_chunk = pos_chunk.tuple()
										voxels[post_chunk] = mat
			self.chunk_set(pos_center, voxels, lod)
		data.objects_chunks_update = []

# Window: Initializes Pygame and starts the main loop, handles all updates and redraws the canvas using a Camera instance
class Window:
	def __init__(self):
		# Configure Pygame and the main screen as well as the camera and thread pool that will be used to update the window
		pg.init()
		pg.display.set_caption("Voxel Tracer")
		self.rect = vec2(data.settings.width, data.settings.height)
		self.rect_win = self.rect * data.settings.scale
		self.screen = pg.display.set_mode(self.rect_win.tuple(), pg.HWSURFACE)
		self.canvas = pg.Surface(self.rect.tuple(), pg.HWSURFACE)
		self.font = pg.font.SysFont(None, 24)
		self.clock = pg.time.Clock()
		self.pool = mp.Pool(processes = data.settings.threads)
		self.cam = Camera()
		self.mouselook = True
		self.running = True

		# Prepare the containers for samples and batches, each sample stores an image slot for every thread which is cleared after being drawn
		self.tiles = []
		self.batches = []
		for s in range(data.settings.samples):
			self.tiles.append([])
			self.batches.append([])
			for t in range(data.settings.threads):
				surface = pg.Surface((data.settings.width, data.settings.tiles), pg.HWSURFACE)
				image = pg.image.tobytes(surface, "RGB")
				self.tiles[s].append(image)
				self.batches[s].append(0)

		# Main loop, limited by FPS with a slower clock when the window isn't focused
		while self.running:
			fps = data.settings.fps if pg.mouse.get_focused() else math.trunc(data.settings.fps / 5)
			self.clock.tick(fps)
			self.update()
			if not self.running:
				self.pool.close()
				self.pool.join()
				exit

	# Called by the thread pool on finish, adds the image to the appropriate sample and thread for the main thread to mix
	def draw_tile(self, result):
		image, sample, thread = result
		self.tiles[sample][thread] = image
		self.batches[sample][thread] = (self.batches[sample][thread] + 1) % data.settings.batches

	# Request the camera to draw a new tile for each thread and sample
	def draw(self):
		# If sync is enabled, skip updates until all samples and tiles have finished
		if data.settings.sync:
			for sample in self.tiles:
				for tile in sample:
					if not tile:
						return

		# Add available tiles to their corresponding sample, blit valid samples to the canvas with performance information on top
		samples = []
		for s in range(len(self.tiles)):
			tiles = []
			for t in range(len(self.tiles[s])):
				if self.tiles[s][t]:
					tile = pg.image.frombytes(self.tiles[s][t], (data.settings.width, data.settings.tiles), "RGB")
					tiles.append((tile, (0, t * data.settings.tiles)))
					self.pool.apply_async(self.cam.tile, args = (self.tiles[s][t], s, t, self.batches[s][t]), callback = self.draw_tile)
					self.tiles[s][t] = None
			if tiles:
				sample = pg.Surface.copy(self.canvas)
				sample.blits(tiles)
				samples.append(sample)
		if samples:
			self.canvas = pg.transform.average_surfaces(samples)
			canvas = pg.transform.smoothscale(self.canvas, self.rect_win.tuple()) if data.settings.smooth else pg.transform.scale(self.canvas, self.rect_win.tuple())
			text_info = str(data.settings.width) + " x " + str(data.settings.height) + " (" + str(data.settings.width * data.settings.height) + "px) - " + str(math.trunc(self.clock.get_fps())) + " / " + str(data.settings.fps) + " FPS"
			text = self.font.render(text_info, True, (255, 255, 255))
			self.screen.blit(canvas, (0, 0))
			self.screen.blit(text, (0, 0))

	# Handle keyboard and mouse input, apply object movement for the camera controlled object
	def input(self, obj_cam: data.Object):
		keys = pg.key.get_pressed()
		mods = pg.key.get_mods()
		time = self.clock.get_time() / 1000
		units = time * data.settings.speed_move
		units_jump = time * data.settings.speed_jump
		units_mouse = time * data.settings.speed_mouse
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
				obj_cam.impulse(vec3(+d.z, 0, -d.x) * e.x * 5)
				obj_cam.impulse(vec3(+d.x, +d.y, +d.z) * e.y * 5)
			if e.type == pg.MOUSEMOTION and self.mouselook:
				center = self.rect_win / 2
				x, y = pg.mouse.get_pos()
				ofs = vec2(center.x - x, center.y - y)
				rot = vec3(0, +ofs.y, -ofs.x)
				obj_cam.rotate(rot * units_mouse, data.settings.max_pitch)
				pg.mouse.set_pos((center.x, center.y))

		# Ongoing events: Camera movement, camera rotation
		if keys[pg.K_w]:
			obj_cam.impulse(vec3(+d.x, +d.y, +d.z) * dh * units)
		if keys[pg.K_s]:
			obj_cam.impulse(vec3(-d.x, -d.y, -d.z) * dh * units)
		if keys[pg.K_a]:
			obj_cam.impulse(vec3(-d.z, 0, +d.x) * dh * units)
		if keys[pg.K_d]:
			obj_cam.impulse(vec3(+d.z, 0, -d.x) * dh * units)
		if keys[pg.K_r] or keys[pg.K_SPACE]:
			obj_cam.impulse(vec3(0, +1, 0) * dv * units_jump)
		if keys[pg.K_f] or keys[pg.K_LCTRL]:
			obj_cam.impulse(vec3(0, -1, 0) * dv * units_jump)
		if keys[pg.K_UP]:
			obj_cam.rotate(vec3(0, +5, 0) * units, data.settings.max_pitch)
		if keys[pg.K_DOWN]:
			obj_cam.rotate(vec3(0, -5, 0) * units, data.settings.max_pitch)
		if keys[pg.K_LEFT]:
			obj_cam.rotate(vec3(0, 0, -5) * units, data.settings.max_pitch)
		if keys[pg.K_RIGHT]:
			obj_cam.rotate(vec3(0, 0, +5) * units, data.settings.max_pitch)

	# Main loop of the Pygame window, trigger draw calls apply input and execute the update function of objects in the scene
	def update(self):
		obj_cam = None
		for obj_cam in data.objects:
			if obj_cam.cam_pos:
				break
		if not obj_cam or not obj_cam.cam_pos:
			print("Error: No camera object found, define at least one object with a camera in the scene.")
			self.running = False
			return

		for obj in data.objects:
			obj.update(self.cam.pos)

		d = obj_cam.rot.dir(False)
		self.cam.update(obj_cam.pos + vec3(obj_cam.cam_pos.x * d.x, obj_cam.cam_pos.y, obj_cam.cam_pos.x * d.z), obj_cam.rot)
		self.input(obj_cam)
		self.draw()
		pg.display.update()
		pg.mouse.set_visible(not self.mouselook)

# Create the main window and start Pygame
Window()
