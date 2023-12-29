#!/usr/bin/python3
from lib import *

import multiprocessing as mp
import pygame as pg
import math
import random

import data

class Camera:
	def __init__(self, bg: callable):
		# Read relevant settings
		cfg_input = cfg.item("INPUT")
		cfg_window = cfg.item("WINDOW")
		cfg_render = cfg.item("RENDER")
		self.max_pitch = float(cfg_input["max_pitch"]) or 0
		self.width = int(cfg_window["width"]) or 120
		self.height = int(cfg_window["height"]) or 60
		self.ambient = float(cfg_render["ambient"]) or 0
		self.static = int(cfg_render["static"]) or 0
		self.fov = float(cfg_render["fov"]) or 90
		self.dof = float(cfg_render["dof"]) or 0
		self.skip = float(cfg_render["skip"]) or 0
		self.blur = float(cfg_render["blur"]) or 0
		self.dist_min = int(cfg_render["dist_min"]) or 0
		self.dist_max = int(cfg_render["dist_max"]) or 24
		self.terminate_hits = float(cfg_render["terminate_hits"]) or 0
		self.terminate_dist = float(cfg_render["terminate_dist"]) or 0
		self.threads = int(cfg_render["threads"]) or mp.cpu_count()
		self.pos = vec3(0, 0, 0)
		self.rot = vec3(0, 0, 0)
		self.proportions = ((self.width + self.height) / 2) / max(self.width, self.height)
		self.bg = bg
		self.objects = []

	def move(self, ofs: vec3):
		if ofs.x != 0 or ofs.y != 0 or ofs.z != 0:
			self.pos += ofs

	def rotate(self, rot: vec3):
		if rot.x != 0 or rot.y != 0 or rot.z != 0:
			self.rot = self.rot.rotate(rot)

			# Limit camera pitch
			if self.max_pitch:
				pitch_min = max(180, 360 - self.max_pitch)
				pitch_max = min(180, self.max_pitch)
				if self.rot.y > pitch_max and self.rot.y <= 180:
					self.rot.y = pitch_max
				if self.rot.y < pitch_min and self.rot.y > 180:
					self.rot.y = pitch_min

	def draw_trace(self, i):
		# Obtain the 2D position of this pixel in the viewport as: X = -1 is left, X = +1 is right, Y = -1 is down, Y = +1 is up
		pos = index_vec2(i, self.width)
		ofs_x = (-0.5 + pos.x / self.width) * 2
		ofs_y = (-0.5 + pos.y / self.height) * 2

		# Probabilistically skip pixel recalculation for pixels closer to the screen edge
		if max(abs(ofs_x), abs(ofs_y)) * self.skip > random.random():
			return None

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
		# Optionally the random seed is set to the index of the pixel so random noise in ray calculations cam be static instead of flickering
		if self.static:
			random.seed(i)
		while ray.step < ray.life:
			for obj in self.objects:
				obj_pos = obj.pos_rel(ray.pos)
				if obj_pos:
					obj_mat = obj.get_voxel(obj_pos)
					if obj_mat:
						obj_mat.function(ray, obj_mat)

			# Terminate this ray earlier in some circumstances to improve performance
			if ray.hits and self.terminate_hits / ray.hits < random.random():
				break
			elif ray.step / ray.life > 1 - self.terminate_dist * random.random():
				break
			ray.step += 1
			ray.pos += ray.vel
		random.seed(None)

		# Once ray calculations are done, run the background function and return the resulting color
		self.bg(ray)
		return ray.col and ray.col.mix(rgb(0, 0, 0), 1 - ray.energy) or None

	def draw(self, thread):
		# Create a new surface for this thread to paint to, returned to the main thread as a byte string
		# The alpha channel is used to skip drawing unchanged pixels and apply the blur effect by reducing how much the image blends to the canvas
		srf = pg.Surface((self.width, math.ceil(self.height / self.threads)), pg.HWSURFACE + pg.SRCALPHA)
		alpha = int(self.blur * 255)

		# Trace every pixel on this surface, the 2D position of each pixel is deduced from its index
		# i is the pixel index relative to the local surface, index is the pixel index at its real position in the window
		pixels = math.ceil(self.height / self.threads) * self.width
		for i in range(pixels):
			index = thread * pixels + i
			if index >= self.width * self.height:
				break

			col = self.draw_trace(index)
			if col:
				srf_pos = index_vec2(i, self.width)
				srf.set_at(srf_pos.tuple(), col.tuple() + (alpha,))

		return pg.image.tobytes(srf, "RGBA")

	def pool(self, pool):
		# Check which objects are active and close enough to the camera to be seen, add valid entries to the local object storage
		self.objects = []
		for obj in data.objects:
			if obj.active and obj.distance(self.pos) <= self.dist_max:
				self.objects.append(obj)

		return pool.map(self.draw, range(self.threads))
