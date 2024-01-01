#!/usr/bin/python3
from lib import *

import random

import pygame as pg

# Global container for all objects, accessed by the window and camera
objects = []

class Material:
	def __init__(self, **settings):
		self.function = "function" in settings and settings["function"] or None
		for s in settings:
			setattr(self, s, settings[s])

class Sprite:
	def __init__(self, **settings):
		self.size = settings["size"] or vec3(0, 0, 0)

		# Animation properties and the frame list used to store multiple voxel meshes representing animation frames
		self.frame_start = self.frame_end = self.frame_time = 0
		self.frames = []
		for i in range(settings["frames"]):
			self.clear(i)

	# Set the animation range and speed at which it should be played
	# If animation time is negative the animation will play backwards
	def anim_set(self, frame_start: int, frame_end: int, frame_time: float):
		self.frame_start = min(frame_start, len(self.frames))
		self.frame_end = min(frame_end, len(self.frames))
		self.frame_time = frame_time * 1000

	# Returns the animation frame that should currently be displayed based on the time
	def anim_frame(self):
		if self.frame_time and len(self.frames) > 1:
			return int(self.frame_start + (pg.time.get_ticks() // self.frame_time) % (self.frame_end - self.frame_start))
		return 0

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

	# Add or remove a voxel at a single position, can be None to clear the voxel
	# Position is local to the object and starts from the minimum corner, each axis should range between 0 and self.size - 1
	# The material applied to the voxel is copied to allow modifying properties per voxel without changing the original material definition
	def set_voxel(self, frame: int, pos: vec3, mat: Material):
		if pos.x < 0 or pos.x >= self.size.x or pos.y < 0 or pos.y >= self.size.y or pos.z < 0 or pos.z >= self.size.z:
			print("Warning: Attempted to set voxel outside of object boundaries at position " + pos.string() + ".")
			return

		voxels = self.frames[frame]
		i = vec3_index(pos, self.size.x, self.size.y)
		if i < len(voxels):
			voxels[i] = mat

	# Same as set_voxel but modifies voxels in a cubic area instead of a point
	def set_voxel_area(self, frame: int, pos_min: vec3, pos_max: vec3, mat: Material):
		for x in range(int(pos_min.x), int(pos_max.x + 1)):
			for y in range(int(pos_min.y), int(pos_max.y + 1)):
				for z in range(int(pos_min.z), int(pos_max.z + 1)):
					self.set_voxel(frame, vec3(x, y, z), mat)

	# Get the voxel at this position, returns the material or None if empty or out of range
	# Position is in local space, always convert the position to local coordinates before calling this
	# Frame can be None to retreive the active frame instead of a specific frame, use this when drawing the sprite
	def get_voxel(self, frame: int, pos: vec3):
		voxels = frame is not None and self.frames[frame] or self.frames[self.anim_frame()]
		i = vec3_index(pos, self.size.x, self.size.y)
		if i < len(voxels):
			return voxels[i]
		return None

class Object:
	def __init__(self, **settings):
		# pos is the center of the object in world space, dist is size / 2 and represents distance from the origin to each bounding box surface
		# mins and maxs represent the start and end corners in world space, updated when moving the object to avoid costly checks during ray tracing
		# When a sprite is set the object is resized to its position and voxels will be fetched from it, setting the sprite to None disables this object
		# The object holds 4 sprites for every direction angle (0* 90* 180* 270*), the set_sprite function can also take a single sprite to disable rotation
		self.pos = settings["pos"] or vec3(0, 0, 0)
		self.size = self.dist = self.mins = self.maxs = vec3(0, 0, 0)
		self.angle = 0
		self.sprites = [None] * 4
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
	def rotate(self, angle: float):
		self.angle = (self.angle + angle) % 360

	# Set a sprite as the active sprite, None removes the sprite from this object and disables it
	# If more than one sprite is provided, store up 4 sprites representing object angles
	# Set the size and bounding box of the object to that of its sprite, or a point if the sprite is disabled
	def set_sprite(self, *sprites):
		self.size = self.dist = self.mins = self.maxs = vec3(0, 0, 0)
		for i in range(len(sprites)):
			self.sprites[i] = sprites[i]
		if self.sprites[0]:
			self.size = self.sprites[0].size
			self.dist = self.size / 2
			self.mins = self.pos - self.dist
			self.maxs = self.pos + self.dist

	# Get the appropriate sprite for this object based on which 0* / 90* / 180* / 270* direction it's facing toward
	def get_sprite(self):
		angle = round(self.angle / 90) % 4
		if self.sprites[angle]:
			return self.sprites[angle]
		return self.sprites[0]
