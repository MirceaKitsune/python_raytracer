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

	# Add or clear a camera chunk frame at this position
	def chunk_set(self, post: tuple, chunk):
		if chunk:
			self.chunks[post] = chunk
		elif post in self.chunks:
			del self.chunks[post]

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
			if not ray.pos >= chunk_min or not ray.pos <= chunk_max:
				chunk_min = ray.pos.snapped(data.settings.chunk_size)
				chunk_max = chunk_min + data.settings.chunk_size
				post_chunk = chunk_min.tuple()
				chunk = self.chunks[post_chunk] if post_chunk in self.chunks else None
				if not post_chunk in ray.traversed:
					ray.traversed.append(post_chunk)

			if chunk:
				pos = math.floor(ray.pos)
				mat = chunk.get_voxel(pos)
				if mat:
					# Call the material function and obtain the bounce amount, add it to the total number of bounces
					# Normalize ray velocity after any changes to ensure the speed of light remains 1 and voxels aren't skipped or calculated twice
					bounce = mat.function(ray, mat, data.settings)
					ray.bounces += bounce
					ray.life /= chunk.resolution + bounce * data.settings.lod_bounces
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
						pos_x = math.floor(ray_pos_x)
						pos_y = math.floor(ray_pos_y)
						pos_z = math.floor(ray_pos_z)
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
			step = chunk.resolution if chunk else 1 + abs(data.settings.chunk_radius - (ray.pos.mins() + data.settings.chunk_radius) % data.settings.chunk_size)
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
		self.chunks_objects = {}
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
		update = False
		for t in range(len(self.busy)):
			if not self.busy[t]:
				self.busy[t] = update = True
				self.pool.apply_async(self.cam.tile, args = (t, 0), callback = self.draw_tile)

		# Redraw the canvas if at least one thread produced a new pixel set
		if update:
			# Color spill: Multiply the canvas with its average color
			canvas = pg.Surface.copy(self.canvas)
			color = pg.transform.average_color(canvas, consider_alpha = True)
			if data.settings.spill:
				fac = 255 - round(data.settings.spill * 255)
				color_tint = min(255, color[0] + fac), min(255, color[1] + fac), min(255, color[2] + fac), min(255, color[3] + fac)
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

			# Subsampling: Smoothly scale the canvas by the subsample amount to create extra pixels
			if data.settings.subsamples:
				fac = 1 + data.settings.subsamples
				canvas = pg.transform.smoothscale_by(canvas, (fac, fac))

			# Filter: Scale the canvas to the window size using the desired type of pixel smoothness, for gradual pixel hardness the canvas is first scaled sharply and then smoothly
			if data.settings.smooth == 0:
				canvas = pg.transform.scale(canvas, data.settings.window_scaled)
			elif data.settings.smooth == 1:
				canvas = pg.transform.smoothscale(canvas, data.settings.window_scaled)
			else:
				fac = math.trunc(1 / data.settings.smooth)
				canvas = pg.transform.scale_by(canvas, (fac, fac))
				canvas = pg.transform.smoothscale(canvas, data.settings.window_scaled)

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
			rot = vec3(0, data.player.rot.y, 0).quaternion() if data.settings.max_pitch else data.player.rot.quaternion()
			if self.input_vel.x:
				unit = data.settings.speed_move * speed * time
				dir_right = rot.vec_right()
				data.player.accelerate(dir_right * max(-1, min(+1, self.input_vel.x)) * unit)
			if self.input_vel.y:
				unit = data.settings.speed_jump / (1 + time)
				dir_up = rot.vec_up()
				data.player.accelerate(dir_up * max(-1, min(+1, self.input_vel.y)) * unit)
			if self.input_vel.z:
				unit = data.settings.speed_move * speed * time
				dir_forward = rot.vec_forward()
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

	# Compile a new list of chunks to be used by the renderer, chunks are only recalculated based on the update timer
	# If culling is enabled only chunks that were traversed are recalculated, other chunks that require update will wait until being viewed
	def chunk_update(self, time: float):
		self.timer += time
		if self.timer >= data.settings.chunk_time:
			self.timer -= max(data.settings.chunk_time, time)
			traversed = unpack(self.traversed)

			# Recalculate the frames of objects that require visual update, chunks that need to be updated are set to None
			# An object's existing chunks are removed if the object was deleted or will be updated, new ones are then added if the object is visible
			# Frames in object chunks are indexed by [object_id][position_chunk]
			for obj_id in merge(data.objects.keys(), self.chunks_objects.keys()):
				if obj_id in self.chunks_objects and (not obj_id in data.objects or data.objects[obj_id].redraw):
					for post_chunk in self.chunks_objects[obj_id]:
						self.chunks[post_chunk] = None
					del self.chunks_objects[obj_id]
				if obj_id in data.objects and data.objects[obj_id].redraw and data.objects[obj_id].visible:
					obj = data.objects[obj_id]
					obj.redraw = False
					spr = obj.get_sprite()
					chunk_min = obj.mins.snapped(data.settings.chunk_size)
					chunk_max = obj.maxs.snapped(data.settings.chunk_size)
					for chunk_x in range(chunk_min.x, chunk_max.x + 1, data.settings.chunk_size):
						for chunk_y in range(chunk_min.y, chunk_max.y + 1, data.settings.chunk_size):
							for chunk_z in range(chunk_min.z, chunk_max.z + 1, data.settings.chunk_size):
								voxels = {}
								pos_min = obj.mins.max(vec3(chunk_x, chunk_y, chunk_z))
								pos_max = obj.maxs.min(vec3(chunk_x + data.settings.chunk_size, chunk_y + data.settings.chunk_size, chunk_z + data.settings.chunk_size))
								post_chunk = chunk_x, chunk_y, chunk_z
								self.chunks[post_chunk] = None
								for x in range(pos_min.x, pos_max.x):
									for y in range(pos_min.y, pos_max.y):
										for z in range(pos_min.z, pos_max.z):
											pos = vec3(x, y, z)
											mat = spr.get_voxel(None, pos - obj.mins, obj.rot)
											if mat:
												post = x, y, z
												voxels[post] = mat
								if voxels:
									if not obj_id in self.chunks_objects:
										self.chunks_objects[obj_id] = {}
									self.chunks_objects[obj_id][post_chunk] = data.Frame(packed = True, resolution = 1)
									self.chunks_objects[obj_id][post_chunk].set_voxels(voxels, True)

			# Empty chunks were marked for recalculation, remove and create new frames from the combined voxels lists of all chunk if any voxel data is available
			# Valid chunks are sent to the camera for rendering if a chunk is visible or occlusion culling is disabled
			# Frames in chunks are indexed by [position_chunk][lod]
			for post_chunk in list(self.chunks.keys()):
				if not self.chunks[post_chunk]:
					voxels = {}
					for obj in self.chunks_objects.values():
						if post_chunk in obj:
							voxels |= obj[post_chunk].get_voxels()
					if voxels:
						self.chunks[post_chunk] = [None] * (data.settings.chunk_lod + 1)
						for lod in range(data.settings.chunk_lod + 1):
							self.chunks[post_chunk][lod] = data.Frame(packed = True, resolution = lod + 1)
							self.chunks[post_chunk][lod].set_voxels(voxels, True)
					else:
						del self.chunks[post_chunk]
				if post_chunk in self.chunks and (not data.settings.culling or post_chunk in traversed):
					pos = vec3(post_chunk[0], post_chunk[1], post_chunk[2]) + data.settings.chunk_radius
					lod = min(math.trunc(pos.distance(self.cam.pos) / (data.settings.dist_max / (1 + data.settings.chunk_lod))), data.settings.chunk_lod)
					self.cam.chunk_set(post_chunk, self.chunks[post_chunk][lod])
				else:
					self.cam.chunk_set(post_chunk, None)

	# Main loop of the Pygame window, apply input then execute the update functions of objects in the scene and request redrawing when the window is focused
	def update(self):
		if not data.player or not data.player.cam_vec:
			print("Error: No camera object found, define at least one object with a camera in the scene.")
			self.running = False
			return

		time = min(1, self.clock.get_time() / 1000)
		if pg.mouse.get_focused():
			self.iris = mix(self.iris, self.iris_target * data.settings.iris, data.settings.iris_time * time)
			self.cam.pos = data.player.cam_pos
			self.cam.rot = data.player.cam_rot
			self.draw()
			self.chunk_update(time)
			pg.mouse.set_visible(not self.mouselook)
		for obj in data.objects.values():
			obj.update(self.cam.pos)
		self.input(time)

# Create the main window and start Pygame
Window()
