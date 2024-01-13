#!/usr/bin/python3
from lib import *

import copy

import pygame as pg

# Variables for global instances such as objects, accessed by the window and camera
objects = []
background = None

# Material: A subset of Frame, used to store the physical properties of a virtual atom
class Material:
	def __init__(self, **settings):
		self.function = "function" in settings and settings["function"] or None
		for s in settings:
			setattr(self, s, settings[s])

	# Create a copy of this material that can be edited independently
	def clone(self):
		return copy.deepcopy(self)

# Frame: A subset of Sprite, stores instances of Material in 3D space for a single model using dictionary stacks of the form [x][y][z] = item
class Frame:
	def __init__(self):
		self.data = {}

	def clear(self):
		self.data = {}

	def get_voxels(self):
		items = []
		for x in self.data:
			for y in self.data[x]:
				for z in self.data[x][y]:
					items.append((vec3(x, y, z), self.data[x][y][z]))
		return items

	def get_voxel(self, pos: vec3):
		pos_x = int(pos.x)
		if pos_x in self.data:
			pos_y = int(pos.y)
			if pos_y in self.data[pos_x]:
				pos_z = int(pos.z)
				if pos_z in self.data[pos_x][pos_y]:
					return self.data[pos_x][pos_y][pos_z]
		return None

	# Axis storage is added or removed based on which entries are needed, each stack is deleted if the last entry on that axis has been removed
	def set_voxel(self, pos: vec3, mat: Material):
		pos_x = int(pos.x)
		pos_y = int(pos.y)
		pos_z = int(pos.z)
		if mat:
			if not pos_x in self.data:
				self.data[pos_x] = {}
			if not pos_y in self.data[pos_x]:
				self.data[pos_x][pos_y] = {}
			self.data[pos_x][pos_y][pos_z] = mat
		else:
			if pos_x in self.data:
				if not self.data[pos_x]:
					del self.data[pos_x]
				elif pos_y in self.data[pos_x]:
					if not self.data[pos_x][pos_y]:
						del self.data[pos_x][pos_y]
					elif pos_z in self.data[pos_x][pos_y]:
						del self.data[pos_x][pos_y][pos_z]

# Sprite: A subset of Object, stores multiple instances of Frame which can be animated or transformed to produce an usable 3D image
class Sprite:
	def __init__(self, **settings):
		self.size = "size" in settings and settings["size"] or vec3(0, 0, 0)

		# Animation properties and the frame list used to store multiple voxel meshes representing animation frames
		self.frame_start = self.frame_end = self.frame_time = 0
		self.frames = []
		for i in range(settings["frames"]):
			self.frames.append(Frame())

	# Create a copy of this sprite that can be edited independently
	def clone(self):
		return copy.deepcopy(self)

	# Clear all voxels on the given frame
	def clear(self, frame: int):
		voxels = self.frames[frame]
		voxels.clear()

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

	# Get the sprites for all rotations of this sprite based on its original rotation
	# Storing the result at startup is recommended to avoid costly data duplication at runtime, but the result can be parsed as object.set_sprite(*sprite.get_rotations())
	def get_rotations(self):
		spr_90 = self.clone()
		spr_180 = self.clone()
		spr_270 = self.clone()
		spr_90.rotate(1)
		spr_180.rotate(2)
		spr_270.rotate(3)
		return self, spr_90, spr_180, spr_270

	# Rotate all frames in the sprite around the Y axis at a 90 degree step: 1 = 90*, 2 = 180*, 3 = 270*
	# This operation is only supported if the X and Z axes of the sprite are equal, voxel meshes with uneven horizontal proportions can't be rotated
	def rotate(self, angle: int):
		if self.size.x != self.size.z:
			print("Warning: Can't rotate uneven sprite of size " + self.size.string() + ", X and Z scale must be equal.")
			return

		for f in range(len(self.frames)):
			voxels = self.frames[f]
			self.clear(f)
			for pos, item in voxels.get_voxels():
				if angle == 1:
					pos = vec3(pos.z, pos.y, (self.size.x - 1) - pos.x)
				elif angle == 2:
					pos = vec3((self.size.x - 1) - pos.x, pos.y, (self.size.z - 1) - pos.z)
				elif angle == 3:
					pos = vec3((self.size.z - 1) - pos.z, pos.y, pos.x)
				self.set_voxel(f, pos, item)

	# Mirror the sprite along the given axes
	def flip(self, x: bool, y: bool, z: bool):
		for f in range(len(self.frames)):
			voxels = self.frames[f]
			self.clear(f)
			for pos, item in voxels.get_voxels():
				if x:
					pos = vec3((self.size.x - 1) - pos.x, pos.y, pos.z)
				if y:
					pos = vec3(pos.x, (self.size.y - 1) - pos.y, pos.z)
				if z:
					pos = vec3(pos.x, pos.y, (self.size.z - 1) - pos.z)
				self.set_voxel(f, pos, item)

	# Mix another sprite of the same size into the given sprite, None ignores changes so empty spaces don't override
	# If the frame count of either sprite is shorter, only the amount of sprites that correspond will be mixed
	# This operation is only supported if the X Y Z axes of the sprite are all equal, meshes of unequal size can't be mixed
	def mix(self, other):
		if self.size.x != other.size.x or self.size.y != other.size.y or self.size.z != other.size.z:
			print("Warning: Can't mix sprites of uneven size, " + self.size.string() + " and " + other.size.string() + " are not equal.")
			return

		for f in range(min(len(self.frames), len(other.frames))):
			voxels = other.frames[f]
			for pos, item in voxels.get_voxels():
				if item:
					self.set_voxel(f, pos, item)

	# Add or remove a voxel at a single position, can be None to clear the voxel
	# Position is local to the object and starts from the minimum corner, each axis should range between 0 and self.size - 1
	# The material applied to the voxel is copied to allow modifying properties per voxel without changing the original material definition
	def set_voxel(self, frame: int, pos: vec3, mat: Material):
		if pos.x < 0 or pos.x >= self.size.x or pos.y < 0 or pos.y >= self.size.y or pos.z < 0 or pos.z >= self.size.z:
			print("Warning: Attempted to set voxel outside of object boundaries at position " + pos.string() + ".")
			return

		voxels = self.frames[frame]
		voxels.set_voxel(pos, mat)

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
		return voxels.get_voxel(pos)

	# Return a list of all voxels on the appropriate frame
	def get_voxels(self, frame: int):
		voxels = frame is not None and self.frames[frame] or self.frames[self.anim_frame()]
		return voxels.get_voxels()

# Object: The base class for objects in the world, uses up to 4 instances of Sprite representing different rotation angles
class Object:
	def __init__(self, **settings):
		# pos is the center of the object in world space, dist is size / 2 and represents distance from the origin to each bounding box surface
		# mins and maxs represent the start and end corners in world space, updated when moving the object to avoid costly checks during ray tracing
		# When a sprite is set the object is resized to its position and voxels will be fetched from it, setting the sprite to None disables this object
		# The object holds 4 sprites for every direction angle (0* 90* 180* 270*), the set_sprite function can also take a single sprite to disable rotation
		self.pos = "pos" in settings and settings["pos"] or vec3(0, 0, 0)
		self.rot = "rot" in settings and settings["rot"] or vec3(0, 0, 0)
		self.cam_pos = None
		self.size = self.dist = self.mins = self.maxs = vec3(0, 0, 0)
		self.sprites = [None] * 4
		self.move(self.pos)
		objects.append(self)

	# Disable this object and remove it from the global object list
	def remove(self):
		objects.remove(self)

	# Create a copy of this object that can be edited independently
	def clone(self):
		return copy.deepcopy(self)

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
		return self.maxs - pos

	# Move this object to a new origin, update mins and maxs to represent the bounding box in space
	def move(self, pos):
		if pos.x != 0 or pos.y != 0 or pos.z != 0:
			self.pos += pos
			self.mins = self.pos.int() - self.dist
			self.maxs = self.pos.int() + self.dist

	# Change the virtual rotation of the object by the given amount, pitch is limited to the provided value
	def rotate(self, rot: vec3, limit_pitch: float):
		if rot.x != 0 or rot.y != 0 or rot.z != 0:
			self.rot = self.rot.rotate(rot)
			if limit_pitch:
				pitch_min = max(180, 360 - limit_pitch)
				pitch_max = min(180, limit_pitch)
				if self.rot.y > pitch_max and self.rot.y <= 180:
					self.rot.y = pitch_max
				if self.rot.y < pitch_min and self.rot.y > 180:
					self.rot.y = pitch_min

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
			self.mins = self.pos.int() - self.dist
			self.maxs = self.pos.int() + self.dist

	# Get the appropriate sprite for this object based on which 0* / 90* / 180* / 270* direction it's facing toward
	def get_sprite(self):
		angle = round(self.rot.y / 90) % 4
		if self.sprites[angle]:
			return self.sprites[angle]
		return self.sprites[0]

	# Mark that we want to attach the camera to this object at the provided position offset
	# The camera can only be attached to one object at a time, this will remove the setting from all other objects
	def set_camera(self, pos: vec2):
		for obj in objects:
			obj.cam_pos = obj == self and pos or None
