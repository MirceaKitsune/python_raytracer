#!/usr/bin/python3
from lib import *

import random

# Default material function, mods can provide materials that use their own functions if desired
def material_default(ray, mat):
	# Translucency: Random chance that each ray will ignore this voxel
	if mat.translucency > random.random():
		return

	# Color: Mix the albedo of this voxel into the pixel color, mixing reduces with the number of hits
	ray.col = ray.col and ray.col.mix(mat.albedo, 1 / ray.hits) or mat.albedo

	# Velocity: Bounce the ray based on material angle
	ray.vel = ray.vel.mix(vec3(-ray.vel.x, -ray.vel.y, -ray.vel.z), mat.angle / 360)
	ray.vel += vec3(rand(mat.roughness), rand(mat.roughness), rand(mat.roughness))
	ray.vel.normalize()

class Material:
	def __init__(self, func: callable, **settings):
		self.function = func or material_default
		for s in settings:
			setattr(self, s, settings[s])

class Voxels:
	def __init__(self):
		self.materials = {}
		self.voxels = {}

	# Add a new material to the material database
	def register_material(self, name: str, mat: Material):
		self.materials[name] = mat

	# Remove a material from the material database
	def unregister_material(self, name: str):
		if name in self.materials:
			del self.materials[name]

	# Get a material by its name
	def get_material(self, name: str):
		if name in self.materials:
			return self.materials[name]

	# Get the voxel at this position
	def get_voxel(self, pos: vec3):
		p = pos.string()
		if p in self.voxels:
			return self.voxels[p]
		return None

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
	def set_voxel(self, pos: vec3, mat: str):
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
	def set_voxel_area(self, pos_min: vec3, pos_max, mat: vec3):
		for x in range(int(pos_min.x), int(pos_max.x + 1)):
			for y in range(int(pos_min.y), int(pos_max.y + 1)):
				for z in range(int(pos_min.z), int(pos_max.z + 1)):
					pos = vec3(x, y, z)
					self.set_voxel(pos, mat)
