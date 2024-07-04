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
	width = cfg.getint("WINDOW", "width") or 64,
	height = cfg.getint("WINDOW", "height") or 64,
	scale = cfg.getint("WINDOW", "scale") or 1,
	smooth = cfg.getfloat("WINDOW", "smooth") or 0,
	fps = cfg.getint("WINDOW", "fps") or 0,

	sync = cfg.getboolean("RENDER", "sync") or False,
	culling = cfg.getboolean("RENDER", "culling") or False,
	static = cfg.getboolean("RENDER", "static") or False,
	samples = cfg.getint("RENDER", "samples") or 1,
	shutter = cfg.getfloat("RENDER", "shutter") or 0,
	spill = cfg.getfloat("RENDER", "spill") or 0,
	iris = cfg.getfloat("RENDER", "iris") or 0,
	iris_time = cfg.getfloat("RENDER", "iris_time") or 0,
	bloom = cfg.getfloat("RENDER", "bloom") or 0,
	bloom_blur = cfg.getfloat("RENDER", "bloom_blur") or 0,
	fov = cfg.getfloat("RENDER", "fov") or 90,
	falloff = cfg.getfloat("RENDER", "falloff") or 0,
	chunk_rate = cfg.getint("RENDER", "chunk_rate") or 0,
	chunk_size = cfg.getint("RENDER", "chunk_size") or 16,
	chunk_lod = cfg.getint("RENDER", "chunk_lod") or 1,
	dof = cfg.getfloat("RENDER", "dof") or 0,
	batches = cfg.getint("RENDER", "batches") or 1,
	dist_min = cfg.getint("RENDER", "dist_min") or 0,
	dist_max = cfg.getint("RENDER", "dist_max") or 32,
	max_light = cfg.getfloat("RENDER", "max_light") or 0,
	max_bounces = cfg.getfloat("RENDER", "max_bounces") or 0,
	lod_bounces = cfg.getfloat("RENDER", "lod_bounces") or 0,
	lod_samples = cfg.getfloat("RENDER", "lod_samples") or 0,
	lod_random = cfg.getfloat("RENDER", "lod_random") or 0,
	lod_edge = cfg.getfloat("RENDER", "lod_edge") or 0,
	threads = cfg.getint("RENDER", "threads") or mp.cpu_count(),

	gravity = cfg.getfloat("PHYSICS", "gravity") or 0,
	friction = cfg.getfloat("PHYSICS", "friction") or 0,
	friction_air = cfg.getfloat("PHYSICS", "friction_air") or 0,
	speed_jump = cfg.getfloat("PHYSICS", "speed_jump") or 1,
	speed_move = cfg.getfloat("PHYSICS", "speed_move") or 1,
	speed_mouse = cfg.getfloat("PHYSICS", "speed_mouse") or 1,
	max_velocity = cfg.getfloat("PHYSICS", "max_velocity") or 0,
	max_pitch = cfg.getfloat("PHYSICS", "max_pitch") or 0,
	dist_move = cfg.getint("PHYSICS", "dist_move") or 0,
)
settings.proportions = ((settings.width + settings.height) / 2) / max(settings.width, settings.height)
settings.chunk_time = settings.chunk_rate / 1000
settings.chunk_radius = round(settings.chunk_size / 2)

# Obtain the number of tiles and store their bounding boxes as (x_min, y_min, x_max, y_max)
tile_x, tile_y = grid(settings.threads)
tile_x, tile_y = (tile_x, tile_y) if settings.width > settings.height else (tile_y, tile_x)
settings.tile_size = math.trunc(settings.width // tile_x), math.trunc(settings.height // tile_y)
settings.tile = []
for x in range(tile_x):
	for y in range(tile_y):
		settings.tile.append((x * settings.tile_size[0], y * settings.tile_size[1], x * settings.tile_size[0] + settings.tile_size[0], y * settings.tile_size[1] + settings.tile_size[1]))

# Variables for global instances such as objects and chunk updates, accessed by the window and camera
objects = []
objects_chunks_update = []
background = None

# Material: A subset of Frame, used to store the physical properties of a virtual atom
class Material:
	def __init__(self, **settings):
		self.function = settings["function"] if  "function" in settings else None
		for s in settings:
			setattr(self, s, settings[s])

	# Create a copy of this material that can be edited independently
	def copy(self):
		return copy.deepcopy(self)

# Frame: A subset of Sprite, also used by camera chunks to store render data, stores instances of Material to describe a single 3D model
class Frame:
	def __init__(self, **settings):
		# If voxel compression is enabled, describe full areas as their min / max corners instead of storing every voxel individually
		# If LOD is higher than 1, positions will be interpreted in lower steps so less data is used to represent a greater area
		self.packed = settings["packed"] if "packed" in settings else False
		self.lod = settings["lod"] if "lod" in settings else 1

		# data3 stores a single material at a precise position and is indexed by (x, y, z)
		# data6 stores a cubic area filled with a material and is indexed by (x_min, y_min, z_min, x_max, y_max, z_max)
		self.data3 = {}
		self.data6 = {}

	def clear(self):
		self.data3 = {}
		self.data6 = {}

	# Get all voxels from the frame, copies data3 as is then adds every point within data6
	def get_voxels(self):
		items = dict(self.data3)
		for post6, mat in self.data6.items():
			for x in range(post6[0], post6[3] + 1):
				for y in range(post6[1], post6[4] + 1):
					for z in range(post6[2], post6[5] + 1):
						post3 = (x, y, z)
						items[post3] = mat
		return items

	# Get the voxel at this position from the frame, attempt to fetch by index from data3 followed by scanning data6 if not found
	def get_voxel(self, pos: vec3):
		pos = pos.snapped(self.lod) if self.lod > 1 else pos
		post3 = pos.tuple()
		if post3 in self.data3:
			return self.data3[post3]
		else:
			for post6, mat in self.data6.items():
				if pos.x >= post6[0] and pos.x <= post6[3] and pos.y >= post6[1] and pos.y <= post6[4] and pos.z >= post6[2] and pos.z <= post6[5]:
					return mat
		return None

	# Set a voxel at this position on the frame, unpack the affected area since its content will be changed
	def set_voxel(self, pos: vec3, mat: Material):
		pos = pos.snapped(self.lod) if self.lod > 1 else pos
		self.unpack(pos)
		post3 = pos.tuple()
		if mat:
			self.data3[post3] = mat
		else:
			del self.data3[post3]
		self.pack()

	# Set a list of voxels provided in the same format as data3
	def set_voxels(self, voxels: dict):
		for post3, mat in voxels.items():
			pos = vec3(post3[0], post3[1], post3[2])
			pos = pos.snapped(self.lod) if self.lod > 1 else pos
			self.unpack(pos)
			if mat:
				self.data3[post3] = mat
			else:
				del self.data3[post3]
		self.pack()

	# Decompress boxes in data6 to points in data3, position determines which box was touched and needs to be unpacked
	def unpack(self, pos: vec3):
		for post6, mat in self.data6.items():
			if pos.x >= post6[0] and pos.x <= post6[3] and pos.y >= post6[1] and pos.y <= post6[4] and pos.z >= post6[2] and pos.z <= post6[5]:
				for x in range(post6[0], post6[3] + 1):
					for y in range(post6[1], post6[4] + 1):
						for z in range(post6[2], post6[5] + 1):
							post3 = (x, y, z)
							self.data3[post3] = mat
				del self.data6[post6]
				break

	# Compress points in data3 to boxes in data6
	def pack(self):
		pack = self.packed
		while pack:
			pack = False

			# Find the first valid voxel to start scanning from, the search area expands from a line to a plane to a cube in reverse order of -X, +X, -Y, +Y, -Z, +Z
			# Search size increases by one unit on each axis as long as voxels of the same material fill the new slice, remove each direction once we found its last full slice
			for post3, mat in self.data3.items():
				pos_min = pos_max = vec3(post3[0], post3[1], post3[2])
				pos_dirs = [vec3(-1, 0, 0), vec3(+1, 0, 0), vec3(0, -1, 0), vec3(0, +1, 0), vec3(0, 0, -1), vec3(0, 0, +1)]
				while pos_dirs:
					pos_dir = pos_dirs[-1]
					pos_slice_min = pos_min + pos_dir if pos_dir.x < 0 or pos_dir.y < 0 or pos_dir.z < 0 else pos_max
					pos_slice_max = pos_max + pos_dir if pos_dir.x > 0 or pos_dir.y > 0 or pos_dir.z > 0 else pos_min
					for x in range(pos_slice_min.x, pos_slice_max.x + 1):
						for y in range(pos_slice_min.y, pos_slice_max.y + 1):
							for z in range(pos_slice_min.z, pos_slice_max.z + 1):
								post = (x, y, z)
								if not post in self.data3 or self.data3[post] != mat:
									pos_dirs.pop(-1)
								if not pos_dir in pos_dirs:
									break
							if not pos_dir in pos_dirs:
								break
						if not pos_dir in pos_dirs:
							break
					if pos_dir in pos_dirs:
						pos_min += pos_dir.min(0)
						pos_max += pos_dir.max(0)

				# If an area larger than a point exists, remove single voxels from data3 and define them as boxes in data6
				# The contents of data3 will be modified and are no longer valid this turn, stop the current search and tell the main loop to run again
				if pos_min.x < pos_max.x or pos_min.y < pos_max.y or pos_min.z < pos_max.z:
					for x in range(pos_min.x, pos_max.x + 1):
						for y in range(pos_min.y, pos_max.y + 1):
							for z in range(pos_min.z, pos_max.z + 1):
								post = (x, y, z)
								if post in self.data3:
									del self.data3[post]
					post6 = pos_min.tuple() + pos_max.tuple()
					self.data6[post6] = mat
					pack = True
					break

# Sprite: A subset of Object, stores multiple instances of Frame which can be animated or transformed to produce an usable 3D image
class Sprite:
	def __init__(self, **settings):
		# Sprite size needs to be an even number as to not break object calculations, voxels are located at integer positions and checking voxel position from object center would result in 0.5
		self.size = settings["size"] if "size" in settings else vec3(0, 0, 0)
		self.lod = settings["lod"] if "lod" in settings else 1
		if self.size.x % 2 or self.size.y % 2 or self.size.z % 2:
			print("Warning: Sprite size " + str(self.size) + " contains a float or odd number in one or more directions, affected axes will be rounded and enlarged by one unit.")
			self.size.x = math.trunc(self.size.x) + 1 if math.trunc(self.size.x) % 2 != 0 else math.trunc(self.size.x)
			self.size.y = math.trunc(self.size.y) + 1 if math.trunc(self.size.y) % 2 != 0 else math.trunc(self.size.y)
			self.size.z = math.trunc(self.size.z) + 1 if math.trunc(self.size.z) % 2 != 0 else math.trunc(self.size.z)

		# Animation properties and the frame list used to store multiple voxel meshes representing animation frames
		self.frame = self.frame_time = self.frame_start = self.frame_end = 0
		self.frames = []
		for i in range(settings["frames"]):
			self.frames.append(Frame(packed = True, lod = self.lod))

	# Create a copy of this sprite that can be edited independently
	def copy(self):
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
			self.frame = math.trunc(self.frame_start + (pg.time.get_ticks() // self.frame_time) % (self.frame_end - self.frame_start + 1))

	# Mix another sprite of the same size into the given sprite, None ignores changes so empty spaces don't override
	# If the frame count of either sprite is shorter, only the amount of sprites that correspond will be mixed
	# This operation is only supported if the X Y Z axes of the sprite are all equal, meshes of unequal size can't be mixed
	def mix(self, other):
		if self.size.x != other.size.x or self.size.y != other.size.y or self.size.z != other.size.z:
			print("Warning: Can't mix sprites of uneven size, " + str(self.size) + " and " + str(other.size) + " are not equal.")
			return

		for f in range(min(len(self.frames), len(other.frames))):
			frame = other.frames[f]
			for post, mat in frame.get_voxels().items():
				if mat:
					pos = vec3(post[0], post[1], post[2])
					self.set_voxel(f, pos, mat)

	# Get the relevant frame of the sprite, can be None to retreive the active frame instead of a specific frame
	def get_frame(self, frame):
		if isinstance(frame, int):
			return self.frames[frame]
		return self.frames[self.frame]

	# Add or remove a voxel at a single position, can be None to clear the voxel
	# Position is local to the object and starts from the minimum corner, each axis should range between 0 and self.size - 1
	# The material applied to the voxel is copied to allow modifying properties per voxel without changing the original material definition
	def set_voxel(self, frame: int, pos: vec3, mat: Material):
		if pos.x < 0 or pos.x >= self.size.x or pos.y < 0 or pos.y >= self.size.y or pos.z < 0 or pos.z >= self.size.z:
			print("Warning: Attempted to set voxel outside of object boundaries at position " + str(pos) + ".")
			return

		self.get_frame(frame).set_voxel(pos, mat)

	# Set a list of voxels in which each item is a tuple of the form (position, material)
	def set_voxels(self, frame: int, voxels: list):
		for post, mat in voxels.items():
			pos = vec3(post[0], post[1], post[2])
			if pos.x < 0 or pos.x >= self.size.x or pos.y < 0 or pos.y >= self.size.y or pos.z < 0 or pos.z >= self.size.z:
				print("Warning: Attempted to set voxel list containing voxels outside of object boundaries at position " + str(pos) + ".")
				return

		self.get_frame(frame).set_voxels(voxels)

	# Fill the cubic area between min and max corners with the given material
	def set_voxels_area(self, frame: int, pos_min: vec3, pos_max: vec3, mat: Material):
		if pos_min.x < 0 or pos_max.x >= self.size.x or pos_min.y < 0 or pos_max.y >= self.size.y or pos_min.z < 0 or pos_max.z >= self.size.z:
			print("Warning: Attempted to set voxel area outside of object boundaries between positions " + str(pos_min) + " and " + str(pos_max) + ".")
			return

		voxels = {}
		for x in range(math.trunc(pos_min.x), math.trunc(pos_max.x + 1)):
			for y in range(math.trunc(pos_min.y), math.trunc(pos_max.y + 1)):
				for z in range(math.trunc(pos_min.z), math.trunc(pos_max.z + 1)):
					post = (x, y, z)
					voxels[post] = mat
		self.get_frame(frame).set_voxels(voxels)

	# Flip the position at which the voxel is being fetched and return the modified position
	# Allows reading a mirrored version of the sprite
	def pos_flipped(self, pos: vec3, x: bool, y: bool, z: bool):
		end = self.size - 1
		if x:
			pos = vec3(end.x - pos.x, pos.y, pos.z)
		if y:
			pos = vec3(pos.x, end.y - pos.y, pos.z)
		if z:
			pos = vec3(pos.x, pos.y, end.z - pos.z)
		return pos

	# Rotate the position at which the voxel is being fetched and return the modified position
	# Allows reading a different rotation of the sprite, used by rotated objects by default
	# Rotation is only possible when the two axes opposite the rotation axis are equal in size
	def pos_rotated(self, pos: vec3, rot: vec3):
		end = self.size - 1
		angle_x = round(rot.x / 90) % 4
		angle_y = round(rot.y / 90) % 4
		angle_z = round(rot.z / 90) % 4

		# Rotate across the X axis
		if angle_x and self.size.y == self.size.z:
			if angle_x == 1:
				pos = vec3(pos.x, end.z - pos.z, pos.y)
			elif angle_x == 2:
				pos = vec3(pos.x, end.y - pos.y, end.z - pos.z)
			elif angle_x == 3:
				pos = vec3(pos.x, pos.z, end.y - pos.y)

		# Rotate across the Y axis
		if angle_y and self.size.x == self.size.z:
			if angle_y == 1:
				pos = vec3(pos.z, pos.y, end.x - pos.x)
			elif angle_y == 2:
				pos = vec3(end.x - pos.x, pos.y, end.z - pos.z)
			elif angle_y == 3:
				pos = vec3(end.z - pos.z, pos.y, pos.x)

		# Rotate across the Z axis
		if angle_z and self.size.x == self.size.y:
			if angle_z == 1:
				pos = vec3(end.y - pos.y, pos.x, pos.z)
			elif angle_z == 2:
				pos = vec3(end.x - pos.x, end.y - pos.y, pos.z)
			elif angle_z == 3:
				pos = vec3(pos.y, end.x - pos.x, pos.z)

		return pos

	# Get the voxel at this position on the given frame, returns the material or None if empty or out of range
	# Position is in local space, always convert the position to local coordinates before calling this
	# The position is interpreted at the desired rotation, always provide the object rotation if this sprite belongs to an object
	# Frame can be None to retreive the active frame instead of a specific frame, use this when drawing the sprite
	def get_voxel(self, frame: int, pos: vec3, rot: vec3):
		pos = self.pos_rotated(pos, rot)
		return self.get_frame(frame).get_voxel(pos)

	# Return a list of all voxels on the given frame
	def get_voxels(self, frame: int):
		return self.get_frame(frame).get_voxels()

	# Clear all voxels on the given frame
	def clear(self, frame: int):
		self.get_frame(frame).clear()

# Object: The base class for objects in the world, uses up to 4 instances of Sprite representing different rotation angles
class Object:
	def __init__(self, **settings):
		# pos is the center of the object in world space, size is half of the active sprite size and represents distance from the origin to each bounding box surface
		# mins and maxs represent the integer start and end corners in world space, updated when moving the object to avoid costly checks during ray tracing
		# When a sprite is set the object is resized to its position and voxels will be fetched from it, setting the sprite to None disables this object
		# The object holds 4 sprites for every direction angle (0* 90* 180* 270*), the set_sprite function can also take a single sprite to disable rotation
		self.pos = settings["pos"] if "pos" in settings else vec3(0, 0, 0)
		self.rot = settings["rot"] if "rot" in settings else vec3(0, 0, 0)
		self.vel = settings["vel"] if "vel" in settings else vec3(0, 0, 0)
		self.physics = settings["physics"] if "physics" in settings else False
		self.function = settings["function"] if  "function" in settings else None

		self.visible = False
		self.size = self.mins = self.maxs = vec3(0, 0, 0)
		self.weight = 0
		self.sprite = None
		self.cam_pos = None
		self.move(self.pos)
		objects.append(self)

	# Disable this object and remove it from the global object list
	def remove(self):
		self.area_update()
		objects.remove(self)

	# Create a copy of this object that can be edited independently
	def copy(self):
		return copy.deepcopy(self)

	# Mark that chunks touching the sprite of this object need to be recalculated by the renderer, used when the object's sprite or position changes
	# If the object moved or its sprite size has changed, this must be ran both before and after the change as to refresh chunks in both cases
	def area_update(self):
		if self.mins < self.maxs:
			pos_min = self.mins.snapped(settings.chunk_size)
			pos_max = self.maxs.snapped(settings.chunk_size)
			for x in range(pos_min.x, pos_max.x + 1, settings.chunk_size):
				for y in range(pos_min.y, pos_max.y + 1, settings.chunk_size):
					for z in range(pos_min.z, pos_max.z + 1, settings.chunk_size):
						pos = vec3(x, y, z)
						if not pos in objects_chunks_update:
							objects_chunks_update.append(pos)

	# Check whether another item intersects the bounding box of this object, pos_min and pos_max represent the corners of another box or a point if identical
	def intersects(self, pos_min: vec3, pos_max: vec3):
		return pos_min <= self.maxs and pos_max >= self.mins

	# Change the virtual rotation of the object by the given amount, pitch is limited to the provided value
	def rotate(self, rot: vec3, limit_pitch: float):
		if rot != 0:
			# Trigger a render update if the new rotation crosses a 90* step and changes the sprite rotation
			angle_x_old = round(self.rot.x / 90) % 4
			angle_y_old = round(self.rot.y / 90) % 4
			angle_z_old = round(self.rot.z / 90) % 4
			self.rot = self.rot.rotate(rot)
			angle_x_new = round(self.rot.x / 90) % 4
			angle_y_new = round(self.rot.y / 90) % 4
			angle_z_new = round(self.rot.z / 90) % 4
			if angle_x_new != angle_x_old or angle_y_new != angle_y_old or angle_z_new != angle_z_old:
				self.area_update()

			# Limit the pitch for special objects such as the player camera
			if limit_pitch:
				pitch_min = max(180, 360 - limit_pitch)
				pitch_max = min(180, limit_pitch)
				if self.rot.z > pitch_max and self.rot.z <= 180:
					self.rot.z = pitch_max
				if self.rot.z < pitch_min and self.rot.z > 180:
					self.rot.z = pitch_min

	# Teleport the object to this origin, use only when necessary and prefer impulse instead
	def move(self, pos):
		if pos != self.pos:
			self.area_update()
			self.pos = pos
			self.mins = math.trunc(self.pos) - self.size
			self.maxs = math.trunc(self.pos) + self.size
			self.area_update()

	# Add velocity to this object, 1 is the maximum speed allowed for objects
	def impulse(self, vel):
		self.vel += vel

	# Physics engine, applies velocity accounting for collisions with other objects and moves this object to the nearest empty space if one is available
	def update_physics(self):
		friction = elasticity = 0
		self_spr = self.get_sprite()
		vel_steps = self.vel
		while(vel_steps != 0):
			# Directions and their corresponding slice boundaries that will be checked, in order -X, +X, -Y, +Y, -Z, +Z
			pos_dirs = {
				(-1, 0, 0): (self.mins.x - 1, self.mins.y + 0, self.mins.z + 0, self.mins.x + 0, self.maxs.y + 0, self.maxs.z + 0),
				(+1, 0, 0): (self.maxs.x + 0, self.mins.y + 0, self.mins.z + 0, self.maxs.x + 1, self.maxs.y + 0, self.maxs.z + 0),
				(0, -1, 0): (self.mins.x + 0, self.mins.y - 1, self.mins.z + 0, self.maxs.x + 0, self.mins.y + 0, self.maxs.z + 0),
				(0, +1, 0): (self.mins.x + 0, self.maxs.y + 0, self.mins.z + 0, self.maxs.x + 0, self.maxs.y + 1, self.maxs.z + 0),
				(0, 0, -1): (self.mins.x + 0, self.mins.y + 0, self.mins.z - 1, self.maxs.x + 0, self.maxs.y + 0, self.mins.z + 0),
				(0, 0, +1): (self.mins.x + 0, self.mins.y + 0, self.maxs.z + 0, self.maxs.x + 0, self.maxs.y + 0, self.maxs.z + 1),
			}

			# Check collisions in the direction of velocity, unnecessary directions are discarded before scanning other objects
			for post3_dir, post6 in dict(pos_dirs).items():
				pos_dir = vec3(post3_dir[0], post3_dir[1], post3_dir[2])
				if not pos_dir.x * self.vel.x > 0 and not pos_dir.y * self.vel.y > 0 and not pos_dir.z * self.vel.z > 0:
					del pos_dirs[post3_dir]
				else:
					for obj in objects:
						if obj != self and obj.visible and obj.intersects(vec3(post6[0], post6[1], post6[2]), vec3(post6[3], post6[4], post6[5])):
							# If we're colliding with another physical object, transfer velocity based on weight difference and projectile speed
							if obj.physics:
								vel = self.vel * max(0, min(1, abs(self.vel).maxs() * self.weight - obj.weight))
								self.vel -= vel
								obj.vel += vel

							# If a direction collides with any solid voxels, it's removed from the list to mark it as invalid for movement
							# This check is also used to apply friction and elasticity from all neighboring voxels the object is touching
							obj_spr = obj.get_sprite()
							for x in range(post6[0], post6[3] + 1):
								for y in range(post6[1], post6[4] + 1):
									for z in range(post6[2], post6[5] + 1):
										pos = vec3(x, y, z)
										obj_mat = obj_spr.get_voxel(None, pos - obj.mins, obj.rot)
										if obj_mat and obj_mat.solidity > random.random():
											self_mat = self_spr.get_voxel(None, pos - self.mins - pos_dir, self.rot)
											if self_mat and self_mat.solidity > random.random():
												friction += obj_mat.friction * self_mat.friction * settings.friction
												elasticity += obj_mat.elasticity * self_mat.elasticity * settings.friction
												if post3_dir in pos_dirs:
													del pos_dirs[post3_dir]

			# Preform a move in at most one unit, extract the amount of movement for this call from the total number of steps
			# If velocity is greater than 1 the main loop will continue until the total velocity has been applied
			# Note: Diagonal movement may intersect corners as direction checks only account for one axis
			vel_step = vel_steps.max(-1).min(+1)
			vel_steps -= vel_step
			vel_dirs = vec3(0, 0, 0)
			for post in pos_dirs:
				vel_dirs += vec3(post[0], post[1], post[2])
			self.move(self.pos + vel_step * abs(vel_dirs))

		# Apply global effects to velocity then bound it to the terminal velocity
		self.vel -= vec3(0, self.weight * settings.gravity, 0)
		self.vel -= self.vel * elasticity
		self.vel /= 1 + friction
		self.vel *= 1 - settings.friction_air
		self.vel = self.vel.min(+settings.max_velocity).max(-settings.max_velocity)

	# Update this object, called by the window every frame
	# An immediate renderer update is issued when the object changes visibility or the sprite animation advances
	def update(self, pos_cam: vec3):
		# Determine object visibility based on available sprites and the object's distance to the camera
		visible_old = self.visible
		self.visible = self.sprite and self.pos.distance(pos_cam) <= settings.dist_max + self.size.maxs()
		visible_new = self.visible
		if visible_old != visible_new:
			self.area_update()

		# Update the animation frame and calculate physics based on the new sprite, limited by the physics sleep distance setting
		if self.visible and self.pos.distance(pos_cam) <= settings.dist_move:
			spr = self.get_sprite()
			frame_old = spr.frame
			spr.anim_update()
			frame_new = spr.frame
			if frame_old != frame_new:
				self.set_weight()
				self.area_update()

			if self.physics:
				self.update_physics()
			if self.function:
				self.function(self)

	# Set a sprite as the active sprite, None removes the sprite and disables the object
	# Set the size and bounding box of the object to that of its sprite, or a point if the sprite is disabled
	def set_sprite(self, sprite):
		self.area_update()
		self.size = self.mins = self.maxs = vec3(0, 0, 0)
		if sprite:
			self.sprite = sprite
			self.size = math.trunc(self.sprite.size / 2)
			self.mins = math.trunc(self.pos) - self.size
			self.maxs = math.trunc(self.pos) + self.size
		self.set_weight()
		self.area_update()

	# Get the sprite assigned to this object
	# Use the angles of this object when fetching voxels from the sprite to get the correct rotation
	def get_sprite(self):
		return self.sprite

	# Calculate the weight of the object from the total weigh of its voxels
	def set_weight(self):
		self.weight = 0
		if self.sprite:
			for mat in self.sprite.get_voxels(None).values():
				self.weight += mat.weight

	# Mark that we want to attach the camera to this object at the provided position offset
	# The camera can only be attached to one object at a time, this will remove the setting from all other objects
	def set_camera(self, pos: vec2):
		for obj in objects:
			obj.cam_pos = pos if obj == self else None

# Execute the init script of the loaded mod
importlib.import_module("mods." + mod + ".init")
