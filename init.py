#!/usr/bin/python3
from lib import *

import importlib
import configparser

import multiprocessing as mp
import pygame as pg
import math
import random

import data

# Fetch the mod name and load the config from the mod path
mod = len(sys.argv) > 1 and sys.argv[1].strip() or "default"
cfg = configparser.RawConfigParser()
cfg.read("mods/" + mod + "/config.cfg")
settings = store(
	width = cfg.getint("WINDOW", "width") or 96,
	height = cfg.getint("WINDOW", "height") or 64,
	scale = cfg.getint("WINDOW", "scale") or 8,
	smooth = cfg.getboolean("WINDOW", "smooth") or False,
	fps = cfg.getint("WINDOW", "fps") or 24,

	static = cfg.getboolean("RENDER", "static") or False,
	samples = cfg.getint("RENDER", "samples") or 1,
	fov = cfg.getfloat("RENDER", "fov") or 90,
	falloff = cfg.getfloat("RENDER", "falloff") or 0,
	dof = cfg.getfloat("RENDER", "dof") or 0,
	skip = cfg.getfloat("RENDER", "skip") or 0,
	dist_min = cfg.getint("RENDER", "dist_min") or 0,
	dist_max = cfg.getint("RENDER", "dist_max") or 48,
	terminate_hits = cfg.getfloat("RENDER", "terminate_hits") or 0,
	terminate_dist = cfg.getfloat("RENDER", "terminate_dist") or 0,
	threads = cfg.getint("RENDER", "threads") or mp.cpu_count(),

	speed_jump = cfg.getfloat("PHYSICS", "speed_jump") or 10,
	speed_move = cfg.getfloat("PHYSICS", "speed_move") or 1,
	speed_mouse = cfg.getfloat("PHYSICS", "speed_mouse") or 10,
	max_pitch = cfg.getfloat("PHYSICS", "max_pitch") or 0,
)

# Camera: A subset of Window which only stores data needed for rendering and is used by threads, preforms ray tracing and draws tiles which are overlayed to the canvas by the main thread
class Camera:
	def __init__(self):
		self.pos = vec3(0, 0, 0)
		self.rot = vec3(0, 0, 0)
		self.lines = math.ceil(settings.height / settings.threads)
		self.proportions = ((settings.width + settings.height) / 2) / max(settings.width, settings.height)
		self.lens = settings.fov * math.pi / 8
		self.objects = []

	# Trace the pixel based on the given 2D direction which is used to calculate ray velocity from lens distorsion: X = -1 is left, X = +1 is right, Y = -1 is down, Y = +1 is up
	def trace(self, dir_x: float, dir_y: float, sample: int):
		# Randomly offset the ray's angle based on the DOF setting, fetch its direction and use it as the ray velocity
		# Velocity must be normalized as voxels need to be checked at all integer positions, the speed of light is always 1
		# Therefore at least one axis must be precisely -1 or +1 while others can be anything in that range, lower speeds are scaled accordingly based on the largest
		lens_x = (dir_x / self.proportions) * self.lens + rand(settings.dof)
		lens_y = (dir_y * self.proportions) * self.lens + rand(settings.dof)
		ray_rot = self.rot.rotate(vec3(0, -lens_y, +lens_x))
		ray_dir = ray_rot.dir(True)
		ray_dir = ray_dir.normalize()

		# Ray data is kept in a data store so it can be easily delivered to material functions and support custom properties
		ray = store(
			color = rgb(0, 0, 0),
			energy = 0,
			pos = self.pos + ray_dir * settings.dist_min,
			vel = ray_dir,
			step = 0,
			life = settings.dist_max - settings.dist_min,
			hits = 0,
		)

		# Each step the ray advances through space by adding its velocity to its position, starting from the minimum distance and going up to the maximum distance
		# If a material is found, its function is called which can modify any of the ray properties provided
		# Note that diagonal steps can be preformed which allows penetrating through 1 voxel thick corners, checking in a stair pattern isn't done for performance reasons
		while ray.step < ray.life:
			for obj in self.objects:
				if obj.intersects(ray.pos, ray.pos):
					spr = obj.get_sprite()
					mat = spr.get_voxel(None, obj.maxs - ray.pos)
					if mat:
						# Reflect the velocity of the ray based on material IOR and the neighbors of this voxel which are used to determine face normals
						# A material considers its neighbors solid if they have the same IOR, otherwise they won't affect the direction of ray reflections
						# If IOR is above 0.5 check the neighbor opposite the ray direction in that axis, otherwise check the neighbor in the ray's direction
						if mat.ior:
							direction = (mat.ior - 0.5) * 2
							dir_x = ray.vel.x * direction < 0 and vec3(-1, 0, 0) or vec3(+1, 0, 0)
							dir_y = ray.vel.y * direction < 0 and vec3(0, -1, 0) or vec3(0, +1, 0)
							dir_z = ray.vel.z * direction < 0 and vec3(0, 0, -1) or vec3(0, 0, +1)
							mat_x = spr.get_voxel(None, obj.maxs - ray.pos + dir_x)
							mat_y = spr.get_voxel(None, obj.maxs - ray.pos + dir_y)
							mat_z = spr.get_voxel(None, obj.maxs - ray.pos + dir_z)
							if not (mat_x and mat_x.ior == mat.ior):
								ray.vel.x = mix(+ray.vel.x, -ray.vel.x, mat.ior)
							if not (mat_y and mat_y.ior == mat.ior):
								ray.vel.y = mix(+ray.vel.y, -ray.vel.y, mat.ior)
							if not (mat_z and mat_z.ior == mat.ior):
								ray.vel.z = mix(+ray.vel.z, -ray.vel.z, mat.ior)

						# Call the material function, normalize ray velocity after making changes to ensure the speed of light remains 1 and future voxels aren't skipped or calculated twice
						mat.function(ray, mat, settings)
						ray.vel = ray.vel.normalize()
						break

			# Terminate this ray earlier in some circumstances to improve performance
			if ray.hits and settings.terminate_hits / ray.hits < random.random():
				break
			elif ray.step / ray.life > 1 - settings.terminate_dist * random.random():
				break
			ray.step += 1
			ray.pos += ray.vel

		# Run the background function and return the resulting color, fall back to black if a color wasn't set
		if data.background:
			data.background(ray, settings)
		return ray.color

	# Called by threads with a tile image to paint to, creates a new surface for this thread to paint to which is returned to the main thread as a byte string
	# If static noise is enabled, the random seed is set to an index unique to this pixel and sample so noise in ray calculations is static instead of flickering
	def tile(self, image: str, sample: int, thread: int):
		tile = pg.image.frombytes(image, (settings.width, self.lines), "RGB")
		for x in range(settings.width):
			for y in range(self.lines):
				if settings.skip < random.random():
					line_y = y + (self.lines * thread)
					dir_x = (-0.5 + x / settings.width) * 2
					dir_y = (-0.5 + line_y / settings.height) * 2

					if settings.static:
						random.seed((1 + x) * (1 + line_y) * (1 + sample))
					tile.set_at((x, y), self.trace(dir_x, dir_y, sample).tuple())
					random.seed(None)

		return (pg.image.tobytes(tile, "RGB"), sample, thread)

	# Update the position and rotation this camera will shoot rays from
	# Valid objects are compiled to an object list local to the camera which is used once per redraw
	def move(self, pos: vec3, rot: vec3):
		self.pos = pos
		self.rot = rot
		self.objects = []
		for obj in data.objects:
			if obj.sprites[0] and math.dist(obj.pos.array(), self.pos.array()) <= settings.dist_max + obj.size.max():
				self.objects.append(obj)

# Window: Initializes Pygame and starts the main loop, handles all updates and redraws the canvas using a Camera instance
class Window:
	def __init__(self):
		# Configure Pygame and the main screen as well as the camera and thread pool that will be used to update the window
		pg.init()
		pg.display.set_caption("Voxel Tracer")
		self.rect = vec2(settings.width, settings.height)
		self.rect_win = self.rect * settings.scale
		self.lines = math.ceil(settings.height / settings.threads)
		self.screen = pg.display.set_mode(self.rect_win.tuple(), pg.HWSURFACE)
		self.canvas = pg.Surface(self.rect.tuple(), pg.HWSURFACE)
		self.font = pg.font.SysFont(None, 24)
		self.clock = pg.time.Clock()
		self.pool = mp.Pool(processes = settings.threads)
		self.cam = Camera()
		self.mouselook = True
		self.running = True

		# Prepare the list of samples, each sample stores an image slot for every thread which is cleared after being drawn
		self.tiles = []
		for s in range(settings.samples):
			self.tiles.append([])
			for t in range(settings.threads):
				surface = pg.Surface((settings.width, self.lines), pg.HWSURFACE)
				image = pg.image.tobytes(surface, "RGB")
				self.tiles[s].append(image)

		# Main loop, limited by FPS with a slower clock when the window isn't focused
		while self.running:
			fps = pg.mouse.get_focused() and settings.fps or math.trunc(settings.fps / 5)
			self.clock.tick(fps)
			self.update()
			if not self.running:
				self.pool.close()
				self.pool.join()
				exit

	# Called by the thread pool on finish, adds the image to the appropriate sample and thread for the main thread to mix
	def update_tile(self, result):
		image, sample, thread = result
		self.tiles[sample][thread] = image

	# Render a new frame from the perspective of the main object, handle object physics and player control
	def update(self):
		obj_cam = None
		for obj in data.objects:
			if obj.cam_pos:
				obj_cam = obj
			obj.physics(self.clock.get_time())

		pg.mouse.set_visible(not self.mouselook)
		keys = pg.key.get_pressed()
		mods = pg.key.get_mods()
		d = obj_cam.rot.dir(False)
		units = self.clock.get_time() / 1000 * settings.speed_move
		units_jump = self.clock.get_time() / 1000 * settings.speed_jump
		units_mouse = settings.speed_mouse / 1000
		self.cam.move(obj_cam.pos + vec3(obj_cam.cam_pos.x * d.x, obj_cam.cam_pos.y, obj_cam.cam_pos.x * d.z), obj_cam.rot)

		# Render: Request the camera to draw a new tile for each thread and sample, gradually blend thread samples that have finished to the canvas
		samples = []
		for s in range(len(self.tiles)):
			tiles = []
			for t in range(len(self.tiles[s])):
				if self.tiles[s][t]:
					tile = pg.image.frombytes(self.tiles[s][t], (settings.width, self.lines), "RGB")
					tiles.append((tile, (0, t * self.lines)))
					self.pool.apply_async(self.cam.tile, args = (self.tiles[s][t], s, t,), callback = self.update_tile)
					self.tiles[s][t] = None
			sample = pg.Surface.copy(self.canvas)
			sample.blits(tiles)
			samples.append(sample)
		self.canvas = pg.transform.average_surfaces(samples)

		# Render: Blit the total number of tiles that are waiting to the canvas, update and blit the info text on top
		canvas = settings.smooth and pg.transform.smoothscale(self.canvas, self.rect_win.tuple()) or pg.transform.scale(self.canvas, self.rect_win.tuple())
		text_info = str(settings.width) + " x " + str(settings.height) + " (" + str(settings.width * settings.height) + "px) - " + str(math.trunc(self.clock.get_fps())) + " / " + str(settings.fps) + " FPS"
		text = self.font.render(text_info, True, (255, 255, 255))
		self.screen.blit(canvas, (0, 0))
		self.screen.blit(text, (0, 0))
		pg.display.update()

		# Input, mods: Acceleration
		if mods & pg.KMOD_SHIFT:
			units *= 5

		# Input, one time events: Quit, request quit or toggle mouselook, mouse wheel movement, mouse motion
		for e in pg.event.get():
			if e.type == pg.QUIT:
				self.running = False
				return
			if e.type == pg.KEYDOWN:
				if e.key == pg.K_ESCAPE:
					self.running = False
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
				obj_cam.rotate(rot * units_mouse, settings.max_pitch)
				pg.mouse.set_pos((center.x, center.y))

		# Input, ongoing events: Camera movement, camera rotation
		if keys[pg.K_w]:
			obj_cam.impulse(vec3(+d.x, +d.y, +d.z) * units)
		if keys[pg.K_s]:
			obj_cam.impulse(vec3(-d.x, -d.y, -d.z) * units)
		if keys[pg.K_a]:
			obj_cam.impulse(vec3(-d.z, 0, +d.x) * units)
		if keys[pg.K_d]:
			obj_cam.impulse(vec3(+d.z, 0, -d.x) * units)
		if keys[pg.K_r] or keys[pg.K_SPACE]:
			obj_cam.impulse(vec3(0, +1, 0) * units_jump)
		if keys[pg.K_f] or keys[pg.K_LCTRL]:
			obj_cam.impulse(vec3(0, -1, 0) * units_jump)
		if keys[pg.K_UP]:
			obj_cam.rotate(vec3(0, +5, 0) * units, settings.max_pitch)
		if keys[pg.K_DOWN]:
			obj_cam.rotate(vec3(0, -5, 0) * units, settings.max_pitch)
		if keys[pg.K_LEFT]:
			obj_cam.rotate(vec3(0, 0, -5) * units, settings.max_pitch)
		if keys[pg.K_RIGHT]:
			obj_cam.rotate(vec3(0, 0, +5) * units, settings.max_pitch)

# Import the init script of the mod and create the main window
importlib.import_module("mods." + mod + ".init")
Window()
