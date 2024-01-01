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
		# Read relevant settings
		cfg_input = cfg.item("INPUT")
		cfg_window = cfg.item("WINDOW")
		cfg_render = cfg.item("RENDER")
		self.speed_move = float(cfg_input["speed_move"]) or 10
		self.speed_mouse = float(cfg_input["speed_mouse"]) or 10
		self.width = int(cfg_window["width"]) or 96
		self.height = int(cfg_window["height"]) or 54
		self.scale = int(cfg_window["scale"]) or 4
		self.smooth = int(cfg_window["smooth"]) or 0
		self.fps = int(cfg_window["fps"]) or 30
		self.threads = int(cfg_render["threads"]) or mp.cpu_count()
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

		# Start the main loop
		while self.running:
			self.input()
			self.update()

			# Enforce the FPS limit, use a slower clock when the window is not focused
			fps = pg.mouse.get_focused() and self.fps or int(self.fps / 5)
			self.clock.tick(fps)

	def input(self):
		pg.mouse.set_visible(not self.mouselook)
		keys = pg.key.get_pressed()
		mods = pg.key.get_mods()
		d = self.cam.rot.dir(False)
		units = self.clock.get_time() / 1000 * self.speed_move
		units_mouse = self.speed_mouse / 1000

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
				if e.key == pg.K_TAB:
					self.mouselook = not self.mouselook
			if e.type == pg.MOUSEWHEEL:
				self.cam.move(vec3(+d.z, 0, -d.x) * e.x * 5)
				self.cam.move(vec3(+d.x, +d.y, +d.z) * e.y * 5)
			if e.type == pg.MOUSEMOTION and self.mouselook:
				center = self.rect_win / 2
				x, y = pg.mouse.get_pos()
				ofs = vec2(center.x - x, center.y - y)
				rot = vec3(0, +ofs.y, -ofs.x)
				self.cam.rotate(rot * units_mouse)
				pg.mouse.set_pos((center.x, center.y))

		# Ongoing events: Camera movement, camera rotation
		if keys[pg.K_w]:
			self.cam.move(vec3(+d.x, +d.y, +d.z) * units)
		if keys[pg.K_s]:
			self.cam.move(vec3(-d.x, -d.y, -d.z) * units)
		if keys[pg.K_a]:
			self.cam.move(vec3(-d.z, 0, +d.x) * units)
		if keys[pg.K_d]:
			self.cam.move(vec3(+d.z, 0, -d.x) * units)
		if keys[pg.K_r]:
			self.cam.move(vec3(0, +1, 0) * units)
		if keys[pg.K_f]:
			self.cam.move(vec3(0, -1, 0) * units)
		if keys[pg.K_UP]:
			self.cam.rotate(vec3(0, +5, 0) * units)
		if keys[pg.K_DOWN]:
			self.cam.rotate(vec3(0, -5, 0) * units)
		if keys[pg.K_LEFT]:
			self.cam.rotate(vec3(0, 0, -5) * units)
		if keys[pg.K_RIGHT]:
			self.cam.rotate(vec3(0, 0, +5) * units)

	def update(self):
		# Request the camera to draw new tiles, add the image of each tile to the canvas at its correct position once all segments have been received
		tiles = []
		result = self.cam.pool(self.pool)
		for i in range(len(result)):
			srf = pg.image.frombytes(result[i], (self.width, math.ceil(self.height / self.threads)), "RGBA")
			tiles.append((srf, (0, math.ceil(self.height / self.threads) * i)))
		self.canvas.blits(tiles)

		# Draw the canvas and info text onto the screen
		canvas = self.smooth and pg.transform.smoothscale(self.canvas, self.rect_win.tuple()) or pg.transform.scale(self.canvas, self.rect_win.tuple())
		text_info = str(self.width) + " x " + str(self.height) + " (" + str(self.width * self.height) + "px) - " + str(int(self.clock.get_fps())) + " / " + str(self.fps) + " FPS"
		text = self.font.render(text_info, True, (255, 255, 255))
		self.screen.blit(canvas, (0, 0))
		self.screen.blit(text, (0, 0))
		pg.display.update()

# Create the camera and main window to start Pygame
builtin.world()
cam = camera.Camera(builtin.material_sky)
win = Window(cam)
