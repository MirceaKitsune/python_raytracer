#!/usr/bin/python3
from lib import *

import copy
import math

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
		pos_x = math.trunc(pos.x)
		if pos_x in self.data:
			pos_y = math.trunc(pos.y)
			if pos_y in self.data[pos_x]:
				pos_z = math.trunc(pos.z)
				if pos_z in self.data[pos_x][pos_y]:
					return self.data[pos_x][pos_y][pos_z]
		return None

	# Axis storage is added or removed based on which entries are needed, each stack is deleted if the last entry on that axis has been removed
	def set_voxel(self, pos: vec3, mat: Material):
		pos_x = math.trunc(pos.x)
		pos_y = math.trunc(pos.y)
		pos_z = math.trunc(pos.z)
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
		# Sprite size needs to be an even number as to not break object calculations, voxels are located at integer positions and checking voxel position from object center would result in 0.5
		self.size = "size" in settings and settings["size"] or vec3(0, 0, 0)
		if self.size.x % 2 != 0 or self.size.y % 2 != 0 or self.size.z % 2 != 0:
			print("Warning: Sprite size " + str(self.size) + " contains a float or odd number in one or more directions, affected axes will be rounded and enlarged by one unit.")
			self.size.x = math.trunc(self.size.x) % 2 != 0 and math.trunc(self.size.x) + 1 or math.trunc(self.size.x)
			self.size.y = math.trunc(self.size.y) % 2 != 0 and math.trunc(self.size.y) + 1 or math.trunc(self.size.y)
			self.size.z = math.trunc(self.size.z) % 2 != 0 and math.trunc(self.size.z) + 1 or math.trunc(self.size.z)

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
			return math.trunc(self.frame_start + (pg.time.get_ticks() // self.frame_time) % (self.frame_end - self.frame_start))
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
			print("Warning: Can't rotate uneven sprite of size " + str(self.size) + ", X and Z scale must be equal.")
			return

		for f in range(len(self.frames)):
			voxels = self.frames[f]
			self.clear(f)
			for pos, mat in voxels.get_voxels():
				if angle == 1:
					pos = vec3(pos.z, pos.y, (self.size.x - 1) - pos.x)
				elif angle == 2:
					pos = vec3((self.size.x - 1) - pos.x, pos.y, (self.size.z - 1) - pos.z)
				elif angle == 3:
					pos = vec3((self.size.z - 1) - pos.z, pos.y, pos.x)
				self.set_voxel(f, pos, mat)

	# Mirror the sprite along the given axes
	def flip(self, x: bool, y: bool, z: bool):
		for f in range(len(self.frames)):
			voxels = self.frames[f]
			self.clear(f)
			for pos, mat in voxels.get_voxels():
				if x:
					pos = vec3((self.size.x - 1) - pos.x, pos.y, pos.z)
				if y:
					pos = vec3(pos.x, (self.size.y - 1) - pos.y, pos.z)
				if z:
					pos = vec3(pos.x, pos.y, (self.size.z - 1) - pos.z)
				self.set_voxel(f, pos, mat)

	# Mix another sprite of the same size into the given sprite, None ignores changes so empty spaces don't override
	# If the frame count of either sprite is shorter, only the amount of sprites that correspond will be mixed
	# This operation is only supported if the X Y Z axes of the sprite are all equal, meshes of unequal size can't be mixed
	def mix(self, other):
		if self.size.x != other.size.x or self.size.y != other.size.y or self.size.z != other.size.z:
			print("Warning: Can't mix sprites of uneven size, " + str(self.size) + " and " + str(other.size) + " are not equal.")
			return

		for f in range(min(len(self.frames), len(other.frames))):
			voxels = other.frames[f]
			for pos, mat in voxels.get_voxels():
				if mat:
					self.set_voxel(f, pos, mat)

	# Add or remove a voxel at a single position, can be None to clear the voxel
	# Position is local to the object and starts from the minimum corner, each axis should range between 0 and self.size - 1
	# The material applied to the voxel is copied to allow modifying properties per voxel without changing the original material definition
	def set_voxel(self, frame: int, pos: vec3, mat: Material):
		if pos.x < 0 or pos.x >= self.size.x or pos.y < 0 or pos.y >= self.size.y or pos.z < 0 or pos.z >= self.size.z:
			print("Warning: Attempted to set voxel outside of object boundaries at position " + str(pos) + ".")
			return

		voxels = self.frames[frame]
		voxels.set_voxel(pos, mat)

	# Same as set_voxel but modifies voxels in a cubic area instead of a point
	def set_voxel_area(self, frame: int, pos_min: vec3, pos_max: vec3, mat: Material):
		for x in range(math.trunc(pos_min.x), math.trunc(pos_max.x + 1)):
			for y in range(math.trunc(pos_min.y), math.trunc(pos_max.y + 1)):
				for z in range(math.trunc(pos_min.z), math.trunc(pos_max.z + 1)):
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
		# pos is the center of the object in world space, size is half of the active sprite size and represents distance from the origin to each bounding box surface
		# mins and maxs represent the start and end corners in world space, updated when moving the object to avoid costly checks during ray tracing
		# When a sprite is set the object is resized to its position and voxels will be fetched from it, setting the sprite to None disables this object
		# The object holds 4 sprites for every direction angle (0* 90* 180* 270*), the set_sprite function can also take a single sprite to disable rotation
		self.pos = "pos" in settings and settings["pos"] or vec3(0, 0, 0)
		self.rot = "rot" in settings and settings["rot"] or vec3(0, 0, 0)
		self.physics = "physics" in settings and settings["physics"] or False

		self.cam_pos = None
		self.size = self.mins = self.maxs = vec3(0, 0, 0)
		self.sprites = [None] * 4
		self.move(self.pos)
		objects.append(self)

	# Disable this object and remove it from the global object list
	def remove(self):
		objects.remove(self)

	# Create a copy of this object that can be edited independently
	def clone(self):
		return copy.deepcopy(self)

	# Check whether another item intersects the bounding box of this object, pos_min and pos_max represent the corners of another box or a point if identical
	def intersects(self, pos_min: vec3, pos_max: vec3):
		return pos_min < self.maxs + 1 and pos_max > self.mins

	# Move this object to a new origin, update mins and maxs to represent the bounding box in space
	def move(self, pos):
		if pos.x != 0 or pos.y != 0 or pos.z != 0:
			self.pos += pos
			self.mins = self.pos.int() - self.size
			self.maxs = self.pos.int() + self.size

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

	# Physics function, detects collisions with other objects and moves this object to the nearest empty space if one is available
	def unstick(self):
		if self.physics and self.sprites[0]:
			# Store the world positions of solid voxels in this object
			points_self = []
			for pos, mat in self.get_sprite().get_voxels(None):
				if mat and mat.solid:
					pos_world = self.maxs - pos
					points_self.append(pos_world)

			# Store the world positions of solid voxels in other objects that intersect self's bounding box within a border radius of one voxel
			points_other = []
			for obj in objects:
				if obj != self and obj.sprites[0] and obj.intersects(self.mins - 1, self.maxs + 1):
					for pos, mat in obj.get_sprite().get_voxels(None):
						if mat and mat.solid:
							pos_world = obj.maxs - pos
							if pos_world >= self.mins - 1 and pos_world <= self.maxs + 1:
								points_other.append(pos_world)

			# Check at which positions any voxel in this object overlaps that of another object, note which directions are solid in the same order: No offset, -X, +X, -Y, +Y, -Z, +Z
			# Iteration is done over the list of other points instead of self's points since it's expected to be smaller, an object should usually only intersect by 1 unit
			# If there are no collisions at the current position, there's no need to move the object and check other slots so the check ends at the first item
			offsets = [vec3(0, 0, 0), vec3(-1, 0, 0), vec3(+1, 0, 0), vec3(0, -1, 0), vec3(0, +1, 0), vec3(0, 0, -1), vec3(0, 0, +1)]
			collides = [False] * len(offsets)
			for i in range(len(offsets)):
				for pos_other in points_other:
					if pos_other - offsets[i] in points_self:
						collides[i] = True
						break
				if i == 0 and not collides[i]:
					break

			# Pick a valid direction to move the object in, give priority to the Y axis so stairs and floors push players upward before acting as walls
			if collides[0]:
				if not collides[3]:
					self.move(vec3(0, -1, 0))
				elif not collides[4]:
					self.move(vec3(0, +1, 0))
				elif not collides[1]:
					self.move(vec3(-1, 0, 0))
				elif not collides[2]:
					self.move(vec3(+1, 0, 0))
				elif not collides[5]:
					self.move(vec3(0, 0, -1))
				elif not collides[6]:
					self.move(vec3(0, 0, +1))

	# Set a sprite as the active sprite, None removes the sprite from this object and disables it
	# If more than one sprite is provided, store up 4 sprites representing object angles
	# Set the size and bounding box of the object to that of its sprite, or a point if the sprite is disabled
	def set_sprite(self, *sprites):
		self.size = self.mins = self.maxs = vec3(0, 0, 0)
		for i in range(len(sprites)):
			self.sprites[i] = sprites[i]
		if self.sprites[0]:
			self.size = self.sprites[0].size / 2
			self.size = self.size.int()
			self.mins = self.pos.int() - self.size
			self.maxs = self.pos.int() + self.size

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
