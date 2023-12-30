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
		self.normals = [False] * 6
		for s in settings:
			setattr(self, s, settings[s])

	# Check if this material is solid to the given group
	def in_group(self, group: str):
		return self.group and group and self.group == group

class Sprite:
	def __init__(self, **settings):
		self.size = settings["size"] or vec3(0, 0, 0)

		# The frame list is used to store multiple voxel meshes representing animation frames
		self.frames = []
		for i in range(settings["frames"]):
			self.clear(i)

	# Clear all voxels on the given frame, also used to initialize empty frames up to the given frame count
	def clear(self, frame: int):
		while len(self.frames) <= frame:
			self.frames.append([None] * self.size.x * self.size.y * self.size.z)
		self.frames[frame] = [None] * self.size.x * self.size.y * self.size.z

	# Rotate all frames in the sprite around the Y axis at a 90 degree step: 1 = 90*, 2 = 180*, 3 = 270*
	# This operation is only supported if the X and Z axes of the sprite are equal, voxel meshes with uneven horizontal proportions can't be rotated
	def rotate(self, angle: int):
		if self.size.x != self.size.z:
			print("Warning: Can't rotate uneven sprite of size " + self.size.string() + ", X and Z scale must be equal.")
			return

		for f in range(len(self.frames)):
			voxels = self.frames[f]
			self.clear(f)
			for i in range(len(voxels)):
				pos = index_vec3(i, self.size.x, self.size.y)
				if angle == 1:
					pos = vec3(pos.z, pos.y, (self.size.x - 1) - pos.x)
				elif angle == 2:
					pos = vec3((self.size.x - 1) - pos.x, pos.y, (self.size.z - 1) - pos.z)
				elif angle == 3:
					pos = vec3((self.size.z - 1) - pos.z, pos.y, pos.x)
				self.set_voxel(f, pos, voxels[i])
			self.set_normals(f)

	# Mirror the sprite along the given axes
	def flip(self, x: bool, y: bool, z: bool):
		for f in range(len(self.frames)):
			voxels = self.frames[f]
			self.clear(f)
			for i in range(len(voxels)):
				pos = index_vec3(i, self.size.x, self.size.y)
				if x:
					pos = vec3((self.size.x - 1) - pos.x, pos.y, pos.z)
				if y:
					pos = vec3(pos.x, (self.size.y - 1) - pos.y, pos.z)
				if z:
					pos = vec3(pos.x, pos.y, (self.size.z - 1) - pos.z)
				self.set_voxel(f, pos, voxels[i])
			self.set_normals(f)

	# Mix another sprite of the same size into the given sprite, None ignores changes so empty spaces don't override
	# If the frame count of either sprite is shorter, only the amount of sprites that correspond will be mixed
	# This operation is only supported if the X Y Z axes of the sprite are all equal, meshes of unequal size can't be mixed
	def mix(self, other):
		if self.size.x != other.size.x or self.size.y != other.size.y or self.size.z != other.size.z:
			print("Warning: Can't mix sprites of uneven size, " + self.size.string() + " and " + other.size.string() + " are not equal.")
			return

		for f in range(min(len(self.frames), len(other.frames))):
			voxels = other.frames[f]
			for i in range(len(voxels)):
				if voxels[i]:
					pos = index_vec3(i, self.size.x, self.size.y)
					self.set_voxel(f, pos, voxels[i])
			self.set_normals(f)

	# Update the voxel normals, this should always be ran after making changes to voxels otherwise ray reflections will not be accurate
	# Normals are stored on the material instance of the voxel, the list describing free or occupied neighbors is in order of: -X, +X, -Y, +Y, -Z, +Z
	def set_normals(self, frame: int):
		voxels = self.frames[frame]
		for i in range(len(voxels)):
			pos = index_vec3(i, self.size.x, self.size.y)
			mat = self.get_voxel(frame, pos)
			if mat:
				mat.normals = []
				neighbors = vec3_neighbors(pos)
				for pos_n in neighbors:
					mat_n = self.get_voxel(frame, pos_n)
					mat_n_free = not mat_n or not mat_n.in_group(mat.group)
					mat.normals.append(mat_n_free and True or False)

	# Add or remove a voxel at a single position, can be None to clear the voxel
	# Position is local to the object and starts from the minimum corner, each axis should range between 0 and self.size - 1
	# The material applied to the voxel is copied to allow modifying properties per voxel without changing the original material definition
	def set_voxel(self, frame: int, pos: vec3, mat: Material):
		if pos.x < 0 or pos.x >= self.size.x or pos.y < 0 or pos.y >= self.size.y or pos.z < 0 or pos.z >= self.size.z:
			print("Warning: Attempted to set voxel outside of object boundaries at position " + pos.string() + ".")
			return

		voxels = self.frames[frame]
		i = vec3_index(pos.int(), self.size.x, self.size.y)
		if i < len(voxels):
			voxels[i] = mat and copy.copy(mat) or None

	# Same as set_voxel but modifies voxels in a cubic area instead of a point
	def set_voxel_area(self, frame: int, pos_min: vec3, pos_max: vec3, mat: Material):
		for x in range(int(pos_min.x), int(pos_max.x + 1)):
			for y in range(int(pos_min.y), int(pos_max.y + 1)):
				for z in range(int(pos_min.z), int(pos_max.z + 1)):
					self.set_voxel(frame, vec3(x, y, z), mat)

	# Get the voxel at this position, returns the material or None if empty or out of range
	# Position is in local space, always convert the position to local coordinates before calling this
	def get_voxel(self, frame: int, pos: vec3):
		voxels = self.frames[frame]
		i = vec3_index(pos.int(), self.size.x, self.size.y)
		if i < len(voxels):
			return voxels[i]
		return None

class Object:
	def __init__(self, **settings):
		# pos is the center of the object in world space, dist is size / 2 and represents distance from the origin to each bounding box surface
		# mins and maxs represent the start and end corners in world space, updated when moving the object to avoid costly checks during ray tracing
		# When a sprite is set the object is resized to its position and voxels will be fetched from it
		self.pos = settings["pos"] or vec3(0, 0, 0)
		self.size = self.dist = self.mins = self.maxs = vec3(0, 0, 0)
		self.angle = 0
		self.sprite = None
		self.active = True
		self.move(self.pos)
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

	# Return position relative to the minimum corner, None if the position is outside of object boundaries
	def pos_rel(self, pos: vec3):
		pos_rel = self.maxs - pos
		if pos_rel.x >= 0 and pos_rel.x < self.size.x:
			if pos_rel.y >= 0 and pos_rel.y < self.size.y:
				if pos_rel.z >= 0 and pos_rel.z < self.size.z:
					return pos_rel
		return None

	# Move this object to a new origin, update mins and maxs to represent the bounding box in space
	def move(self, pos):
		self.pos = pos.int()
		self.mins = self.pos - self.dist
		self.maxs = self.pos + self.dist

	# Rotate the angle of object around the Y axis by the provided rotation
	# Only change sprite rotation if the object faces toward a different 0* / 90* / 180* / 270* direction after the change
	def rotate(self, angle: float):
		ang_old = round(self.angle / 90)
		ang_new = round((self.angle + angle) / 90)
		ang = (ang_new - ang_old) % 4
		self.angle = (self.angle + angle) % 360
		if ang:
			self.sprite.rotate(ang)

	# Return the voxel at this position on the active sprite
	def get_voxel(self, pos: vec3):
		if self.sprite:
			return self.sprite.get_voxel(0, pos)
		return None

	# Set a sprite as the active sprite, None removes the sprite from this object
	# Angle is reset to 0 as every sprite must be rotated together with the object
	# Set the size and bounding box of the object to that of its sprite, or a point if the sprite is disabled
	def set_sprite(self, spr: Sprite):
		self.sprite = spr
		self.angle = 0
		if self.sprite:
			self.size = self.sprite.size
			self.dist = self.size / 2
			self.mins = self.pos - self.dist
			self.maxs = self.pos + self.dist
		else:
			self.size = self.dist = self.mins = self.maxs = vec3(0, 0, 0)
