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

class Sprite:
	def __init__(self, **settings):
		self.size = settings["size"] or vec3(0, 0, 0)
		self.voxels = [None] * self.size.x * self.size.y * self.size.z
		self.angle = 0

	# Rotates the sprite's voxels around the Y axis in 90 degree increments
	def rotate(self, angle: float):
		# Determine if this change induces a rotation compared to the existing angle and by what magnitude
		# Only preform voxel mesh rotation if the object now faces toward a different 0* / 90* / 180* / 270* direction
		ang_old = round(self.angle / 90)
		ang_new = round((self.angle + angle) / 90)
		ang = (ang_new - ang_old) % 4
		self.angle = (self.angle + angle) % 360
		if not ang:
			return

		# Remember old voxel data used to regenerate the voxel array
		# If this is a 90* or 270* rotation, the x and z size are also swapped
		old_voxels = self.voxels
		old_size = self.size
		if ang == 1 or ang == 3:
			self.size = vec3(self.size.z, self.size.y, self.size.x)

		# Generate new voxel list rotated at the given angle: 1 = 90*, 2 = 180*, 3 = 270*
		self.voxels = [None] * self.size.x * self.size.y * self.size.z
		for i in range(len(old_voxels)):
			pos = index_vec3(i, old_size.x, old_size.y)
			if ang == 1:
				pos = vec3(pos.z, pos.y, (old_size.x - 1) - pos.x)
			elif ang == 2:
				pos = vec3((old_size.x - 1) - pos.x, pos.y, (old_size.z - 1) - pos.z)
			elif ang == 3:
				pos = vec3((old_size.z - 1) - pos.z, pos.y, pos.x)
			self.set_voxel(pos, old_voxels[i])

	# Get the voxel at this position, returns the material or None if empty
	# Position is in local space, always convert the position with pos_rel before calling this
	def get_voxel(self, pos: vec3):
		i = vec3_index(pos.int(), self.size.x, self.size.y)
		if i < len(self.voxels):
			return self.voxels[i]
		return None

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

	# Mix another sprite of the same size into the given sprite, None ignores changes so empty spaces don't override
	def mix(self, other):
		if self.size.x == other[i].size.x and self.size.y == other[i].size.y and self.size.z == other[i].size.z:
			for i in range(self.size.x * self.size.y * self.size.z):
				if other.voxels[i]:
					pos = index_vec3(i, self.size.x, self.size.y)
					self.set_voxel(pos, other.voxels[i])

class Object:
	def __init__(self, **settings):
		# pos is the center of the object in world space, dist is size / 2 and represents distance from the origin to each bounding box surface
		# mins and maxs represent the start and end corners in world space, updated when moving the object to avoid costly checks during ray tracing
		self.pos = settings["pos"] or vec3(0, 0, 0)
		self.size = self.dist = self.mins = self.maxs = vec3(0, 0, 0)
		self.active = True
		self.move(self.pos)

		# Sprites are used to store multiple voxel models on the object which can be activated on demand
		# When a sprite is set as the active sprite, the object is resized to its position and voxels will be fetched from it
		self.sprites = {}
		self.sprite = None

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

	# Check whether another item intersects the bounding box of this object, pos_min and pos_max represent the corners of another box or a point if identical
	def intersects(self, pos_min: vec3, pos_max: vec3):
		if pos_min.x < self.maxs.x + 1 and pos_max.x > self.mins.x:
			if pos_min.y < self.maxs.y + 1 and pos_max.y > self.mins.y:
				if pos_min.z < self.maxs.z + 1 and pos_max.z > self.mins.z:
					return True
		return False

	# Returns position relative to the minimum corner, None if the position is outside of object boundaries
	def pos_rel(self, pos: vec3):
		pos_rel = self.maxs - pos
		if pos_rel.x >= 0 and pos_rel.x < self.size.x:
			if pos_rel.y >= 0 and pos_rel.y < self.size.y:
				if pos_rel.z >= 0 and pos_rel.z < self.size.z:
					return pos_rel
		return None

	# Moves this object to a new origin, update mins and maxs to represent the bounding box in space
	def move(self, pos):
		self.pos = pos.int()
		self.mins = self.pos - self.dist
		self.maxs = self.pos + self.dist

	# Returns the voxel at this position on the active sprite
	def get_voxel(self, pos: vec3):
		if self.sprite and self.sprite in self.sprites:
			sprite = self.sprites[self.sprite]
			return sprite.get_voxel(pos)
		return None

	# Store the provided sprite in the object under the given name
	# If no data is given this sprite is deleted, disable the object sprite if this was the active sprite
	def set_sprite(self, name: str, spr: Sprite):
		if spr:
			self.sprites[name] = spr
		elif name in self.sprites:
			del self.sprites[name]
			if self.sprite == name:
				self.activate_sprite(None)

	# Set a sprite as the active voxel mesh, None disables the sprite of this object
	def activate_sprite(self, name: str):
		self.sprite = name

		# Set the size and bounding box of the object to that of its active sprite, a point if the sprite was disabled
		if self.sprite and self.sprite in self.sprites:
			sprite = self.sprites[self.sprite]
			self.size = sprite.size
			self.dist = self.size / 2
			self.mins = self.pos - self.dist
			self.maxs = self.pos + self.dist
		else:
			self.size = self.dist = self.mins = self.maxs = vec3(0, 0, 0)
