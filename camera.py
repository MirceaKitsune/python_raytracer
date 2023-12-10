#!/usr/bin/python3
from lib import *

import multiprocessing as mp
import tkinter as tk
import random

import data

class Camera:
	def __init__(self, data: data.Voxels, **settings):
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
		# Pixel position is converted to a ray velocity based on the lens distorsion defined by FOV and randomly offset by DOF
		px_col = None
		px_pos = line_to_rect(i, self.width)
		lens_x = (-0.5 + px_pos.x / self.width) / self.proportions * ((self.fov + rand(self.dof)) * math.pi / 4)
		lens_y = (-0.5 + px_pos.y / self.height) * self.proportions * ((self.fov + rand(self.dof)) * math.pi / 4)

		# Randomly offset the ray's angle based on the DOF setting, fetch its direction and use it as the ray velocity
		# Velocity must be normalized as voxels need to be checked at all integer positions, the speed of light is always 1
		# Therefore at least one axis must be precisely -1 or +1 while others can be anything in that range, lower speeds are scaled accordingly based on the largest
		ray_rot = self.rot.clone()
		ray_rot = ray_rot.rotate(vec3(0, -lens_y, +lens_x))
		ray_dir = ray_rot.dir()
		ray_dir.normalize()

		# Ray data is kept in a data store so it can be easily delivered to material functions and support custom properties
		ray = store(
			col = None,
			pos = self.pos + ray_dir * vec3(self.dist_min, self.dist_min, self.dist_min),
			vel = ray_dir,
			step = 0,
			life = self.dist_max - self.dist_min,
			hits = 0,
		)

		# Each step the ray advances through space by adding its velocity to its position, starting from the minimum distance and going up to the maximum distance
		# As voxels exist at integer numbers, the float position is rounded to check if a voxel is located at this spot
		# If a material is found, its function is called which can modify any of the ray properties provided
		while ray.step < ray.life:
			ray.step += 1
			ray.pos += ray.vel
			vox = self.data.get_voxel(ray.pos.round())
			if vox:
				ray.hits += 1
				mat = self.data.get_material(vox)
				mat.function(ray, mat)
			if self.hits > 0 and ray.hits >= self.hits:
				break

		# Once ray calculations are done, return the resulting color in hex format or black if no changes were made
		return ray.col and ray.col.get_hex() or "000000"

	def get(self, width, height, pool, chunks):
		return pool.map(self.trace, range(0, width * height))
