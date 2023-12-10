#!/usr/bin/python3
from lib import *

import multiprocessing as mp
import tkinter as tk

import data

class Camera:
	def __init__(self, settings: dict, data: data.Voxels):
		# Store relevant settings
		self.width = int(settings["width"] or 120)
		self.height = int(settings["height"] or 60)
		self.samples_min = int(settings["samples_min"] or 0)
		self.samples_max = int(settings["samples_max"] or 1)
		self.fov = float(settings["fov"] or 90)
		self.dof = float(settings["dof"] or 0)
		self.dist_min = int(settings["dist_min"] or 2)
		self.dist_max = int(settings["dist_max"] or 8)
		self.data = data
		self.pos = vec3(0, 0, 0)
		self.rot = vec3(0, 0, 0)
		self.proportions = ((self.width + self.height) / 2) / max(self.width, self.height)

	def move(axis: int, amount: float):
		self.pos += self.rot.dir() * vec3(amount, amount, amount)

	def rotate(rot: vec3):
		self.rot.rot(rot)

	def trace(self, i):
		# Allow skiping pixel calculation for sample counts lesser than or equal to zero
		samples_count = random.randint(self.samples_min, self.samples_max)
		if samples_count <= 0:
			return ""

		# Obtain the 2D position of this pixel in the viewport as: X = -1 is left, X = +1 is right, Y = -1 is down, Y = +1 is up
		# Pixel position is then converted to a ray velocity based on the lens distorsion defined by the FOV
		px_col = None
		px_pos = line_to_rect(i, self.width)
		lens_x = (-0.5 + px_pos.x / self.width) / self.proportions * (self.fov * math.pi / 4)
		lens_y = (-0.5 + px_pos.y / self.height) * self.proportions * (self.fov * math.pi / 4)
		ray_rot = vec3(self.rot.x, self.rot.y, self.rot.z)
		ray_rot.rot(vec3(0, -lens_y, +lens_x))

		for sample in range(0, samples_count):
			# Randomly offset the ray's angle based on the DOF setting, fetch its direction and use it as the ray velocity
			# Velocity must be normalized as voxels need to be checked at all integer positions, the speed of light is always 1
			# Therefore at least one axis must be precisely -1 or +1 while others can be anything in that range, lower speeds are scaled accordingly based on the largest
			ray_rot.rot(vec3(0, rand(self.dof), rand(self.dof)))
			vel = ray_rot.dir()
			vel.normalize()

			# Each step the ray advances through space by adding its velocity to its position
			# As voxels exist at integer numbers, the float position is rounded to check if a voxel is located at this spot
			# If a material is found, its function is called and returns the modified ray properties provided
			pos = self.pos
			col = rgb(0, 0, 0)
			for step in range(0, self.dist_max):
				pos += vel
				if step >= self.dist_min:
					pos_int = vec3(round(pos.x), round(pos.y), round(pos.z))
					mat = self.data.get_voxel(pos_int)
					if mat:
						mat_data = self.data.get_material(mat)
						pos, vel, col = mat_data.function(pos, vel, col, mat_data.data)

			# Mix the color obtained from this sample into the final color of the pixel, if a color wasn't previously set use the sample color directly
			# Once all samples are done return the resulting color in hex format to the main thread
			px_col = px_col and px_col.mix(col, 0.5) or col
		return px_col.get_hex()

	def get(self, width, height, pool, chunks):
		return pool.map(self.trace, range(0, width * height))
