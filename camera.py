#!/usr/bin/python3
from lib import *

import multiprocessing as mp
import pygame as pg
import math
import random

import data

class Camera:
	def __init__(self, bg: callable):
		self.width = cfg.getint("WINDOW", "width") or 96
		self.height = cfg.getint("WINDOW", "height") or 64
		self.ambient = cfg.getfloat("RENDER", "ambient") or 0
		self.static = cfg.getboolean("RENDER", "static") or False
		self.fov = cfg.getfloat("RENDER", "fov") or 90
		self.dof = cfg.getfloat("RENDER", "dof") or 0
		self.skip = cfg.getfloat("RENDER", "skip") or 0
		self.blur = cfg.getfloat("RENDER", "blur") or 0
		self.dist_min = cfg.getint("RENDER", "dist_min") or 0
		self.dist_max = cfg.getint("RENDER", "dist_max") or 48
		self.terminate_hits = cfg.getfloat("RENDER", "terminate_hits") or 0
		self.terminate_dist = cfg.getfloat("RENDER", "terminate_dist") or 0
		self.threads = cfg.getint("RENDER", "threads") or mp.cpu_count()
		self.pos = vec3(0, 0, 0)
		self.rot = vec3(0, 0, 0)
		self.proportions = ((self.width + self.height) / 2) / max(self.width, self.height)
		self.bg = bg
		self.objects = []

	# Obtain the 2D position of this pixel in the viewport as: X = -1 is left, X = +1 is right, Y = -1 is down, Y = +1 is up
	def trace(self, i):
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
				if obj.intersects(ray.pos, ray.pos):
					obj_spr = obj.get_sprite()
					obj_pos = obj.pos_rel(ray.pos.int())
					obj_mat = obj_spr.get_voxel(None, obj_pos)
					if obj_mat:
						# Reflect the velocity of the ray based on material IOR and the neighbors of this voxel which are used to determine face normals
						# A material considers its neighbors solid if they have the same IOR, otherwise they won't affect the direction of ray reflections
						# If IOR is above 0.5 check the neighbor opposite the ray direction in that axis, otherwise check the neighbor in the ray's direction
						if obj_mat.ior:
							direction = (obj_mat.ior - 0.5) * 2
							dir_x = ray.vel.x * direction < 0 and +1 or -1
							dir_y = ray.vel.y * direction < 0 and +1 or -1
							dir_z = ray.vel.z * direction < 0 and +1 or -1
							mat_x = obj_spr.get_voxel(None, obj_pos + vec3(dir_x, 0, 0))
							mat_y = obj_spr.get_voxel(None, obj_pos + vec3(0, dir_y, 0))
							mat_z = obj_spr.get_voxel(None, obj_pos + vec3(0, 0, dir_z))
							if not (mat_x and mat_x.ior == obj_mat.ior):
								ray.vel.x = mix(+ray.vel.x, -ray.vel.x, obj_mat.ior)
							if not (mat_y and mat_y.ior == obj_mat.ior):
								ray.vel.y = mix(+ray.vel.y, -ray.vel.y, obj_mat.ior)
							if not (mat_z and mat_z.ior == obj_mat.ior):
								ray.vel.z = mix(+ray.vel.z, -ray.vel.z, obj_mat.ior)

						# Call the material function, normalize ray velocity after making changes to ensure the speed of light remains 1 and future voxels aren't skipped or calculated twice
						obj_mat.function(ray, obj_mat)
						ray.vel = ray.vel.normalize()
						break

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

	# Create a new surface for this thread to paint to, returned to the main thread as a byte string
	# The alpha channel is used to skip drawing unchanged pixels and apply the blur effect by reducing how much the image blends to the canvas
	def draw(self, thread):
		srf = pg.Surface((self.width, math.ceil(self.height / self.threads)), pg.HWSURFACE + pg.SRCALPHA)
		alpha = int(self.blur * 255)

		# Trace every pixel on this surface, the 2D position of each pixel is deduced from its index
		# i is the pixel index relative to the local surface, index is the pixel index at its real position in the window
		pixels = math.ceil(self.height / self.threads) * self.width
		for i in range(pixels):
			index = thread * pixels + i
			if index >= self.width * self.height:
				break

			col = self.trace(index)
			if col:
				srf_pos = index_vec2(i, self.width)
				srf.set_at(srf_pos.tuple(), col.tuple() + (alpha,))

		return pg.image.tobytes(srf, "RGBA")

	# Render a new frame at this position, only calculate objects that have a sprite and are close enough to the camera to be seen
	def render(self, pos: vec3, rot: vec3, pool):
		self.pos = pos
		self.rot = rot
		self.objects = []
		for obj in data.objects:
			if obj.sprites and obj.distance(self.pos) <= self.dist_max:
				self.objects.append(obj)

		return pool.map(self.draw, range(self.threads))
