#!/usr/bin/python3
from lib import *

import multiprocessing as mp
import time as t
import tkinter as tk

import data
import camera

class Window:
	def __init__(self, objects: list, **settings):
		# Store relevant settings
		self.width = int(settings["width"] or 96)
		self.height = int(settings["height"] or 54)
		self.scale = int(settings["scale"] or 4)
		self.fps = int(settings["fps"] or 30)
		self.iris = float(settings["iris"] or 0)
		self.blur = float(settings["blur"] or 0)
		self.threads = int(settings["threads"] or mp.cpu_count())

		# Setup the camera and thread pool that will be used to update this window
		self.pool = mp.Pool(processes = self.threads)
		self.cam = camera.Camera(objects, **settings)

		# Configure TK and elements
		self.root = tk.Tk()
		self.root.title("Voxel Tracer")
		self.root.geometry(str(self.width * self.scale) + "x" + str(self.height * self.scale))
		# self.root.config(cursor="none")
		# self.root.overrideredirect(True)
		self.root.bind("<Escape>", exit)
		self.root.bind("<KeyPress>", self.onKeyPress)
		self.root.bind("<Motion>", self.onMouseMove)

		self.canvas = tk.Canvas(self.root, width = self.width * self.scale, height = self.height * self.scale)
		self.canvas.pack()

		# Configure the pixel elements on the canvas at their default black color, use a pixel cache to remember pixel colors by index
		# Index represents 2D positions, the range is ordered to represent all pixels read from left-to-right and up-to-down
		self.pixels = []
		self.canvas_pixels = []
		for i in range(0, self.width * self.height):
			pos = index_vec2(i, self.width)
			pos_min = pos * self.scale
			pos_max = pos_min + self.scale
			canvas_rect = self.canvas.create_rectangle(pos_min.x, pos_min.y, pos_max.x, pos_max.y, fill = "#000000", width = 0)
			self.canvas_pixels.append(canvas_rect)
			self.pixels.append(rgb(0, 0, 0))

		# Configure info text
		self.canvas_info = self.canvas.create_text(10, 10, font = ("Purisa", 8) , anchor = "nw", fill = "#ffffff")

		# Start the main loop and update function, a timer is used to keep track of update rate
		self.time = 0
		self.root.after_idle(self.update)
		self.root.mainloop()

	def onKeyPress(self, event):
		# Movement keys
		if event.keysym.lower() in "wasdrf":
			d = self.cam.rot.dir(False)
			if event.keysym.lower() == "w":
				self.cam.pos += vec3(+d.x, +d.y, +d.z)
			elif event.keysym.lower() == "s":
				self.cam.pos += vec3(-d.x, -d.y, -d.z)
			elif event.keysym.lower() == "a":
				self.cam.pos += vec3(-d.z, 0, +d.x)
			elif event.keysym.lower() == "d":
				self.cam.pos += vec3(+d.z, 0, -d.x)
			elif event.keysym.lower() == "r":
				self.cam.pos += vec3(0, +1, 0)
			elif event.keysym.lower() == "f":
				self.cam.pos += vec3(0, -1, 0)

		# Rotation keys
		elif event.keysym.lower() in "up" + "down" + "left" + "right":
			deg = 90 / 16
			if event.keysym.lower() == "up" and (self.cam.rot.y < 90 or self.cam.rot.y >= 270):
				self.cam.rot = self.cam.rot.rotate(vec3(0, +deg, 0))
			elif event.keysym.lower() == "down" and (self.cam.rot.y <= 90 or self.cam.rot.y > 270):
				self.cam.rot = self.cam.rot.rotate(vec3(0, -deg, 0))
			elif event.keysym.lower() == "left":
				self.cam.rot = self.cam.rot.rotate(vec3(0, 0, -deg))
			elif event.keysym.lower() == "right":
				self.cam.rot = self.cam.rot.rotate(vec3(0, 0, +deg))

	def onMouseMove(self, event):
		pass

	def update(self):
		# Execute updates once the amount of time passed since the last update is greater than the desired FPS
		time = t.time()
		if self.time + (1 / self.fps) < time:
			delay = time - self.time
			self.time = time

			# Request the camera to compute new pixels, then update each canvas rectangle element to display the new color data
			# The 2D position of each pixel is stored as its index and implicitly known here
			# The color burn effect is used to improve viewport performance by probabilistically skipping redraws of pixels who's color hasn't changes a lot
			result = self.cam.pool(self.pool, range(0, self.width * self.height))
			for i, c in enumerate(result):
				if c and c != self.pixels[i]:
					col = hex_to_rgb(c)
					col_old = self.pixels[i]
					threshold = self.iris * random.random()
					if abs((col.r - col_old.r) / 255) > threshold or abs((col.g - col_old.g) / 255) > threshold or abs((col.b - col_old.b) / 255) > threshold:
						col = col.mix(col_old, self.blur)
						item = self.canvas_pixels[i]
						self.canvas.itemconfig(item, fill = "#" + col.get_hex())
						self.pixels[i] = col

			# Measure the time before and after the update to deduce practical FPS
			info_text = str(self.width) + " x " + str(self.height) + " (" + str(self.width * self.height) + "px) - " + str(int(1 / delay)) + " / " + str(self.fps) + " FPS"
			self.canvas.itemconfig(self.canvas_info, text = info_text)

		self.root.after(1, self.update)

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
	height = 54,
	scale = 8,
	fps = 30,
	fov = 90,
	dof = 1,
	fog = 0.5,
	skip = 0.75,
	iris = 0.5,
	blur = 0.25,
	dist_min = 2,
	dist_max = 48,
	terminate_hits = 2,
	terminate_dist = 0.5,
	threads = 4,
)
