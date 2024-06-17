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
		self.lines = math.ceil(data.settings.height / data.settings.threads)
		self.proportions = ((data.settings.width + data.settings.height) / 2) / max(data.settings.width, data.settings.height)
		self.lens = data.settings.fov * math.pi / 8
		self.chunks = {}

	# Get a material from a chunk's frame at the given global position
	def chunk_get(self, pos: vec3):
		pos_chunk = pos.snapped(data.settings.chunk_size, -1)
		pos_chunk_post = pos_chunk + round(data.settings.chunk_size / 2)
		post = pos_chunk_post.tuple()
		if post in self.chunks:
			pos = math.trunc(pos - pos_chunk)
			return self.chunks[post].get_voxel(pos)
		return None

	# Create a new frame with this voxel list or delete the chunk if empty
	def chunk_set(self, pos: vec3, voxels: dict):
		post = pos.tuple()
		if voxels:
			self.chunks[post] = data.Frame(packed = True)
			self.chunks[post].set_voxels(voxels)
		elif post in self.chunks:
			del self.chunks[post]

	# Trace the pixel based on the given 2D direction which is used to calculate ray velocity from lens distorsion: X = -1 is left, X = +1 is right, Y = -1 is down, Y = +1 is up
	def trace(self, dir_x: float, dir_y: float, sample: int):
		# Randomly offset the ray's angle based on the DOF setting, fetch its direction and use it as the ray velocity
		# Velocity must be normalized as voxels need to be checked at all integer positions, the speed of light is always 1
		# Therefore at least one axis must be precisely -1 or +1 while others can be anything in that range, lower speeds are scaled accordingly based on the largest
		lens_x = (dir_x / self.proportions) * self.lens + rand(data.settings.dof)
		lens_y = (dir_y * self.proportions) * self.lens + rand(data.settings.dof)
		ray_rot = self.rot.rotate(vec3(0, -lens_y, +lens_x))
		ray_dir = ray_rot.dir(True)
		ray_dir = ray_dir.normalize()

		# Ray data is kept in a data store so it can be easily delivered to material functions and support custom properties
		ray = store(
			color = rgb(0, 0, 0),
			energy = 0,
			pos = self.pos + ray_dir * data.settings.dist_min,
			vel = ray_dir,
			step = 0,
			life = data.settings.dist_max - data.settings.dist_min,
			hits = 0,
		)

		# Each step the ray advances through space by adding its velocity to its position, starting from the minimum distance and going up to the maximum distance
		# If a material is found, its function is called which can modify any of the ray properties provided
		# Note that diagonal steps can be preformed which allows penetrating through 1 voxel thick corners, checking in a stair pattern isn't done for performance reasons
		while ray.step < ray.life:				
			mat = self.chunk_get(ray.pos)
			if mat:
				# Reflect the velocity of the ray based on material IOR and the neighbors of this voxel which are used to determine face normals
				# A material considers its neighbors solid if they have the same IOR, otherwise they won't affect the direction of ray reflections
				# If IOR is above 0.5 check the neighbor opposite the ray direction in that axis, otherwise check the neighbor in the ray's direction
				if mat.ior:
					direction = (mat.ior - 0.5) * 2
					pos_x = ray.pos + vec3(1, 0, 0) if ray.vel.x * direction < 0 else ray.pos - vec3(1, 0, 0)
					pos_y = ray.pos + vec3(0, 1, 0) if ray.vel.y * direction < 0 else ray.pos - vec3(0, 1, 0)
					pos_z = ray.pos + vec3(0, 0, 1) if ray.vel.z * direction < 0 else ray.pos - vec3(0, 0, 1)
					mat_x = self.chunk_get(pos_x)
					mat_y = self.chunk_get(pos_y)
					mat_z = self.chunk_get(pos_z)
					if not (mat_x and mat_x.ior == mat.ior):
						ray.vel.x = mix(+ray.vel.x, -ray.vel.x, mat.ior)
					if not (mat_y and mat_y.ior == mat.ior):
						ray.vel.y = mix(+ray.vel.y, -ray.vel.y, mat.ior)
					if not (mat_z and mat_z.ior == mat.ior):
						ray.vel.z = mix(+ray.vel.z, -ray.vel.z, mat.ior)

				# Call the material function, normalize ray velocity after making changes to ensure the speed of light remains 1 and future voxels aren't skipped or calculated twice
				mat.function(ray, mat, data.settings)
				ray.vel = ray.vel.normalize()

			# Terminate the ray earlier to improve performance, hit based checks only need to be calculated if a material was hit
			if mat and ray.hits and ray.color.raw_total() * ray.hits * data.settings.terminate_light >= 1:
				break
			elif mat and ray.hits and data.settings.terminate_hits / ray.hits < random.random():
				break
			elif ray.step / ray.life > 1 - data.settings.terminate_dist * random.random():
				break
			ray.step += 1
			ray.pos += ray.vel

		# Run the background function and return the resulting color, fall back to black if a color wasn't set
		if data.background:
			data.background(ray, data.settings)
		return ray.color

	# Called by threads with a tile image to paint to, creates a new surface for this thread to paint to which is returned to the main thread as a byte string
	# If static noise is enabled, the random seed is set to an index unique to this pixel and sample so noise in ray calculations is static instead of flickering
	# The batch number decides which group of pixels should be rendered this call using a pattern generated from the 2D position of the pixel
	def tile(self, image: str, sample: int, thread: int, batch: int):
		tile = pg.image.frombytes(image, (data.settings.width, self.lines), "RGB")

		for x in range(data.settings.width):
			for y in range(self.lines):
				if (x ^ y) % data.settings.batches == batch:
					line_y = y + (self.lines * thread)
					dir_x = (-0.5 + x / data.settings.width) * 2
					dir_y = (-0.5 + line_y / data.settings.height) * 2

					if data.settings.static:
						random.seed((1 + x) * (1 + line_y) * (1 + sample))
					tile.set_at((x, y), self.trace(dir_x, dir_y, sample).tuple())
					random.seed(None)

		return (pg.image.tobytes(tile, "RGB"), sample, thread)

	# Update the position and rotation this camera will shoot rays from
	# Valid objects are compiled to an object list local to the camera which is used once per redraw
	def update(self, cam_pos: vec3, cam_rot: vec3):
		self.pos = cam_pos
		self.rot = cam_rot

		# Compile a new voxel list for chunks that need to be redrawn, add intersecting voxels for every object touching this chunk
		for pos_center in data.objects_chunks_update:
			voxels = {}
			pos_min = pos_center - round(data.settings.chunk_size / 2)
			pos_max = pos_center + round(data.settings.chunk_size / 2)
			for obj in data.objects:
				if obj.visible and obj.intersects(pos_min, pos_max):
					spr = obj.get_sprite()
					for x in range(pos_min.x, pos_max.x):
						for y in range(pos_min.y, pos_max.y):
							for z in range(pos_min.z, pos_max.z):
								pos = vec3(x, y, z)
								if obj.intersects(pos, pos):
									mat = spr.get_voxel(None, pos - obj.mins)
									if mat:
										pos_chunk = pos - pos_min
										post_chunk = pos_chunk.tuple()
										voxels[post_chunk] = mat
			self.chunk_set(pos_center, voxels)
		data.objects_chunks_update = []

# Window: Initializes Pygame and starts the main loop, handles all updates and redraws the canvas using a Camera instance
class Window:
	def __init__(self):
		# Configure Pygame and the main screen as well as the camera and thread pool that will be used to update the window
		pg.init()
		pg.display.set_caption("Voxel Tracer")
		self.rect = vec2(data.settings.width, data.settings.height)
		self.rect_win = self.rect * data.settings.scale
		self.lines = math.ceil(data.settings.height / data.settings.threads)
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
				surface = pg.Surface((data.settings.width, self.lines), pg.HWSURFACE)
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
					tile = pg.image.frombytes(self.tiles[s][t], (data.settings.width, self.lines), "RGB")
					tiles.append((tile, (0, t * self.lines)))
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
