#!/usr/bin/python3
from lib import *

import multiprocessing as mp
import pygame as pg
import math
import random

import data

# Camera: A subset of Window which only stores data needed for rendering and is used by threads, preforms ray tracing and draws tiles which are overlayed to the canvas by the main thread
# Camera rotation is stored as quaternion rather than euler to facilitate rolling and calculating the perspective of light rays
class Camera:
	def __init__(self):
		self.pos = vec3(0, 0, 0)
		self.rot = quaternion(0, 0, 0, 0)
		self.lens = data.settings.fov * math.pi / 8
		self.chunks = {}

	# Clear all chunks from the camera
	def chunk_clear(self):
		self.chunks = {}

	# Add a new chunk frame to the camera at this position
	def chunk_set(self, post: tuple, chunk: data.Frame):
		self.chunks[post] = chunk

	# Get the frame of the chunk touched by this position if one exists
	def chunk_get(self, pos: vec3):
		pos_chunk = pos.snapped(data.settings.chunk_size)
		post_chunk = pos_chunk.tuple()
		if post_chunk in self.chunks:
			return self.chunks[post_chunk]
		return None

	# Trace the pixel based on the given 2D direction which is used to calculate ray velocity from lens distorsion: X = -1 is left, X = +1 is right, Y = -1 is down, Y = +1 is up
	# Returns the ray data after processing is over, the result represents the ray state during the last step it has preformed
	def trace(self, dir_x: float, dir_y: float, detail: float):
		# Randomly offset the ray's angle based on the DOF setting, fetch its direction and use it as the ray velocity
		# Velocity must be normalized as voxels need to be checked at all integer positions, the speed of light is always 1
		# Therefore at least one axis must be precisely -1 or +1 while others can be anything in that range, lower speeds are scaled accordingly based on the largest
		lens_x = (dir_x / data.settings.proportions) * self.lens + rand(data.settings.dof)
		lens_y = (dir_y * data.settings.proportions) * self.lens + rand(data.settings.dof)
		lens = vec3(0, -lens_x, +lens_y)
		ray_rot = self.rot.multiply(lens.quaternion())
		ray_dir = ray_rot.vec_forward()
		chunk_min = chunk_max = vec3(0, 0, 0)
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
			if ray.pos.x < chunk_min.x or ray.pos.y < chunk_min.y or ray.pos.z < chunk_min.z or ray.pos.x > chunk_max.x or ray.pos.y > chunk_max.y or ray.pos.z > chunk_max.z:
				chunk_min = ray.pos.snapped(data.settings.chunk_size)
				chunk_max = chunk_min + data.settings.chunk_size
				post_chunk = chunk_min.tuple()
				chunk = self.chunks[post_chunk] if post_chunk in self.chunks else None
				if not post_chunk in ray.traversed:
					ray.traversed.append(post_chunk)

			if chunk:
				pos = math.trunc(ray.pos - ray.pos.snapped(data.settings.chunk_size))
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
						pos_x = math.trunc(ray_pos_x - ray_pos_x.snapped(data.settings.chunk_size))
						pos_y = math.trunc(ray_pos_y - ray_pos_y.snapped(data.settings.chunk_size))
						pos_z = math.trunc(ray_pos_z - ray_pos_z.snapped(data.settings.chunk_size))
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

			# Advance the ray, move by frame LOD if inside a valid chunk or skip toward the safest possible distance to the nearest chunk if void
			step = chunk.lod if chunk else 1 + abs(data.settings.chunk_radius - (ray.pos.mins() + data.settings.chunk_radius) % data.settings.chunk_size)
			ray.step += step
			ray.pos += ray.vel * step

		# Run the background function and return the ray data
		if data.background:
			data.background(ray, data.settings)
		return ray

	# Called by threads with a tile image to paint to, creates a new surface for this thread to paint to which is returned to the main thread as a byte string
	# If static noise is enabled, the random seed is set to an index unique to this pixel and sample so noise in ray calculations is static instead of flickering
	# The alpha channel is used for motion blur, ray energy is translated to transparency which simulates a shutter making bright pixels stronger
	def tile(self, thread: int, t: int):
		surface = pg.Surface(data.settings.window, pg.SRCALPHA)
		traversed = []
		for x, y in data.settings.pixels[thread]:
			colors = []
			dir_x = -1 + (x / data.settings.width) * 2
			dir_y = -1 + (y / data.settings.height) * 2
			detail = 1 - abs(dir_x * dir_y) * data.settings.lod_edge
			samples = max(1, round(data.settings.samples * detail))
			for sample in range(samples):
				if data.settings.static:
					random.seed((1 + x) * (1 + y) * (1 + sample))

				ray_detail = detail / (1 + sample * data.settings.lod_samples) * (1 - data.settings.lod_random * random.random())
				ray = self.trace(dir_x, dir_y, ray_detail)
				alpha = round(min(1, ray.energy + data.settings.shutter) * 255)
				colors.append(ray.color.array() + [alpha])
				traversed = merge(traversed, ray.traversed)

			color = average(colors)
			surface.set_at((x, y), (color[0], color[1], color[2], color[3]))
			random.seed(None)

		image = pg.image.tobytes(surface, "RGBA")
		return image, traversed, thread

# Window: Initializes Pygame and starts the main loop, handles all updates and redraws the canvas using a Camera instance
class Window:
	def __init__(self):
		# Configure Pygame and the main screen as well as the camera and thread pool that will be used to update the window
		pg.init()
		pg.display.set_caption("Voxel Tracer")
		self.screen = pg.display.set_mode(data.settings.window_scaled)
		self.canvas = pg.Surface(data.settings.window, pg.SRCALPHA)
		self.font = pg.font.SysFont(None, 24)
		self.clock = pg.time.Clock()
		self.pool = mp.Pool(data.settings.threads)
		self.cam = Camera()
		self.chunks = {}
		self.timer = 0
		self.iris = self.iris_target = 0
		self.mouselook = True
		self.running = True
		self.input_vel = vec3(0, 0, 0)
		self.input_rot = vec3(0, 0, 0)
		self.busy = [False] * data.settings.threads
		self.traversed = [[]] * data.settings.threads

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
		image, traversed, thread = result
		surface = pg.image.frombytes(image, data.settings.window, "RGBA")
		self.canvas.blit(surface, (0, 0))
		self.traversed[thread] = traversed
		self.busy[thread] = False

	# Request the camera to draw a new tile for each thread
	def draw(self):
		# If sync is enabled, skip updates until all tiles have finished
		if data.settings.sync:
			for t in range(len(self.busy)):
				if self.busy[t]:
					return

		# Start render threads that aren't busy
		for t in range(len(self.busy)):
			if not self.busy[t]:
				self.busy[t] = True
				self.pool.apply_async(self.cam.tile, args = (t, 0), callback = self.draw_tile)

		# Color spill: Multiply the canvas with its average color
		canvas = pg.Surface.copy(self.canvas)
		color = pg.transform.average_color(canvas, consider_alpha = True)
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
			canvas_mask = pg.Surface(data.settings.window, pg.SRCALPHA)
			canvas_mask.fill((col, col, col, col), special_flags = 0)
			canvas_mask.blit(canvas_gray, (0, 0), special_flags = mod)
			canvas_mask.fill((fac, fac, fac, fac), special_flags = pg.BLEND_RGBA_MULT)
			canvas.blit(canvas_mask, (0, 0), special_flags = mod)
			self.iris_target = 1 - (max(color[0], color[1], color[2]) / 255) * 2

		# Bloom: Duplicate the canvas, darken the copy to adjust intensity, downscale then upscale to blur, lighten the canvas with the result
		if data.settings.bloom and data.settings.bloom_blur:
			box = round(data.settings.window[0] / max(1, data.settings.bloom_blur)), round(data.settings.window[1] / max(1, data.settings.bloom_blur))
			fac = round((1 - data.settings.bloom) * 255)
			canvas_blur = pg.Surface.copy(canvas)
			canvas_blur.fill((fac, fac, fac), special_flags = pg.BLEND_RGBA_SUB)
			canvas_blur = pg.transform.smoothscale(canvas_blur, box)
			canvas_blur = pg.transform.smoothscale(canvas_blur, data.settings.window)
			canvas.blit(canvas_blur, (0, 0), special_flags = pg.BLEND_RGBA_ADD)

		# Filter: Scale the canvas to the window resolution, smooth and sharp passes are alternated to achieve the selected pixel filter
		# 0 = Fully sharp, 1 = Fully smooth, < 1 = Emulate subsampling, > 1 = Emulate supersampling
		if data.settings.scale > 1:
			func_scale_by = pg.transform.scale_by if data.settings.smooth > 1 else pg.transform.smoothscale_by
			func_scale = pg.transform.scale if data.settings.smooth < 1 else pg.transform.smoothscale
			if data.settings.smooth and data.settings.smooth != 1:
				fac = 1 / (1 - data.settings.smooth) if data.settings.smooth < 1 else data.settings.smooth
				canvas = func_scale_by(canvas, (fac, fac))
			canvas = func_scale(canvas, data.settings.window_scaled)

		# Add the info text to the canvas, blit the canvas to the screen, update Pygame display
		text_info = str(data.settings.width) + " x " + str(data.settings.height) + " (" + str(data.settings.width * data.settings.height) + "px) - " + str(math.trunc(self.clock.get_fps())) + " / " + str(data.settings.fps) + " FPS"
		text = self.font.render(text_info, True, (255, 255, 255))
		self.screen.blit(canvas, (0, 0))
		self.screen.blit(text, (0, 0))
		pg.display.flip()

	# Handle keyboard and mouse input, apply object movement and rotation for the main object
	def input(self, time: float):
		mods = pg.key.get_mods()
		mouse_rot = vec2(0, 0)

		# Read pending events and preform the appropriate actions based on mouse movement or the keys being pressed or released
		for e in pg.event.get():
			match e.type:
				case pg.QUIT:
					self.running = False
					return
				case pg.MOUSEMOTION:
					if self.mouselook:
						x, y = pg.mouse.get_pos()
						center = vec2(data.settings.window_scaled[0] / 2, data.settings.window_scaled[1] / 2)
						mouse_rot.x += center.x - x
						mouse_rot.y += center.y - y
						pg.mouse.set_pos((center.x, center.y))
						pg.event.clear(pg.MOUSEMOTION)
				case pg.MOUSEWHEEL:
					self.cam.lens = max(math.pi, min(math.pi * 48, self.cam.lens - e.y * 10))
				case pg.MOUSEBUTTONUP:
					match e.button:
						case 6:
							self.input_rot.x += 10
						case 7:
							self.input_rot.x -= 10
				case pg.MOUSEBUTTONDOWN:
					match e.button:
						case 6:
							self.input_rot.x -= 10
						case 7:
							self.input_rot.x += 10
				case pg.KEYUP:
					match e.key:
						case pg.K_w | pg.K_UP:
							self.input_vel.z -= 1
						case pg.K_s | pg.K_DOWN:
							self.input_vel.z += 1
						case pg.K_a | pg.K_LEFT:
							self.input_vel.x -= 1
						case pg.K_d | pg.K_RIGHT:
							self.input_vel.x += 1
						case pg.K_r | pg.K_SPACE:
							self.input_vel.y -= 1
						case pg.K_f | pg.K_LCTRL:
							self.input_vel.y += 1
						case pg.K_KP2:
							self.input_rot.z -= 10
						case pg.K_KP8:
							self.input_rot.z += 10
						case pg.K_KP4:
							self.input_rot.y -= 10
						case pg.K_KP6:
							self.input_rot.y += 10
						case pg.K_KP7:
							self.input_rot.x -= 10
						case pg.K_KP9:
							self.input_rot.x += 10
				case pg.KEYDOWN:
					match e.key:
						case pg.K_w | pg.K_UP:
							self.input_vel.z += 1
						case pg.K_s | pg.K_DOWN:
							self.input_vel.z -= 1
						case pg.K_a | pg.K_LEFT:
							self.input_vel.x += 1
						case pg.K_d | pg.K_RIGHT:
							self.input_vel.x -= 1
						case pg.K_r | pg.K_SPACE:
							self.input_vel.y += 1
						case pg.K_f | pg.K_LCTRL:
							self.input_vel.y -= 1
						case pg.K_KP2:
							self.input_rot.z += 10
						case pg.K_KP8:
							self.input_rot.z -= 10
						case pg.K_KP4:
							self.input_rot.y += 10
						case pg.K_KP6:
							self.input_rot.y -= 10
						case pg.K_KP7:
							self.input_rot.x += 10
						case pg.K_KP9:
							self.input_rot.x -= 10
						case pg.K_TAB:
							self.mouselook = not self.mouselook
						case pg.K_ESCAPE:
							self.running = False
							return

		# Apply movement if any direction is desired
		if self.input_vel != 0:
			speed = 2 if mods & pg.KMOD_SHIFT else 1

			if self.input_vel.x:
				unit = data.settings.speed_move * speed * time
				dir_right = self.cam.rot.vec_right()
				if data.settings.max_pitch:
					dir_right *= vec3(1, 0, 1)
					dir_right = dir_right.normalize()
				data.player.accelerate(dir_right * max(-1, min(+1, self.input_vel.x)) * unit)

			if self.input_vel.y:
				unit = data.settings.speed_jump / (1 + time)
				dir_up = self.cam.rot.vec_up()
				if data.settings.max_pitch:
					dir_up *= vec3(0, 1, 0)
					dir_up = dir_up.normalize()
				data.player.accelerate(dir_up * max(-1, min(+1, self.input_vel.y)) * unit)

			if self.input_vel.z:
				unit = data.settings.speed_move * speed * time
				dir_forward = self.cam.rot.vec_forward()
				if data.settings.max_pitch:
					dir_forward *= vec3(1, 0, 1)
					dir_forward = dir_forward.normalize()
				data.player.accelerate(dir_forward * max(-1, min(+1, self.input_vel.z)) * unit)

		# Apply rotation if any direction is desired, limit the roll and pitch of the camera to safe settings
		if self.input_rot != 0 or mouse_rot != 0:
			unit_key = data.settings.speed_move * time
			unit_mouse = data.settings.speed_mouse / (1 + time * 1000)
			rot = self.input_rot * unit_key + vec3(0, +mouse_rot.x, -mouse_rot.y) * unit_mouse
			data.player.rotate(rot)

			if data.settings.max_roll:
				roll_min = max(180, 360 - data.settings.max_roll)
				roll_max = min(180, data.settings.max_roll)
				data.player.rot.x = roll_max if data.player.rot.x > roll_max and data.player.rot.x <= 180 else data.player.rot.x
				data.player.rot.x = roll_min if data.player.rot.x < roll_min and data.player.rot.x > 180 else data.player.rot.x

			if data.settings.max_pitch:
				pitch_min = max(180, 360 - data.settings.max_pitch)
				pitch_max = min(180, data.settings.max_pitch)
				data.player.rot.z = pitch_max if data.player.rot.z > pitch_max and data.player.rot.z <= 180 else data.player.rot.z
				data.player.rot.z = pitch_min if data.player.rot.z < pitch_min and data.player.rot.z > 180 else data.player.rot.z

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
	# If culling is enabled only chunks that were traversed are recalculated, other chunks that require update will wait until being viewed
	def chunk_update(self, time: float):
		self.timer += time
		if self.timer >= data.settings.chunk_time:
			self.timer -= max(data.settings.chunk_time, time)
			traversed = unpack(self.traversed)

			# Scan existing chunks and check if their LOD changed, force recalculation if so
			for post, frame in self.chunks.items():
				if not data.settings.culling or post in traversed:
					pos = vec3(post[0], post[1], post[2])
					if not pos in data.objects_chunks_update and self.chunk_lod(pos + data.settings.chunk_radius) != frame.lod:
						data.objects_chunks_update.append(post)

			# Compile a new voxel list for chunks that need to be redrawn, add intersecting voxels for every object touching this chunk
			for post in list(data.objects_chunks_update):
				if not data.settings.culling or post in traversed:
					pos_min = vec3(post[0], post[1], post[2])
					pos_max = pos_min + data.settings.chunk_size
					lod = self.chunk_lod(pos_min + data.settings.chunk_radius)
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
					self.chunk_set(pos_min, voxels, lod)
					data.objects_chunks_update.remove(post)

			# Clear the old chunks from the camera and set new ones that will be used during ray tracing
			self.cam.chunk_clear()
			for post in self.chunks:
				if not data.settings.culling or post in traversed:
					self.cam.chunk_set(post, self.chunks[post])

	# Main loop of the Pygame window, apply input then execute the update functions of objects in the scene and request redrawing when the window is focused
	def update(self):
		if not data.player or not data.player.cam_vec:
			print("Error: No camera object found, define at least one object with a camera in the scene.")
			self.running = False
			return

		time = self.clock.get_time() / 1000
		if pg.mouse.get_focused():
			self.iris = mix(self.iris, self.iris_target * data.settings.iris, data.settings.iris_time * time)
			self.cam.pos = data.player.cam_pos
			self.cam.rot = data.player.cam_rot
			self.draw()
			self.chunk_update(time)
			pg.mouse.set_visible(not self.mouselook)
		for obj in data.objects:
			obj.update(self.cam.pos)
		self.input(time)

# Create the main window and start Pygame
Window()
