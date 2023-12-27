#!/usr/bin/python3
from lib import *

import multiprocessing as mp
import time as t
import pygame as pg

import data
import camera

class Window:
	def __init__(self, objects: list, **settings):
		# Store relevant settings
		self.width = int(settings["width"] or 96)
		self.height = int(settings["height"] or 54)
		self.scale = int(settings["scale"] or 4)
		self.smooth = int(settings["smooth"] or False)
		self.fps = int(settings["fps"] or 30)
		self.blur = float(settings["blur"] or 0)
		self.threads = int(settings["threads"] or mp.cpu_count())

		# Setup the camera and thread pool that will be used to update this window
		self.pool = mp.Pool(processes = self.threads)
		self.cam = camera.Camera(objects, **settings)

		# Configure the pixel elements on the canvas at their default black color, use a pixel cache to remember pixel colors by index
		# Index represents 2D positions, the range is ordered to represent all pixels read from left-to-right and up-to-down
		self.pixels = [rgb(0, 0, 0)] * (self.width * self.height)
		self.rect = vec2(self.width, self.height)
		self.rect_win = self.rect * self.scale

		# Configure and start Pygame
		pg.init()
		pg.display.set_caption("Voxel Tracer")
		self.screen = pg.display.set_mode(self.rect_win.tuple())
		self.canvas = pg.Surface(self.rect.tuple())
		self.font = pg.font.SysFont(None, 24)
		self.clock = pg.time.Clock()
		self.running = True

		# Start the main loop
		while self.running:
			for event in pg.event.get():
				self.event(event)
			self.update()

	def event(self, event):
		if event.type == pg.QUIT:
			self.running = False

		if event.type == pg.KEYDOWN:
			d = self.cam.rot.dir(False)
			deg = 90 / 16

			# Quit key
			if event.key == pg.K_ESCAPE:
				self.running = False

			# Movement keys
			elif event.key == pg.K_w:
				self.cam.pos += vec3(+d.x, +d.y, +d.z)
			elif event.key == pg.K_s:
				self.cam.pos += vec3(-d.x, -d.y, -d.z)
			elif event.key == pg.K_a:
				self.cam.pos += vec3(-d.z, 0, +d.x)
			elif event.key == pg.K_d:
				self.cam.pos += vec3(+d.z, 0, -d.x)
			elif event.key == pg.K_r:
				self.cam.pos += vec3(0, +1, 0)
			elif event.key == pg.K_f:
				self.cam.pos += vec3(0, -1, 0)

			# Rotation keys
			elif event.key == pg.K_UP and (self.cam.rot.y < 90 or self.cam.rot.y >= 270):
				self.cam.rot = self.cam.rot.rotate(vec3(0, +deg, 0))
			elif event.key == pg.K_DOWN and (self.cam.rot.y <= 90 or self.cam.rot.y > 270):
				self.cam.rot = self.cam.rot.rotate(vec3(0, -deg, 0))
			elif event.key == pg.K_LEFT:
				self.cam.rot = self.cam.rot.rotate(vec3(0, 0, -deg))
			elif event.key == pg.K_RIGHT:
				self.cam.rot = self.cam.rot.rotate(vec3(0, 0, +deg))

	def update(self):
		# Request the camera to compute new pixels, then update each canvas rectangle element to display the new color data
		# The 2D position of each pixel is stored as its index and implicitly known here
		# The color burn effect is used to improve viewport performance by probabilistically skipping redraws of pixels who's color hasn't changes a lot
		result = self.cam.pool(self.pool)
		for i, c in enumerate(result):
			if c and c != self.pixels[i]:
				col = hex_to_rgb(c)
				col = col.mix(self.pixels[i], self.blur)
				pos = index_vec2(i, self.width)
				self.canvas.set_at(pos.tuple(), col.tuple())

				# Adjust the weight of this pixel based on the color difference, the weight is a 0 to 1 range representing changes in each channel (255 * 3 = 765)
				diff = (abs(col.r - self.pixels[i].r) + abs(col.g - self.pixels[i].g) + abs(col.b - self.pixels[i].b)) / 765
				self.cam.set_weight(i, diff)
				self.pixels[i] = col

		# Draw the canvas and info text onto the screen
		canvas = self.smooth and pg.transform.smoothscale(self.canvas, self.rect_win.tuple()) or pg.transform.scale(self.canvas, self.rect_win.tuple())
		text_info = str(self.width) + " x " + str(self.height) + " (" + str(self.width * self.height) + "px) - " + str(int(self.clock.get_fps())) + " / " + str(self.fps) + " FPS"
		text = self.font.render(text_info, True, (255, 255, 255))
		self.screen.blit(canvas, (0, 0))
		self.screen.blit(text, (0, 0))
		pg.display.update()

		# Wait for the next tick based on the desired FPS
		self.clock.tick(self.fps)

# Spawn test environment
mat_red = data.Material(
	function = data.material_default,
	albedo = rgb(255, 0, 0),
	roughness = 0.1,
	translucency = 0,
	group = "solid",
)
mat_green = data.Material(
	function = data.material_default,
	albedo = rgb(0, 255, 0),
	roughness = 0.1,
	translucency = 0,
	group = "solid",
)
mat_blue = data.Material(
	function = data.material_default,
	albedo = rgb(0, 0, 255),
	roughness = 0.1,
	translucency = 0,
	group = "solid",
)

obj_environment = data.Object(origin = vec3(0, 0, 0), size = vec3(16, 16, 16), active = True)
obj_environment.set_voxel_area(vec3(0, 0, 0), vec3(15, 15, 0), mat_red)
obj_environment.set_voxel_area(vec3(0, 0, 0), vec3(0, 15, 15), mat_green)
obj_environment.set_voxel_area(vec3(0, 15, 0), vec3(15, 15, 15), mat_blue)

objects = []
objects.append(obj_environment)

Window(objects,
	width = 96,
	height = 64,
	scale = 8,
	smooth = False,
	fps = 24,
	fov = 90,
	dof = 1,
	fog = 0.5,
	iris = 0.5,
	blur = 0.5,
	dist_min = 2,
	dist_max = 192,
	terminate_hits = 1,
	terminate_dist = 0.5,
	threads = 0,
)
