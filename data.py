#!/usr/bin/python3
from lib import *

import copy
import random

# Global container for all objects, accessed by the window and camera
objects = []

class Material:
	def __init__(self, **settings):
		self.function = "function" in settings and settings["function"] or None
		self.group = None
		self.normals = None
		for s in settings:
			setattr(self, s, settings[s])

	# Check if this material is solid to the given group
	def in_group(self, group: str):
		return self.group and group and self.group == group

class Object:
	def __init__(self, **settings):
		# pos is the center of the object in world space, dist is size / 2 and represents distance from the origin to each bounding box surface
		# mins and maxs represent the start and end corners in world space, updated when moving the object to avoid costly checks during ray tracing
		self.pos = settings["pos"] or vec3(0, 0, 0)
		self.size = settings["size"] or vec3(0, 0, 0)
		self.active = settings["active"] or False
		self.dist = self.size / 2
		self.mins = vec3(0, 0, 0)
		self.maxs = vec3(0, 0, 0)
		self.move(self.pos)

		# Initialize the voxel list with empty material positions filling the bounding box of this object
		# Sprites can store alternate models which may be activated or mixed on demand to replace the active mesh
		# The voxel list is ordered, 3D position is converted from the index to know which position a voxel refers to
		self.sprites = {}
		self.voxels = []
		for i in range(self.size.x * self.size.y * self.size.z):
			self.voxels.append(None)

		# Add self to the list of objects, the object deletes itself from the list when removed
		objects.append(self)

	def remove(self):
		objects.remove(self)

	# Get the distance from the bounding box surface to the given position
	def distance(self, pos: vec3):
		x = max(0, abs(self.pos.x - pos.x) - self.dist.x)
		y = max(0, abs(self.pos.y - pos.y) - self.dist.y)
		z = max(0, abs(self.pos.z - pos.z) - self.dist.z)
		return max(x, y, z)

	# Check whether a point position is inside the bounding box of this object
	def intersects(self, pos: vec3):
		if pos.x < self.maxs.x + 1 and pos.x > self.mins.x:
			if pos.y < self.maxs.y + 1 and pos.y > self.mins.y:
				if pos.z < self.maxs.z + 1 and pos.z > self.mins.z:
					return True
		return False

	# Check whether another box intersects the bounding box of this object, pos_min and pos_max represent the corners of the other box
	def intersects_box(self, pos_min: vec3, pos_max: vec3):
		if pos_min.x < self.maxs.x + 1 and pos_max.x > self.mins.x:
			if pos_min.y < self.maxs.y + 1 and pos_max.y > self.mins.y:
				if pos_min.z < self.maxs.z + 1 and pos_max.z > self.mins.z:
					return True
		return False

	# Returns position relative to the minimum corner, add range 0 to self.size to get a particular voxel
	def pos_rel(self, pos: vec3):
		return self.maxs - pos

	# Moves this object to a new origin, update mins and maxs to represent the bounding box in space
	def move(self, pos):
		self.pos = pos.int()
		self.mins = self.pos - self.dist
		self.maxs = self.pos + self.dist

	# Remove a sprite from the sprite list
	def del_sprite(self, sprite: str):
		if sprite in self.sprites:
			del self.sprites[sprite]

	# Mix another sprite into the given sprite, None ignores changes so empty spaces don't override
	def mix_sprite(self, sprite: str, other: str):
		for i in range(self.size.x * self.size.y * self.size.z):
			if self.sprites[other][i]:
				self.sprites[sprite][i] = self.sprites[other][i]

	# Store the provided voxel data to a sprite, if no data is given create an empty sprite
	# Use self.voxels to store the current mesh to a sprite
	def set_sprite(self, data: list):
		if data:
			self.sprites[sprite] = data
		else:
			self.sprites[sprite] = []
			for i in range(self.size.x * self.size.y * self.size.z):
				self.sprites[sprite][i] = None

	# Set a sprite as the current voxel mesh
	def activate_sprite(self, sprite: str):
		if sprite in self.sprites:
			self.voxels = self.sprites[sprite]

	# Get the voxel at this position, returns the material or None if empty
	# Position is in local space, always convert the position with pos_rel before calling this
	def get_voxel(self, pos: vec3):
		i = vec3_index(pos.int(), self.size.x, self.size.y)
		if i < len(self.voxels):
			return self.voxels[i]
		return None

	# Check neighbors and update the normals for this voxel, used by material functions to calculate ray bounce direction
	# Normals are stored on the material instance of the voxel, the list describing free or occupied neighbors is in the order: -x, +x, -y, +y, -z, +z
	def set_voxel_normals(self, pos: vec3):
		mat = self.get_voxel(pos)
		if mat:
			mat.normals = []
			neighbors = vec3_neighbors(pos)
			for pos_n in neighbors:
				mat_n = self.get_voxel(pos_n)
				mat_n_free = not mat_n or not mat_n.in_group(mat.group)
				mat.normals.append(mat_n_free and True or False)

	# Add or remove a voxel at a single position, can be None to clear the voxel
	# Position is local to the object and starts from the minimum corner, each axis should range between 0 and self.size - 1
	# The material applied to the voxel is copied to allow modifying properties per voxel without changing the original material definition
	def set_voxel(self, pos: vec3, mat: Material):
		if pos.x < 0 or pos.x >= self.size.x or pos.y < 0 or pos.y >= self.size.y or pos.z < 0 or pos.z >= self.size.z:
			print("Warning: Attempted to set voxel outside of object boundaries at position " + pos.string() + ".")
			return

		i = vec3_index(pos.int(), self.size.x, self.size.y)
		if i < len(self.voxels):
			self.voxels[i] = mat and copy.copy(mat) or None

			# When a voxel changes, its normals as well as those of direct neighbors must be updated to reflect the newly freed / occupied space
			neighbors = vec3_neighbors(pos)
			for pos_n in neighbors:
				self.set_voxel_normals(pos_n)
			if mat:
				self.set_voxel_normals(pos)

	# Same as set_voxel but modifies voxels in a cubic area instead of a point
	def set_voxel_area(self, pos_min: vec3, pos_max: vec3, mat: Material):
		for x in range(int(pos_min.x), int(pos_max.x + 1)):
			for y in range(int(pos_min.y), int(pos_max.y + 1)):
				for z in range(int(pos_min.z), int(pos_max.z + 1)):
					self.set_voxel(vec3(x, y, z), mat)
