#!/usr/bin/python3
from lib import *

import random

# Default material function, mods can provide materials that use their own functions if desired
def material_default(ray, mat):
	# Color: Use material color darkened by alpha value, mixing reduces with the number of hits
	col = mat.albedo.mix(rgb(0, 0, 0), 1 - ray.alpha)
	ray.col = ray.col and ray.col.mix(col, 1 / ray.hits) or col

	# Velocity: Estimate the normal direction of the voxel based on its neighbors, bounce the ray back for solid bounces but not translucent ones
	# Reflections may occur in one or all three axis, diagonal face normals are not supported but corner voxels may act as a 45* mirror
	if mat.translucency < random.random():
		if ray.vel.x > 0 and (not ray.neighbors[0] or ray.neighbors[0].translucency > random.random()):
			ray.vel.x *= -1
		elif ray.vel.x < 0 and (not ray.neighbors[1] or ray.neighbors[1].translucency > random.random()):
			ray.vel.x *= -1
		if ray.vel.y > 0 and (not ray.neighbors[2] or ray.neighbors[2].translucency > random.random()):
			ray.vel.y *= -1
		elif ray.vel.y < 0 and (not ray.neighbors[3] or ray.neighbors[3].translucency > random.random()):
			ray.vel.y *= -1
		if ray.vel.z > 0 and (not ray.neighbors[4] or ray.neighbors[4].translucency > random.random()):
			ray.vel.z *= -1
		elif ray.vel.z < 0 and (not ray.neighbors[5] or ray.neighbors[5].translucency > random.random()):
			ray.vel.z *= -1
	ray.vel += vec3(rand(mat.roughness), rand(mat.roughness), rand(mat.roughness))
	ray.vel.normalize()

class Material:
	def __init__(self, func: callable, **settings):
		self.function = func or material_default
		for s in settings:
			setattr(self, s, settings[s])

class Voxels:
	def __init__(self):
		self.voxels = {}

	# Get the voxel at this position
	def get_voxel(self, pos: vec3):
		p = pos.string()
		return p in self.voxels and self.voxels[p] or None

	# Move a voxel in the specified direction, will either swap or erase a voxel present at the new position
	def swap_voxels(self, pos: vec3, vec: vec3, swap: bool):
		pos_dst = pos + vec
		mat = self.get_voxel(pos)
		mat_dst = self.get_voxel(pos_dst)
		if swap:
			self.set_voxel(pos, mat_dst)
		else:
			self.clear_voxel(pos)
		self.set_voxel(pos_dst, mat)

	# Remove all voxels from the data set
	def clear_voxels(self):
		self.voxels = {}

	# Remove a voxel from a single position
	def clear_voxel(self, pos: vec3):
		p = pos.string()
		if pos in self.voxels:
			del self.voxels[pos]

	# Add a voxel at a single position
	def set_voxel(self, pos: vec3, mat: Material):
		p = pos.string()
		self.voxels[p] = mat

	# Remove voxels from a cubic area
	def clear_voxel_area(self, pos_min: vec3, pos_max: vec3):
		for x in range(int(pos_min.x), int(pos_max.x + 1)):
			for y in range(int(pos_min.y), int(pos_max.y + 1)):
				for z in range(int(pos_min.z), int(pos_max.z + 1)):
					pos = vec3(x, y, z)
					self.clear_voxel(pos)

	# Add voxels in a cubic area
	def set_voxel_area(self, pos_min: vec3, pos_max: vec3, mat: Material):
		for x in range(int(pos_min.x), int(pos_max.x + 1)):
			for y in range(int(pos_min.y), int(pos_max.y + 1)):
				for z in range(int(pos_min.z), int(pos_max.z + 1)):
					pos = vec3(x, y, z)
					self.set_voxel(pos, mat)
