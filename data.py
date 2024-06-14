#!/usr/bin/python3
from lib import *
import multiprocessing as mp

import configparser
import importlib
import copy
import math

import pygame as pg

# Fetch the mod name and load the config from the mod path
mod = sys.argv[1].strip() if len(sys.argv) > 1 else "default"
cfg = configparser.RawConfigParser()
cfg.read("mods/" + mod + "/config.cfg")
settings = store(
	width = cfg.getint("WINDOW", "width") or 96,
	height = cfg.getint("WINDOW", "height") or 64,
	scale = cfg.getint("WINDOW", "scale") or 8,
	smooth = cfg.getboolean("WINDOW", "smooth") or False,
	fps = cfg.getint("WINDOW", "fps") or 24,

	sync = cfg.getboolean("RENDER", "sync") or False,
	static = cfg.getboolean("RENDER", "static") or False,
	samples = cfg.getint("RENDER", "samples") or 1,
	fov = cfg.getfloat("RENDER", "fov") or 90,
	falloff = cfg.getfloat("RENDER", "falloff") or 0,
	chunk_size = cfg.getint("RENDER", "chunk_size") or 16,
	dof = cfg.getfloat("RENDER", "dof") or 0,
	skip = cfg.getfloat("RENDER", "skip") or 0,
	dist_min = cfg.getint("RENDER", "dist_min") or 0,
	dist_max = cfg.getint("RENDER", "dist_max") or 48,
	terminate_hits = cfg.getfloat("RENDER", "terminate_hits") or 0,
	terminate_dist = cfg.getfloat("RENDER", "terminate_dist") or 0,
	threads = cfg.getint("RENDER", "threads") or mp.cpu_count(),

	speed_jump = cfg.getfloat("PHYSICS", "speed_jump") or 10,
	speed_move = cfg.getfloat("PHYSICS", "speed_move") or 1,
	speed_mouse = cfg.getfloat("PHYSICS", "speed_mouse") or 10,
	max_pitch = cfg.getfloat("PHYSICS", "max_pitch") or 0,
)

# Variables for global instances such as objects and chunk updates, accessed by the window and camera
objects = []
objects_chunks_update = []
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

# Frame: A subset of Sprite, also used by camera chunks to store render data, stores instances of Material to describe a single 3D model
class Frame:
	def __init__(self):
		self.clear()

	def clear(self):
		self.data = {}

	def get_voxels(self):
		items = []
		for post in self.data:
			items.append((vec3(post[0], post[1], post[2]), self.data[post]))
		return items

	def get_voxel(self, pos: vec3):
		post = pos.tuple()
		if post in self.data:
			return self.data[post]
		return None

	def set_voxel(self, pos: vec3, mat: Material):
		post = pos.tuple()
		if mat:
			self.data[post] = mat
		else:
			del self.data[post]

# Sprite: A subset of Object, stores multiple instances of Frame which can be animated or transformed to produce an usable 3D image
class Sprite:
	def __init__(self, **settings):
		# Sprite size needs to be an even number as to not break object calculations, voxels are located at integer positions and checking voxel position from object center would result in 0.5
		self.size = settings["size"] if "size" in settings else vec3(0, 0, 0)
		if self.size.x % 2 != 0 or self.size.y % 2 != 0 or self.size.z % 2 != 0:
			print("Warning: Sprite size " + str(self.size) + " contains a float or odd number in one or more directions, affected axes will be rounded and enlarged by one unit.")
			self.size.x = math.trunc(self.size.x) + 1 if math.trunc(self.size.x) % 2 != 0 else math.trunc(self.size.x)
			self.size.y = math.trunc(self.size.y) + 1 if math.trunc(self.size.y) % 2 != 0 else math.trunc(self.size.y)
			self.size.z = math.trunc(self.size.z) + 1 if math.trunc(self.size.z) % 2 != 0 else math.trunc(self.size.z)

		# Animation properties and the frame list used to store multiple voxel meshes representing animation frames
		self.frame = self.frame_time = self.frame_start = self.frame_end = 0
		self.frames = []
		for i in range(settings["frames"]):
			self.frames.append(Frame())

	# Create a copy of this sprite that can be edited independently
	def clone(self):
		return copy.deepcopy(self)

	# Set the animation range and speed at which it should be played
	# If animation time is negative the animation will play backwards
	def anim_set(self, frame_start: int, frame_end: int, frame_time: float):
		self.frame = 0
		self.frame_time = frame_time * 1000
		self.frame_start = min(frame_start, len(self.frames))
		self.frame_end = min(frame_end, len(self.frames))

	# Updates the animation frame that should currently be displayed based on the time
	def anim_update(self):
		if self.frame_time and len(self.frames) > 1:
			self.frame = math.trunc(self.frame_start + (pg.time.get_ticks() // self.frame_time) % (self.frame_end - self.frame_start))

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

	# Set a list of voxels in which each item is a tuple of the form (position, material)
	def set_voxels(self, frame: int, voxels: list):
		for pos, mat in voxels:
			self.set_voxel(frame, pos, mat)

	# Fill the cubic area between min and max corners with the given material
	def set_voxels_area(self, frame: int, pos_min: vec3, pos_max: vec3, mat: Material):
		voxels = []
		for x in range(math.trunc(pos_min.x), math.trunc(pos_max.x + 1)):
			for y in range(math.trunc(pos_min.y), math.trunc(pos_max.y + 1)):
				for z in range(math.trunc(pos_min.z), math.trunc(pos_max.z + 1)):
					voxels.append((vec3(x, y, z), mat))
		self.set_voxels(frame, voxels)

	# Get the voxel at this position, returns the material or None if empty or out of range
	# Position is in local space, always convert the position to local coordinates before calling this
	# Frame can be None to retreive the active frame instead of a specific frame, use this when drawing the sprite
	def get_voxel(self, frame: int, pos: vec3):
		voxels = self.frames[frame] if frame is not None else self.frames[self.frame]
		return voxels.get_voxel(pos)

	# Return a list of all voxels on the appropriate frame
	def get_voxels(self, frame: int):
		voxels = self.frames[frame] if frame is not None else self.frames[self.frame]
		return voxels.get_voxels()

	# Clear all voxels on the given frame
	def clear(self, frame: int):
		voxels = self.frames[frame] if frame is not None else self.frames[self.frame]
		voxels.clear()

# Object: The base class for objects in the world, uses up to 4 instances of Sprite representing different rotation angles
class Object:
	def __init__(self, **settings):
		# pos is the center of the object in world space, size is half of the active sprite size and represents distance from the origin to each bounding box surface
		# mins and maxs represent the start and end corners in world space, updated when moving the object to avoid costly checks during ray tracing
		# When a sprite is set the object is resized to its position and voxels will be fetched from it, setting the sprite to None disables this object
		# The object holds 4 sprites for every direction angle (0* 90* 180* 270*), the set_sprite function can also take a single sprite to disable rotation
		self.pos = settings["pos"] if "pos" in settings else vec3(0, 0, 0)
		self.rot = settings["rot"] if "rot" in settings else vec3(0, 0, 0)
		self.vel = settings["vel"] if "vel" in settings else vec3(0, 0, 0)
		self.physics = settings["physics"] if "physics" in settings else False

		self.visible = False
		self.vel_step = vec3(0, 0, 0)
		self.size = self.mins = self.maxs = vec3(0, 0, 0)
		self.sprites = [None] * 4
		self.cam_pos = None
		self.move(self.pos)
		objects.append(self)

	# Disable this object and remove it from the global object list
	def remove(self):
		self.area_update()
		objects.remove(self)

	# Create a copy of this object that can be edited independently
	def clone(self):
		return copy.deepcopy(self)

	# Mark that chunks touching the sprite of this object need to be recalculated by the renderer, used when the object's sprite or position changes
	# If the object moved or its sprite size has changed, this must be ran both before and after the change as to refresh chunks in both cases
	def area_update(self):
		if self.mins < self.maxs:
			pos_min = self.mins.snapped(settings.chunk_size, -1) + round(settings.chunk_size / 2)
			pos_max = self.maxs.snapped(settings.chunk_size, +1) + round(settings.chunk_size / 2)
			for x in range(pos_min.x, pos_max.x, settings.chunk_size):
				for y in range(pos_min.y, pos_max.y, settings.chunk_size):
					for z in range(pos_min.z, pos_max.z, settings.chunk_size):
						pos = vec3(x, y, z)
						if not pos in objects_chunks_update:
							objects_chunks_update.append(pos)

	# Check whether another item intersects the bounding box of this object, pos_min and pos_max represent the corners of another box or a point if identical
	def intersects(self, pos_min: vec3, pos_max: vec3):
		return pos_min <= self.maxs and pos_max >= self.mins

	# Change the virtual rotation of the object by the given amount, pitch is limited to the provided value
	def rotate(self, rot: vec3, limit_pitch: float):
		if rot != 0:
			# Trigger a renderer update if this rotation changed the sprite angle
			angle_old = round(self.rot.z / 90) % 4
			self.rot = self.rot.rotate(rot)
			angle_new = round(self.rot.z / 90) % 4
			if angle_new != angle_old and self.sprites[angle_new] and self.sprites[angle_old]:
				self.area_update()

			# Limit the pitch for special objects such as the player camera
			if limit_pitch:
				pitch_min = max(180, 360 - limit_pitch)
				pitch_max = min(180, limit_pitch)
				if self.rot.y > pitch_max and self.rot.y <= 180:
					self.rot.y = pitch_max
				if self.rot.y < pitch_min and self.rot.y > 180:
					self.rot.y = pitch_min

	# Teleport the object to this origin, use only when necessary and prefer impulse instead
	def move(self, pos):
		if pos != self.pos:
			self.area_update()
			self.pos = math.trunc(pos)
			self.mins = self.pos - self.size
			self.maxs = self.pos + self.size
			self.area_update()

	# Add velocity to this object, 1 is the maximum speed allowed for objects
	def impulse(self, vel):
		self.vel += vel
		self.vel = vec3(min(+1, max(-1, self.vel.x)), min(+1, max(-1, self.vel.y)), min(+1, max(-1, self.vel.z)))

	# Physics function, applies velocity accounting for collisions with other objects and moves this object to the nearest empty space if one is available
	def update_physics(self, time: float):
		if self.visible and self.physics:
			# List of offsets used to calculate neighboring object positions in order: Current position, -X, +X, -Y, +Y, -Z, +Z
			offset = [vec3(0, 0, 0), vec3(-1, 0, 0), vec3(+1, 0, 0), vec3(0, -1, 0), vec3(0, +1, 0), vec3(0, 0, -1), vec3(0, 0, +1)]
			offset_free = [True] * len(offset)
			offset_desired = [False] * len(offset)
			weight = friction = elasticity = 0

			# Check at which neighboring positions any voxel in this object overlaps that of other objects to determine which locations are free
			# The check is also used to estimate friction and elasticity, by comparing the values of all voxels that would touch at any position
			self_spr = self.get_sprite()
			for pos, mat in self_spr.get_voxels(None):
				weight += mat.weight
			for obj in objects:
				if obj != self and obj.visible and obj.intersects(self.mins - 1, self.maxs + 1):
					obj_spr = obj.get_sprite()
					for x in range(self.mins.x - 1, self.maxs.x + 2):
						for y in range(self.mins.y - 1, self.maxs.y + 2):
							for z in range(self.mins.z - 1, self.maxs.z + 2):
								pos = vec3(x, y, z)
								obj_mat = obj_spr.get_voxel(None, pos - obj.mins)
								if obj_mat and obj_mat.solidity > random.random():
									for i in range(len(offset)):
										self_mat = self_spr.get_voxel(None, pos - self.mins - offset[i])
										if self_mat:
											if self_mat.solidity > random.random():
												offset_free[i] = False
											friction += obj_mat.friction * self_mat.friction
											elasticity += obj_mat.elasticity * self_mat.elasticity

			# Modify object velocity based on weight and friction, apply velocity to the step counter and reset it when -1 or +1 is reached on an axis
			# Note which directions are desired based on velocity in the same order as offsets, current position is always false
			# If a position collides in the direction of velocity, reflect the velocity on that axis based on elasticity
			self.vel -= vec3(0, weight, 0)
			self.vel *= max(0, 1 - friction)
			for i in range(1, len(offset)):
				if not offset_free[i]:
					if (self.vel.x < 0 and offset[i].x < 0) or (self.vel.x > 0 and offset[i].x > 0):
						self.vel.x *= -min(1, elasticity)
					if (self.vel.y < 0 and offset[i].y < 0) or (self.vel.y > 0 and offset[i].y > 0):
						self.vel.y *= -min(1, elasticity)
					if (self.vel.z < 0 and offset[i].z < 0) or (self.vel.z > 0 and offset[i].z > 0):
						self.vel.z *= -min(1, elasticity)
			self.vel_step += self.vel * time
			offset_desired = [False, self.vel_step.x <= -1, self.vel_step.x >= +1, self.vel_step.y <= -1, self.vel_step.y >= +1, self.vel_step.z <= -1, self.vel_step.z >= +1]
			self.vel_step -= math.trunc(self.vel_step)

			# Pick a random direction to move to from the list of valid directions that can be preformed this execution
			# If the object is free move only to a desired position based on velocity, if the object is stuck any free position is allowed
			positions = []
			for i in range(1, len(offset)):
				if offset_free[i] and (offset_desired[i] or not offset_free[0]):
					positions.append(offset[i])
			if len(positions):
				self.move(self.pos + random.choice(positions))

	# Update this object, called by the window every frame
	# An immediate renderer update is issued when the object changes visibility or the sprite animation advances
	def update(self, pos_cam: vec3, time: float):
		# Determine object visibility based on available sprites and the object's distance to the camera
		visible_old = self.visible
		self.visible = self.sprites[0] and math.dist(self.pos.array(), pos_cam.array()) <= settings.dist_max + self.size.max()
		visible_new = self.visible
		if visible_old != visible_new:
			self.area_update()

		# Update the animation frame and calculate physics based on the new sprite
		if self.visible:
			spr = self.get_sprite()
			frame_old = spr.frame
			spr.anim_update()
			frame_new = spr.frame
			if frame_old != frame_new:
				self.area_update()

			self.update_physics(time)

	# Set a sprite as the active sprite, None removes the sprite from this object and disables it
	# If more than one sprite is provided, store up 4 sprites representing object angles
	# Set the size and bounding box of the object to that of its sprite, or a point if the sprite is disabled
	def set_sprite(self, *sprites):
		self.area_update()
		self.size = self.mins = self.maxs = vec3(0, 0, 0)
		for i in range(len(sprites)):
			self.sprites[i] = sprites[i]
		if self.sprites[0]:
			self.size = math.trunc(self.sprites[0].size / 2)
			self.mins = math.trunc(self.pos) - self.size
			self.maxs = math.trunc(self.pos) + self.size
		self.area_update()

	# Get the appropriate sprite for this object based on which 0* / 90* / 180* / 270* direction it's facing toward
	def get_sprite(self):
		angle = round(self.rot.z / 90) % 4
		if self.sprites[angle]:
			return self.sprites[angle]
		return self.sprites[0]

	# Mark that we want to attach the camera to this object at the provided position offset
	# The camera can only be attached to one object at a time, this will remove the setting from all other objects
	def set_camera(self, pos: vec2):
		for obj in objects:
			obj.cam_pos = pos if obj == self else None

# Execute the init script of the loaded mod
importlib.import_module("mods." + mod + ".init")
