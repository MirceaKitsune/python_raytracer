#!/usr/bin/python3
from lib import *

import multiprocessing as mp
import pygame as pg
import math

import builtin
import data
import camera

class Window:
	def __init__(self, cam: camera.Camera):
		self.width = cfg.getint("WINDOW", "width") or 96
		self.height = cfg.getint("WINDOW", "height") or 64
		self.scale = cfg.getint("WINDOW", "scale") or 8
		self.smooth = cfg.getboolean("WINDOW", "smooth") or False
		self.fps = cfg.getint("WINDOW", "fps") or 24
		self.threads = cfg.getint("RENDER", "threads") or mp.cpu_count()
		self.speed_move = cfg.getfloat("INPUT", "speed_move") or 10
		self.speed_mouse = cfg.getfloat("INPUT", "speed_mouse") or 10
		self.max_pitch = cfg.getfloat("INPUT", "max_pitch") or 0
		self.mouselook = True

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
		self.cam = cam
		self.running = True

		# Main loop, limited by FPS with a slower clock when the window isn't focused
		while self.running:
			for obj in data.objects:
				if obj.cam_pos:
					self.update(obj)
					break

			fps = pg.mouse.get_focused() and self.fps or int(self.fps / 5)
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
		result = self.cam.render(obj.pos + vec3(obj.cam_pos.x * d.x, obj.cam_pos.y, obj.cam_pos.x * d.z), obj.rot, self.pool)
		for i in range(len(result)):
			srf = pg.image.frombytes(result[i], (self.width, math.ceil(self.height / self.threads)), "RGBA")
			tiles.append((srf, (0, math.ceil(self.height / self.threads) * i)))
		self.canvas.blits(tiles)

		# Render: Draw the canvas and info text onto the screen
		canvas = self.smooth and pg.transform.smoothscale(self.canvas, self.rect_win.tuple()) or pg.transform.scale(self.canvas, self.rect_win.tuple())
		text_info = str(self.width) + " x " + str(self.height) + " (" + str(self.width * self.height) + "px) - " + str(int(self.clock.get_fps())) + " / " + str(self.fps) + " FPS"
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

# Create the camera and main window to start Pygame
builtin.world()
cam = camera.Camera(builtin.material_sky)
win = Window(cam)
