#!/usr/bin/python3
from lib import *

import random

# Default material function, mods may provide their own to replace this
def material_default(pos, vel, col, step, hits, data):
	# Translucency: Random chance that each ray will ignore this voxel
	if data["translucency"] > random.random():
		return pos, vel, col

	# Color: Mix the albedo of this voxel into the pixel color, mixing reduces with the number of hits
	col = col and col.mix(data["albedo"], 1 / hits) or data["albedo"]

	# Velocity: Either bounce the ray or let it pass based on translucency probability
	vel = vel.mix(vec3(-vel.x, -vel.y, -vel.z), data["angle"] / 360)
	vel += vec3(rand(data["roughness"]), rand(data["roughness"]), rand(data["roughness"]))
	vel.normalize()

	return pos, vel, col

class Material:
	def __init__(self, func: callable, data: dict):
		# Materials hold a function executed when a ray hits them, as well as data storing the properties used by this function
		self.function = func or material_default
		self.data = data or {
			"albedo": rgb(255, 255, 255),
			"roughness": 0.5,
			"translucency": 0,
			"angle": 0.5,
		}

class Voxels:
	def __init__(self):
		self.materials = {}
		self.voxels = {}

	# Register a new material in the material database
	def register_material(self, name: str, func: callable, data: dict):
		self.materials[name] = Material(func, data)

	#Unregister a from the material database
	def unregister_material(self, name: str):
		if name in self.materials:
			del self.materials[name]

	#Get the properties of a material
	def get_material(self, name: str):
		if name in self.materials:
			return self.materials[name]

	#Get the voxel at this position
	def get_voxel(self, pos: vec3):
		p = pos.get_str()
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
		p = pos.get_str()
		if pos in self.voxels:
			del self.voxels[pos]

	# Add a voxel at a single position
	def set_voxel(self, pos: vec3, mat: str):
		p = pos.get_str()
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
