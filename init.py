#!/usr/bin/python3
from lib import *

import multiprocessing as mp
import time as t
import tkinter as tk

import data
import camera

class Window:
	def __init__(self, settings: dict, data: data.Voxels):
		# Store relevant settings
		self.width = int(settings["width"] or 120)
		self.height = int(settings["height"] or 60)
		self.scale = int(settings["scale"] or 4)
		self.fps = int(settings["fps"] or 30)
		self.threads = int(settings["threads"] or mp.cpu_count())

		# Setup the camera and thread pool that will be used to update this window
		self.pool = mp.Pool(processes = self.threads)
		self.cam = camera.Camera(settings, data)

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

		# Configure the pixel elements on the canvas
		self.canvas_pixels = {}
		for x in range(0, self.width):
			for y in range(0, self.height):
				pos = vec2(x, y)
				pos_min = vec2(pos.x * self.scale, pos.y * self.scale)
				pos_max = vec2(pos_min.x + self.scale, pos_min.y + self.scale)
				col = "#" + rgb(2, 0, 0).get_hex()
				self.canvas_pixels[pos.get_str()] = self.canvas.create_rectangle(pos_min.x, pos_min.y, pos_max.x, pos_max.y, fill = col, width = 0)

		# Configure info text
		self.text_info = self.canvas.create_text(10, 10, font = ("Purisa", self.scale) , anchor = "nw", fill = "#ffffff")

		# Start the main loop and update function
		self.root.after(0, self.update)
		self.root.mainloop()

	def onKeyPress(self, event):
		# Movement keys
		if event.keysym.lower() in "wasdrf":
			d = self.cam.rot.dir()
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
			if event.keysym.lower() == "up" and (self.cam.rot.y < 90 or self.cam.rot.y >= 270):
				self.cam.rot.rot(vec3(0, +11.25, 0))
			elif event.keysym.lower() == "down" and (self.cam.rot.y <= 90 or self.cam.rot.y > 270):
				self.cam.rot.rot(vec3(0, -11.25, 0))
			elif event.keysym.lower() == "left":
				self.cam.rot.rot(vec3(0, 0, -11.25))
			elif event.keysym.lower() == "right":
				self.cam.rot.rot(vec3(0, 0, +11.25))

	def onMouseMove(self, event):
		pass

	def update(self):
		time_start = t.time()

		# Request the camera to compute new pixels, then update each canvas rectangle element to display the new color data
		# The 2D position of each pixel is extracted from its index in the array
		result = self.cam.get(self.width, self.height, self.pool, self.threads)
		for i, c in enumerate(result):
			if c:
				px = line_to_rect(i, self.width)
				item = self.canvas_pixels[vec2(px.x, px.y).get_str()]
				self.canvas.itemconfig(item, fill = "#" + c)

		# Measure the time before and after the update to deduce practical FPS
		# Reschedule the function to aim for the chosen FPS and update the info text
		time_end = t.time()
		time_next = round(1000 / self.fps / (1 + time_end - time_start))
		fps_text = str(self.width) + " x " + str(self.height) + " (" + str(self.width * self.height) + "px) - " + str(time_next) + " / " + str(self.fps) + " FPS"
		fps_col = time_next >= self.fps + 10 and "#00ff00" or time_next <= self.fps - 10 and "#ff0000" or "#ffff00"
		self.canvas.itemconfig(self.text_info, text = fps_text)
		self.canvas.itemconfig(self.text_info, fill = fps_col)
		self.root.after(int(time_next), self.update)

# Spawn test environment
settings = data.Voxels()
settings.register_material("solid_red", data.material_default, { "albedo": rgb(255, 0, 0), "roughness": 0.1 })
settings.register_material("solid_green", data.material_default, { "albedo": rgb(0, 255, 0), "roughness": 0.1 })
settings.register_material("solid_blue", data.material_default, { "albedo": rgb(0, 0, 255), "roughness": 0.1 })
settings.set_voxel_area(vec3(-2, -2, 8), vec3(2, 2, 8), "solid_red")
settings.set_voxel_area(vec3(8, -2, -2), vec3(8, 2, 2), "solid_green")
settings.set_voxel_area(vec3(-2, -8, -2), vec3(2, -8, 2), "solid_blue")
Window({
	"width": 120,
	"height": 60,
	"scale": 8,
	"fps": 30,
	"samples_min": 0,
	"samples_max": 4,
	"fov": 90,
	"dof": 0.5,
	"dist_min": 2,
	"dist_max": 16,
	"threads": 4,
}, settings)
