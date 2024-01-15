#!/usr/bin/python3
from lib import *

import multiprocessing as mp
import pygame as pg
import math
import random

import builtin
import data

# Camera: A subset of Window which only stores data needed for rendering and is used by threads, preforms ray tracing and draws tiles which are overlayed to the canvas by the main thread
class Camera:
	def __init__(self):
		self.width = cfg.getint("WINDOW", "width") or 96
		self.height = cfg.getint("WINDOW", "height") or 64
		self.ambient = cfg.getfloat("RENDER", "ambient") or 0
		self.static = cfg.getboolean("RENDER", "static") or False
		self.samples_min = cfg.getfloat("RENDER", "samples_min") or 0
		self.samples_max = cfg.getfloat("RENDER", "samples_max") or 0
		self.fov = cfg.getfloat("RENDER", "fov") or 90
		self.dof = cfg.getfloat("RENDER", "dof") or 0
		self.blur = cfg.getfloat("RENDER", "blur") or 0
		self.dist_min = cfg.getint("RENDER", "dist_min") or 0
		self.dist_max = cfg.getint("RENDER", "dist_max") or 48
		self.terminate_hits = cfg.getfloat("RENDER", "terminate_hits") or 0
		self.terminate_dist = cfg.getfloat("RENDER", "terminate_dist") or 0
		self.threads = cfg.getint("RENDER", "threads") or mp.cpu_count()

		self.pos = vec3(0, 0, 0)
		self.rot = vec3(0, 0, 0)
		self.lens = self.fov * math.pi / 8
		self.proportions = ((self.width + self.height) / 2) / max(self.width, self.height)
		self.frame = data.Frame()

	# Trace the pixel based on the given 2D direction which is used to calculate ray velocity from lens distorsion: X = -1 is left, X = +1 is right, Y = -1 is down, Y = +1 is up
	def trace(self, dir_x: float, dir_y: float):
		# Randomly offset the ray's angle based on the DOF setting, fetch its direction and use it as the ray velocity
		# Velocity must be normalized as voxels need to be checked at all integer positions, the speed of light is always 1
		# Therefore at least one axis must be precisely -1 or +1 while others can be anything in that range, lower speeds are scaled accordingly based on the largest
		lens_x = (dir_x / self.proportions) * self.lens + rand(self.dof)
		lens_y = (dir_y * self.proportions) * self.lens + rand(self.dof)
		ray_rot = self.rot.rotate(vec3(0, -lens_y, +lens_x))
		ray_dir = ray_rot.dir(True)
		ray_dir = ray_dir.normalize()

		# Ray data is kept in a data store so it can be easily delivered to material functions and support custom properties
		ray = store(
			col = None,
			absorption = 1,
			energy = self.ambient,
			pos = self.pos + ray_dir * self.dist_min,
			vel = ray_dir,
			step = 0,
			life = self.dist_max - self.dist_min,
			hits = 0,
		)

		# Each step the ray advances through space by adding its velocity to its position, starting from the minimum distance and going up to the maximum distance
		# If a material is found, its function is called which can modify any of the ray properties provided
		# Note that diagonal steps can be preformed which allows penetrating through 1 voxel thick corners, checking in a stair pattern isn't done for performance reasons
		while ray.step < ray.life:
			mat = self.frame.get_voxel(ray.pos)
			if mat:
				# Reflect the velocity of the ray based on material IOR and the neighbors of this voxel which are used to determine face normals
				# A material considers its neighbors solid if they have the same IOR, otherwise they won't affect the direction of ray reflections
				# If IOR is above 0.5 check the neighbor opposite the ray direction in that axis, otherwise check the neighbor in the ray's direction
				if mat.ior:
					direction = (mat.ior - 0.5) * 2
					ofs_x = ray.vel.x * direction < 0 and vec3(+1, 0, 0) or vec3(-1, 0, 0)
					ofs_y = ray.vel.y * direction < 0 and vec3(0, +1, 0) or vec3(0, -1, 0)
					ofs_z = ray.vel.z * direction < 0 and vec3(0, 0, +1) or vec3(0, 0, -1)
					mat_x = self.frame.get_voxel(ray.pos + ofs_x)
					mat_y = self.frame.get_voxel(ray.pos + ofs_y)
					mat_z = self.frame.get_voxel(ray.pos + ofs_z)
					if not (mat_x and mat_x.ior == mat.ior):
						ray.vel.x = mix(+ray.vel.x, -ray.vel.x, mat.ior)
					if not (mat_y and mat_y.ior == mat.ior):
						ray.vel.y = mix(+ray.vel.y, -ray.vel.y, mat.ior)
					if not (mat_z and mat_z.ior == mat.ior):
						ray.vel.z = mix(+ray.vel.z, -ray.vel.z, mat.ior)

				# Call the material function, normalize ray velocity after making changes to ensure the speed of light remains 1 and future voxels aren't skipped or calculated twice
				mat.function(ray, mat)
				ray.vel = ray.vel.normalize()

			# Terminate this ray earlier in some circumstances to improve performance
			if ray.hits and self.terminate_hits / ray.hits < random.random():
				break
			elif ray.step / ray.life > 1 - self.terminate_dist * random.random():
				break
			ray.step += 1
			ray.pos += ray.vel

		# Run the background function and return the resulting color, fall back to black if a color wasn't set
		if data.background:
			data.background(ray)
		return ray.col and ray.col.mix(rgb(0, 0, 0), 1 - ray.energy) or rgb(0, 0, 0)

	# Called by threads with a thread ID indicating the tile number, creates a new surface for this thread to paint to which is returned to the main thread as a byte string
	# The alpha channel is used to skip drawing unchanged pixels and apply the blur effect by reducing how much pixels on the image are blended to the canvas
	def draw(self, thread):
		tile = pg.Surface((self.width, math.ceil(self.height / self.threads)), pg.HWSURFACE + pg.SRCALPHA)
		lines = math.ceil(self.height / self.threads)
		for x in range(self.width):
			dir_x = (-0.5 + x / self.width) * 2
			for y in range(lines):
				dir_y = (-0.5 + (y + lines * thread) / self.height) * 2
				colors = []

				# Preform a trace for each sample and get its pixel color, the number of samples is the closest integer between the minimum and maximum random sample range
				# If static noise is enabled, the random seed is set to an index unique to this pixel and sample so noise in ray calculations is static instead of flickering
				samples = round(max(0, random.uniform(self.samples_min, self.samples_max)))
				for i in range(samples):
					if self.static:
						random.seed(math.trunc(((1 + dir_x) * self.width) * ((1 + dir_y) * self.height) * (1 + i)))
					colors.append(self.trace(dir_x, dir_y))
				random.seed(None)

				# Paint the pixel with the average color of all samples, skip updating this pixel if no samples were traced
				if len(colors) > 0:
					col_r = col_g = col_b = col_a = 0
					for c in colors:
						col_r += c.r
						col_g += c.g
						col_b += c.b
					col_r = round(col_r / len(colors))
					col_g = round(col_g / len(colors))
					col_b = round(col_b / len(colors))
					col_a = round(self.blur * 255)
					tile.set_at((x, y), (col_r, col_g, col_b, col_a))

		return pg.image.tobytes(tile, "RGBA")

	# Update the position and rotation this camera will shoot rays from
	# The voxels of valid objects are compiled to a virtual frame local to the camera, which is used once per redraw to preform ray tracing
	# Only check objects containing a sprite that are within the view range, after which only add voxels that are themselves within range
	def move(self, pos: vec3, rot: vec3):
		self.pos = pos
		self.rot = rot
		self.frame.clear()
		for obj in data.objects:
			if obj.sprites[0] and math.dist(obj.pos.array(), self.pos.array()) <= self.dist_max + obj.size.max():
				for pos, mat in obj.get_sprite().get_voxels(None):
					pos_world = obj.maxs - pos
					if mat and math.dist(pos_world.array(), self.pos.array()) <= self.dist_max:
						self.frame.set_voxel(pos_world, mat)

# Window: Initializes Pygame and starts the main loop, handles all updates and redraws the canvas using a Camera instance
class Window:
	def __init__(self):
		self.width = cfg.getint("WINDOW", "width") or 96
		self.height = cfg.getint("WINDOW", "height") or 64
		self.scale = cfg.getint("WINDOW", "scale") or 8
		self.smooth = cfg.getboolean("WINDOW", "smooth") or False
		self.fps = cfg.getint("WINDOW", "fps") or 24
		self.threads = cfg.getint("RENDER", "threads") or mp.cpu_count()
		self.speed_move = cfg.getfloat("INPUT", "speed_move") or 10
		self.speed_mouse = cfg.getfloat("INPUT", "speed_mouse") or 10
		self.max_pitch = cfg.getfloat("INPUT", "max_pitch") or 0

		# Configure Pygame and the main screen as well as the camera and thread pool that will be used to update the window
		pg.init()
		pg.display.set_caption("Voxel Tracer")
		self.rect = vec2(self.width, self.height)
		self.rect_win = self.rect * self.scale
		self.screen = pg.display.set_mode(self.rect_win.tuple(), pg.HWSURFACE)
		self.canvas = pg.Surface(self.rect.tuple(), pg.HWSURFACE)
		self.font = pg.font.SysFont(None, 24)
		self.clock = pg.time.Clock()
		self.pool = mp.Pool(processes = self.threads)
		self.cam = Camera()
		self.mouselook = True
		self.running = True

		# Main loop, limited by FPS with a slower clock when the window isn't focused
		while self.running:
			for obj in data.objects:
				if obj.cam_pos:
					self.update(obj)
				obj.unstick()

			fps = pg.mouse.get_focused() and self.fps or math.trunc(self.fps / 5)
			self.clock.tick(fps)

	# Render a new frame from the perspective of the main object, move the object and preform other actions based on input
	def update(self, obj: data.Object):
		pg.mouse.set_visible(not self.mouselook)
		keys = pg.key.get_pressed()
		mods = pg.key.get_mods()
		d = obj.rot.dir(False)
		units = self.clock.get_time() / 1000 * self.speed_move
		units_mouse = self.speed_mouse / 1000

		# Render: Request the camera to draw new tiles, add the image of each tile to the canvas at its correct position once all segments have been received
		tiles = []
		self.cam.move(obj.pos + vec3(obj.cam_pos.x * d.x, obj.cam_pos.y, obj.cam_pos.x * d.z), obj.rot)
		result = self.pool.map(self.cam.draw, range(self.threads))
		for i in range(len(result)):
			srf = pg.image.frombytes(result[i], (self.width, math.ceil(self.height / self.threads)), "RGBA")
			tiles.append((srf, (0, math.ceil(self.height / self.threads) * i)))
		self.canvas.blits(tiles)

		# Render: Draw the canvas and info text onto the screen
		canvas = self.smooth and pg.transform.smoothscale(self.canvas, self.rect_win.tuple()) or pg.transform.scale(self.canvas, self.rect_win.tuple())
		text_info = str(self.width) + " x " + str(self.height) + " (" + str(self.width * self.height) + "px) - " + str(math.trunc(self.clock.get_fps())) + " / " + str(self.fps) + " FPS"
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
				obj.move(vec3(+d.z, 0, -d.x) * e.x * 5)
				obj.move(vec3(+d.x, +d.y, +d.z) * e.y * 5)
			if e.type == pg.MOUSEMOTION and self.mouselook:
				center = self.rect_win / 2
				x, y = pg.mouse.get_pos()
				ofs = vec2(center.x - x, center.y - y)
				rot = vec3(0, +ofs.y, -ofs.x)
				obj.rotate(rot * units_mouse, self.max_pitch)
				pg.mouse.set_pos((center.x, center.y))

		# Input, ongoing events: Camera movement, camera rotation
		if keys[pg.K_w]:
			obj.move(vec3(+d.x, +d.y, +d.z) * units)
		if keys[pg.K_s]:
			obj.move(vec3(-d.x, -d.y, -d.z) * units)
		if keys[pg.K_a]:
			obj.move(vec3(-d.z, 0, +d.x) * units)
		if keys[pg.K_d]:
			obj.move(vec3(+d.z, 0, -d.x) * units)
		if keys[pg.K_r]:
			obj.move(vec3(0, +1, 0) * units)
		if keys[pg.K_f]:
			obj.move(vec3(0, -1, 0) * units)
		if keys[pg.K_UP]:
			obj.rotate(vec3(0, +5, 0) * units, self.max_pitch)
		if keys[pg.K_DOWN]:
			obj.rotate(vec3(0, -5, 0) * units, self.max_pitch)
		if keys[pg.K_LEFT]:
			obj.rotate(vec3(0, 0, -5) * units, self.max_pitch)
		if keys[pg.K_RIGHT]:
			obj.rotate(vec3(0, 0, +5) * units, self.max_pitch)

# Load the default world and create the main window
builtin.world()
win = Window()
