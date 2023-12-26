#!/usr/bin/python3
from lib import *

import multiprocessing as mp
import tkinter as tk
import random

import data

class Camera:
	def __init__(self, objects: list, **settings):
		# Store relevant settings
		self.width = int(settings["width"] or 120)
		self.height = int(settings["height"] or 60)
		self.fov = float(settings["fov"] or 90)
		self.dof = float(settings["dof"] or 0)
		self.fog = float(settings["fog"] or 0)
		self.iris = float(settings["iris"] or 0)
		self.dist_min = int(settings["dist_min"] or 0)
		self.dist_max = int(settings["dist_max"] or 24)
		self.terminate_hits = float(settings["terminate_hits"] or 0)
		self.terminate_dist = float(settings["terminate_dist"] or 0)
		self.objects = objects
		self.pos = vec3(0, 0, 0)
		self.rot = vec3(0, 0, 0)
		self.proportions = ((self.width + self.height) / 2) / max(self.width, self.height)
		self.weights = [1] * (self.width * self.height)

	def set_weight(self, i: int, amount: float):
		self.weights[i] = amount

	def move(self, axis: int, amount: float):
		self.pos += self.rot.dir(False) * amount

	def rotate(self, rot: vec3):
		self.rot = self.rot.rotate(rot)

	def trace(self, i):
		# Probabilistically skip pixel recalculation based on weight
		if (1 - self.weights[i]) * self.iris > random.random():
			return None

		# Obtain the 2D position of this pixel in the viewport as: X = -1 is left, X = +1 is right, Y = -1 is down, Y = +1 is up
		pos = index_vec2(i, self.width)
		ofs_x = (-0.5 + pos.x / self.width) * 2
		ofs_y = (-0.5 + pos.y / self.height) * 2

		# Pixel position is converted to a ray velocity based on the lens distorsion defined by FOV and randomly offset by DOF
		lens_fov = (self.fov + rand(self.dof)) * math.pi / 8
		lens_x = ofs_x / self.proportions * lens_fov
		lens_y = ofs_y * self.proportions * lens_fov

		# Randomly offset the ray's angle based on the DOF setting, fetch its direction and use it as the ray velocity
		# Velocity must be normalized as voxels need to be checked at all integer positions, the speed of light is always 1
		# Therefore at least one axis must be precisely -1 or +1 while others can be anything in that range, lower speeds are scaled accordingly based on the largest
		ray_rot = self.rot.rotate(vec3(0, -lens_y, +lens_x))
		ray_dir = ray_rot.dir(True)
		ray_dir = ray_dir.normalize()

		# Ray data is kept in a data store so it can be easily delivered to material functions and support custom properties
		ray = store(
			col = None,
			alpha = 1,
			pos = self.pos + ray_dir * self.dist_min,
			vel = ray_dir,
			step = 0,
			life = self.dist_max - self.dist_min,
			hits = 0,
			neighbors = [],
		)

		# Each step the ray advances through space by adding its velocity to its position, starting from the minimum distance and going up to the maximum distance
		# As voxels exist at integer numbers, the float position is rounded to check if a voxel is located at this spot
		# If a material is found, its function is called which can modify any of the ray properties provided
		# Note that diagonal steps can be preformed which allows penetrating through 1 voxel thick corners, checking in a stair pattern isn't done for performance reasons
		while ray.step < ray.life:
			ray.step += 1
			ray.pos += ray.vel
			pos_int = ray.pos.int()
			for obj in self.objects:
				if obj.active and obj.intersects(pos_int):
					pos = obj.pos_rel(pos_int)
					mat = obj.get_voxel(pos)
					if mat:
						mat.function(ray, mat)

			# Terminate this ray earlier in some circumstances to improve performance
			if ray.hits > 0 and self.terminate_hits / ray.hits < random.random():
				break
			elif ray.step / ray.life > 1 - self.terminate_dist * random.random():
				break
			elif ray.step / ray.life > 1 - self.fog:
				ray.alpha *= self.fog

		# Once ray calculations are done, return the resulting color in hex format or black if no changes were made
		return ray.col and ray.col.get_hex() or "000000"

	def pool(self, pool):
		return pool.map(self.trace, range(0, self.width * self.height))
