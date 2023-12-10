#!/usr/bin/python3
from lib import *

import multiprocessing as mp
import tkinter as tk
import random

import data

class Camera:
	def __init__(self, settings: dict, data: data.Voxels):
		# Store relevant settings
		self.width = int(settings["width"] or 120)
		self.height = int(settings["height"] or 60)
		self.skip = float(settings["skip"] or 0)
		self.fov = float(settings["fov"] or 90)
		self.dof = float(settings["dof"] or 0)
		self.hits = int(settings["hits"] or 0)
		self.dist_min = int(settings["dist_min"] or 2)
		self.dist_max = int(settings["dist_max"] or 8)
		self.data = data
		self.pos = vec3(0, 0, 0)
		self.rot = vec3(0, 0, 0)
		self.proportions = ((self.width + self.height) / 2) / max(self.width, self.height)

	def move(axis: int, amount: float):
		self.pos += self.rot.dir() * vec3(amount, amount, amount)

	def rotate(rot: vec3):
		self.rot = self.rot.rotate(rot)

	def trace(self, i):
		# Allow probabilistically skiping pixel recalculation each frame
		if self.skip > random.random():
			return ""

		# Obtain the 2D position of this pixel in the viewport as: X = -1 is left, X = +1 is right, Y = -1 is down, Y = +1 is up
		# Pixel position is then converted to a ray velocity based on the lens distorsion defined by the FOV
		px_col = None
		px_pos = line_to_rect(i, self.width)
		lens_x = (-0.5 + px_pos.x / self.width) / self.proportions * (self.fov * math.pi / 4)
		lens_y = (-0.5 + px_pos.y / self.height) * self.proportions * (self.fov * math.pi / 4)
		ray_rot = vec3(self.rot.x, self.rot.y, self.rot.z)
		ray_rot = ray_rot.rotate(vec3(0, -lens_y, +lens_x))

		# Randomly offset the ray's angle based on the DOF setting, fetch its direction and use it as the ray velocity
		# Velocity must be normalized as voxels need to be checked at all integer positions, the speed of light is always 1
		# Therefore at least one axis must be precisely -1 or +1 while others can be anything in that range, lower speeds are scaled accordingly based on the largest
		ray_rot = ray_rot.rotate(vec3(0, rand(self.dof), rand(self.dof)))
		vel = ray_rot.dir()
		vel.normalize()

		# Each step the ray advances through space by adding its velocity to its position, starting from the minimum distance and going up to the maximum distance
		# As voxels exist at integer numbers, the float position is rounded to check if a voxel is located at this spot
		# If a material is found, its function is called and returns the modified ray properties provided
		col = None
		pos = self.pos + vel * vec3(self.dist_min, self.dist_min, self.dist_min)
		hits = 0
		for step in range(0, self.dist_max - self.dist_min):
			pos += vel
			pos_int = vec3(round(pos.x), round(pos.y), round(pos.z))
			mat = self.data.get_voxel(pos_int)
			if mat:
				hits += 1
				mat_data = self.data.get_material(mat)
				pos, vel, col = mat_data.function(pos, vel, col, step / (self.dist_max - self.dist_min), hits, mat_data.data)
			if self.hits > 0 and hits >= self.hits:
				break

		# Once ray calculations are done, return the resulting color in hex format or black if no changes were made
		return col and col.get_hex() or "000000"

	def get(self, width, height, pool, chunks):
		return pool.map(self.trace, range(0, width * height))
