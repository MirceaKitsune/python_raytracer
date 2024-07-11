#!/usr/bin/python3
from lib import *
import multiprocessing as mp

import configparser
import importlib
import gzip
import copy
import math
import random

import pygame as pg

# Fetch the mod name and load the config from the mod path
mod = sys.argv[1].strip() if len(sys.argv) > 1 else "default"
cfg = configparser.RawConfigParser()
cfg.read("mods/" + mod + "/config.cfg")
settings = store(
	width = cfg.getint("WINDOW", "width") or 64,
	height = cfg.getint("WINDOW", "height") or 64,
	scale = cfg.getint("WINDOW", "scale") or 1,
	subsamples = cfg.getfloat("WINDOW", "subsamples") or 0,
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
	chunk_lod = cfg.getint("RENDER", "chunk_lod") or 0,
	dof = cfg.getfloat("RENDER", "dof") or 0,
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
	min_velocity = cfg.getfloat("PHYSICS", "min_velocity") or 0,
	max_velocity = cfg.getfloat("PHYSICS", "max_velocity") or 0,
	max_pitch = cfg.getint("PHYSICS", "max_pitch") or 0,
	max_roll = cfg.getint("PHYSICS", "max_roll") or 0,
	dist_move = cfg.getint("PHYSICS", "dist_move") or 0,
)
settings.window = settings.width, settings.height
settings.window_scaled = settings.window[0] * settings.scale, settings.window[1] * settings.scale
settings.proportions = ((settings.width + settings.height) / 2) / max(settings.width, settings.height)
settings.chunk_time = settings.chunk_rate / 1000
settings.chunk_radius = round(settings.chunk_size / 2)

# Obtain the (x, y) pixel positions for all pixels in the canvas and assign them to the appropriate thread for rendering
settings.pixels = []
for t in range(settings.threads):
	settings.pixels.append([])
for x in range(settings.width):
	for y in range(settings.height):
		t = (x ^ y) % settings.threads
		settings.pixels[t].append((x, y))

# Variables for global instances such as objects and chunk updates, accessed by the window and camera
objects = {}
player = None
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
		# If resolution is higher than 1, positions will be interpreted in lower steps so less data is used to represent a greater area
		self.packed = settings["packed"] if "packed" in settings else False
		self.resolution = settings["resolution"] if "resolution" in settings else 1

		# data3 stores a single material at a precise position and is indexed by (x, y, z)
		# data6 stores a cubic area filled with a material and is indexed by (x_min, y_min, z_min, x_max, y_max, z_max)
		self.data3 = {}
		self.data6 = {}

	# Clear all voxels from the frame
	def clear(self):
		self.data3 = {}
		self.data6 = {}

	# Mix the voxels of another frame into this frame
	def mix(self, other, force: bool):
		voxels = other.get_voxels()
		self.set_voxels(voxels, force)

	# Get all voxels from the frame
	def get_voxels(self):
		voxels = {}
		for post3, mat in self.data3.items():
			for x in range(post3[0] * self.resolution, post3[0] * self.resolution + self.resolution):
				for y in range(post3[1] * self.resolution, post3[1] * self.resolution + self.resolution):
					for z in range(post3[2] * self.resolution, post3[2] * self.resolution + self.resolution):
						post = x, y, z
						voxels[post] = mat
		for post6, mat in self.data6.items():
			for x in range(post6[0] * self.resolution, post6[3] * self.resolution + self.resolution):
				for y in range(post6[1] * self.resolution, post6[4] * self.resolution + self.resolution):
					for z in range(post6[2] * self.resolution, post6[5] * self.resolution + self.resolution):
						post = x, y, z
						voxels[post] = mat
		return voxels

	# Get the voxel at this position from the frame, attempt to fetch by index from data3 followed by scanning data6 if not found
	def get_voxel(self, pos: vec3):
		pos = pos // self.resolution if self.resolution > 1 else pos
		post3 = pos.tuple()
		if post3 in self.data3:
			return self.data3[post3]
		else:
			for post6, mat in self.data6.items():
				if pos.x >= post6[0] and pos.x <= post6[3] and pos.y >= post6[1] and pos.y <= post6[4] and pos.z >= post6[2] and pos.z <= post6[5]:
					return mat
		return None

	# Set a voxel at this position on the frame
	# Unpack the affected area since its content will be changed, ignore positions that aren't valid at the frame's LOD
	def set_voxel(self, pos: vec3, mat: Material, force: bool):
		if self.resolution <= 1 or (not pos.x % self.resolution and not pos.y % self.resolution and not pos.z % self.resolution):
			pos = pos // self.resolution if self.resolution > 1 else pos
			if force or not self.get_voxel(pos):
				post3 = pos.tuple()
				self.unpack(pos)
				if mat:
					self.data3[post3] = mat
				else:
					del self.data3[post3]
				self.pack()

	# Set a list of voxels provided in the same format as data3
	# Unpack the affected area since its content will be changed, ignore positions that aren't valid at the frame's LOD
	def set_voxels(self, voxels: dict, force: bool):
		for post, mat in voxels.items():
			if self.resolution <= 1 or (not post[0] % self.resolution and not post[1] % self.resolution and not post[2] % self.resolution):
				pos = vec3(post[0], post[1], post[2])
				if force or not self.get_voxel(pos):
					pos = pos // self.resolution if self.resolution > 1 else pos
					post3 = pos.tuple()
					self.unpack(pos)
					if mat:
						self.data3[post3] = mat
					else:
						del self.data3[post3]
		self.pack()

	# Decompress boxes in data6 to points in data3, position determines which box was touched and needs to be unpacked
	def unpack(self, pos: vec3):
		for post6, mat in dict(self.data6).items():
			if pos.x >= post6[0] and pos.x <= post6[3] and pos.y >= post6[1] and pos.y <= post6[4] and pos.z >= post6[2] and pos.z <= post6[5]:
				for x in range(post6[0], post6[3] + 1):
					for y in range(post6[1], post6[4] + 1):
						for z in range(post6[2], post6[5] + 1):
							post3 = x, y, z
							self.data3[post3] = mat
				del self.data6[post6]
				break

	# Compress points in data3 to boxes in data6
	# Search size increases by one unit on each axis as long as voxels of the same material fill each slice being checked
	# Start scanning from the first valid voxel found, the search area expands from a line to a plane to a cube in order -X, +X, -Y, +Y, -Z, +Z
	def pack(self):
		pack = self.packed
		while pack:
			pack = False
			for post3, mat in self.data3.items():
				pos_min = pos_max = vec3(post3[0], post3[1], post3[2])
				i = 0
				while i < 6:
					pos = post6 = None
					pos_i = i
					match pos_i:
						case 0:
							pos = vec3(-1, 0, 0)
							post6 = pos_min.x - 1, pos_min.y + 0, pos_min.z + 0, pos_min.x + 0, pos_max.y + 0, pos_max.z + 0
						case 1:
							pos = vec3(+1, 0, 0)
							post6 = pos_max.x + 0, pos_min.y + 0, pos_min.z + 0, pos_max.x + 1, pos_max.y + 0, pos_max.z + 0
						case 2:
							pos = vec3(0, -1, 0)
							post6 = pos_min.x + 0, pos_min.y - 1, pos_min.z + 0, pos_max.x + 0, pos_min.y + 0, pos_max.z + 0
						case 3:
							pos = vec3(0, +1, 0)
							post6 = pos_min.x + 0, pos_max.y + 0, pos_min.z + 0, pos_max.x + 0, pos_max.y + 1, pos_max.z + 0
						case 4:
							pos = vec3(0, 0, -1)
							post6 = pos_min.x + 0, pos_min.y + 0, pos_min.z - 1, pos_max.x + 0, pos_max.y + 0, pos_min.z + 0
						case 5:
							pos = vec3(0, 0, +1)
							post6 = pos_min.x + 0, pos_min.y + 0, pos_max.z + 0, pos_max.x + 0, pos_max.y + 0, pos_max.z + 1
					for x in range(post6[0], post6[3] + 1):
						for y in range(post6[1], post6[4] + 1):
							for z in range(post6[2], post6[5] + 1):
								post = x, y, z
								if not post in self.data3 or self.data3[post] != mat:
									i += 1
								if i != pos_i:
									break
							if i != pos_i:
								break
						if i != pos_i:
							break
					if i == pos_i:
						if pos.x < 0 or pos.y < 0 or pos.z < 0:
							pos_min += pos
						else:
							pos_max += pos

				# If an area larger than a point exists, remove single voxels from data3 and define them as boxes in data6
				# The contents of data3 will be modified and are no longer valid this turn, stop the current search and tell the main loop to run again
				if pos_min.x < pos_max.x or pos_min.y < pos_max.y or pos_min.z < pos_max.z:
					for x in range(pos_min.x, pos_max.x + 1):
						for y in range(pos_min.y, pos_max.y + 1):
							for z in range(pos_min.z, pos_max.z + 1):
								post = x, y, z
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
		self.lod = settings["lod"] if "lod" in settings else 0
		if self.size.x % 2 or self.size.y % 2 or self.size.z % 2:
			print("Warning: Sprite size " + str(self.size) + " contains a float or odd number in one or more directions, affected axes will be rounded and enlarged by one unit.")
			self.size.x = math.trunc(self.size.x) + 1 if math.trunc(self.size.x) % 2 != 0 else math.trunc(self.size.x)
			self.size.y = math.trunc(self.size.y) + 1 if math.trunc(self.size.y) % 2 != 0 else math.trunc(self.size.y)
			self.size.z = math.trunc(self.size.z) + 1 if math.trunc(self.size.z) % 2 != 0 else math.trunc(self.size.z)

		# Animation properties and the frame list used to store multiple voxel meshes representing animation frames
		self.frame = self.frame_time = self.frame_start = self.frame_end = 0
		self.frames = []
		for i in range(settings["frames"]):
			self.frames.append(Frame(packed = False, resolution = self.lod + 1))

	# Import from text file, Y and Z are flipped to match the engine's coordinate system
	def load(self, files: list, materials: dict):
		for frame in range(min(len(files), len(self.frames))):
			data = None
			match files[frame].split(".")[-1]:
				case "txt":
					data = open(files[frame], "rt")
				case "gz":
					data = gzip.open(files[frame], "rt")
			if not data:
				print("Warning: Cannot open sprite " + file + ", make sure the path and extension are correct.")
				return

			voxels = {}
			for line in data.readlines():
				params = line.strip().split(" ")
				if params[0].isdigit() and params[1].isdigit() and params[2].isdigit() and params[3] in materials:
					post = self.size.x - int(params[0]), int(params[2]), int(params[1])
					voxels[post] = materials[params[3]]
			self.get_frame(frame).set_voxels(voxels, True)

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
	def mix(self, other, force: bool):
		if self.size.x != other.size.x or self.size.y != other.size.y or self.size.z != other.size.z:
			print("Warning: Can't mix sprites of uneven size, " + str(self.size) + " and " + str(other.size) + " are not equal.")
			return

		for f in range(min(len(self.frames), len(other.frames))):
			frame = other.frames[f]
			for post, mat in frame.get_voxels().items():
				if mat:
					pos = vec3(post[0], post[1], post[2])
					self.set_voxel(f, pos, mat, force)

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

	# Get the relevant frame of the sprite, can be None to retreive the active frame instead of a specific frame
	def get_frame(self, frame):
		if isinstance(frame, int):
			return self.frames[frame]
		return self.frames[self.frame]

	# Add or remove a voxel at a single position, can be None to clear the voxel
	# Position is local to the object and starts from the minimum corner, each axis should range between 0 and self.size - 1
	# The material applied to the voxel is copied to allow modifying properties per voxel without changing the original material definition
	def set_voxel(self, frame: int, pos: vec3, mat: Material, force: bool):
		if pos.x < 0 or pos.x >= self.size.x or pos.y < 0 or pos.y >= self.size.y or pos.z < 0 or pos.z >= self.size.z:
			print("Warning: Attempted to set voxel outside of object boundaries at position " + str(pos) + ".")
			return

		self.get_frame(frame).set_voxel(pos, mat, force)

	# Set a list of voxels in which each item is a tuple of the form (position, material)
	def set_voxels(self, frame: int, voxels: list):
		for post, mat in voxels.items():
			pos = vec3(post[0], post[1], post[2])
			if pos.x < 0 or pos.x >= self.size.x or pos.y < 0 or pos.y >= self.size.y or pos.z < 0 or pos.z >= self.size.z:
				print("Warning: Attempted to set voxel list containing voxels outside of object boundaries at position " + str(pos) + ".")
				return

		self.get_frame(frame).set_voxels(voxels, force)

	# Fill the cubic area between min and max corners with the given material
	def set_voxels_area(self, frame: int, pos_min: vec3, pos_max: vec3, mat: Material, force: bool):
		if pos_min.x < 0 or pos_max.x >= self.size.x or pos_min.y < 0 or pos_max.y >= self.size.y or pos_min.z < 0 or pos_max.z >= self.size.z:
			print("Warning: Attempted to set voxel area outside of object boundaries between positions " + str(pos_min) + " and " + str(pos_max) + ".")
			return

		voxels = {}
		for x in range(math.trunc(pos_min.x), math.trunc(pos_max.x + 1)):
			for y in range(math.trunc(pos_min.y), math.trunc(pos_max.y + 1)):
				for z in range(math.trunc(pos_min.z), math.trunc(pos_max.z + 1)):
					post = x, y, z
					voxels[post] = mat
		self.get_frame(frame).set_voxels(voxels, force)

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

		self.id = random.getrandbits(64)
		self.visible = False
		self.redraw = True
		self.size = self.mins = self.maxs = vec3(0, 0, 0)
		self.weight = 0
		self.sprite = None
		self.cam_vec = vec2(0, 0)
		self.cam_pos = vec3(0, 0, 0)
		self.cam_rot = quaternion(0, 0, 0, 0)
		self.move(self.pos)
		objects[self.id] = self

	# Disable this object and remove it from the global object list
	def remove(self):
		del objects[self.id]

	# Create a copy of this object that can be edited independently
	def copy(self):
		return copy.deepcopy(self)

	# Check whether another item intersects the bounding box of this object, pos_min and pos_max represent the corners of another box or a point if identical
	def intersects(self, pos_min: vec3, pos_max: vec3):
		return pos_min <= self.maxs and pos_max >= self.mins

	# Change the virtual rotation of the object by the given amount
	def rotate(self, rot: vec3):
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
				self.redraw = True
			self.set_camera_pos()

	# Teleport the object to this origin, use only when necessary and prefer impulse instead
	def move(self, pos):
		if pos != self.pos:
			self.pos = pos
			self.mins = math.ceil(self.pos) - self.size
			self.maxs = math.floor(self.pos) + self.size
			self.redraw = True
			self.set_camera_pos()

	# Add velocity to this object, 1 is the maximum speed allowed for objects
	def accelerate(self, vel):
		self.vel += vel

	# Physics engine, applies velocity accounting for collisions with other objects and moves this object to the nearest empty space if one is available
	def update_physics(self):
		# Each iteration a move is preformed in the direction of the largest velocity step, the check continues until all velocity steps have been processed
		self_spr = self.get_sprite()
		friction = elasticity = 0
		vel_apply = self.vel
		while vel_apply != 0:
			vel_dir = math.trunc(vel_apply.normalize())
			blocked = False
			post6 = None

			# Determine the start and end corners of the slice that will be checked for collisions in order -X, +X, -Y, +Y, -Z, +Z
			if vel_dir.x < 0:
				post6 = self.mins.x - 1, self.mins.y + 0, self.mins.z + 0, self.mins.x + 0, self.maxs.y + 0, self.maxs.z + 0
			elif vel_dir.x > 0:
				post6 = self.maxs.x + 0, self.mins.y + 0, self.mins.z + 0, self.maxs.x + 1, self.maxs.y + 0, self.maxs.z + 0
			elif vel_dir.y < 0:
				post6 = self.mins.x + 0, self.mins.y - 1, self.mins.z + 0, self.maxs.x + 0, self.mins.y + 0, self.maxs.z + 0
			elif vel_dir.y > 0:
				post6 = self.mins.x + 0, self.maxs.y + 0, self.mins.z + 0, self.maxs.x + 0, self.maxs.y + 1, self.maxs.z + 0
			elif vel_dir.z < 0:
				post6 = self.mins.x + 0, self.mins.y + 0, self.mins.z - 1, self.maxs.x + 0, self.maxs.y + 0, self.mins.z + 0
			elif vel_dir.z > 0:
				post6 = self.mins.x + 0, self.mins.y + 0, self.maxs.z + 0, self.maxs.x + 0, self.maxs.y + 0, self.maxs.z + 1

			# Check all objects that intersect the slice in which self desires to move
			for obj in objects.values():
				if obj != self and obj.visible and obj.intersects(vec3(post6[0], post6[1], post6[2]), vec3(post6[3], post6[4], post6[5])):
					# If we're colliding with another physical object, transfer velocity based on weight difference and projectile speed
					if obj.physics:
						vel_transfer = vel_apply * max(0, min(1, abs(vel_apply).maxs() * self.weight - obj.weight))
						obj.vel += vel_transfer
						self.vel -= vel_transfer
						vel_apply -= vel_transfer

					# If the slice collides with any solid voxel in the object the move will no longer be preformed this call
					# The check is also used to update friction and elasticity from voxels that were touched
					obj_spr = obj.get_sprite()
					for x in range(post6[0], post6[3] + 1):
						for y in range(post6[1], post6[4] + 1):
							for z in range(post6[2], post6[5] + 1):
								pos = vec3(x, y, z)
								obj_mat = obj_spr.get_voxel(None, pos - obj.mins, obj.rot)
								if obj_mat and obj_mat.solidity > random.random():
									self_mat = self_spr.get_voxel(None, pos - self.mins - vel_dir, self.rot)
									if self_mat and self_mat.solidity > random.random():
										friction += obj_mat.friction * self_mat.friction * settings.friction
										elasticity += obj_mat.elasticity * self_mat.elasticity * settings.friction
										blocked = True

			# If the direction is valid move by at most one unit per step and decrease the amount from the velocity, if not clear all velocity in this direction since it will never collide during this check
			vel_step = vel_dir * abs(vel_apply) if blocked else vel_dir * abs(vel_apply).min(1)
			vel_apply -= vel_step
			if not blocked:
				self.move(self.pos + vel_step)

		# Apply global effects to velocity then bound it to the terminal velocity
		self.vel -= vec3(0, self.weight * settings.gravity, 0)
		self.vel -= self.vel * elasticity
		self.vel /= 1 + max(0, friction + settings.friction_air)
		self.vel = self.vel.min(+settings.max_velocity).max(-settings.max_velocity)
		if abs(self.vel.x) < settings.min_velocity:
			self.vel.x = 0
		if abs(self.vel.y) < settings.min_velocity:
			self.vel.y = 0
		if abs(self.vel.z) < settings.min_velocity:
			self.vel.z = 0

	# Update this object, called by the window every frame
	# An immediate renderer update is issued when the object changes visibility or the sprite animation advances
	def update(self, pos_cam: vec3):
		dist = self.pos.distance(pos_cam)

		# Determine object visibility based on available sprites and the object's distance to the camera
		visible_old = self.visible
		self.visible = self.sprite and dist <= settings.dist_max + self.size.maxs()
		visible_new = self.visible
		if visible_old != visible_new:
			self.redraw = True

		# Update the animation frame and calculate physics based on the new sprite, limited by the physics sleep distance setting
		if self.visible and dist <= settings.dist_move:
			spr = self.get_sprite()
			frame_old = spr.frame
			spr.anim_update()
			frame_new = spr.frame
			if frame_old != frame_new:
				self.redraw = True
				self.set_weight()

			if self.physics:
				self.update_physics()
			if self.function:
				self.function(self)

	# Set a sprite as the active sprite, None removes the sprite and disables the object
	# Set the size and bounding box of the object to that of its sprite, or a point if the sprite is disabled
	def set_sprite(self, sprite):
		self.size = self.mins = self.maxs = vec3(0, 0, 0)
		if sprite:
			self.sprite = sprite
			self.size = math.trunc(self.sprite.size / 2)
			self.mins = math.ceil(self.pos) - self.size
			self.maxs = math.floor(self.pos) + self.size
		self.redraw = True
		self.set_weight()

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

	# Update the world camera position and rotation coordinates for camera objects
	def set_camera_pos(self):
		if self.cam_vec != 0:
			self.cam_rot = self.rot.quaternion()
			d = vec3(0, self.rot.y, 0).quaternion().vec_forward()
			self.cam_pos = self.pos + vec3(self.cam_vec.x * d.x, self.cam_vec.y, self.cam_vec.x * d.z)

	# Mark that we want to attach the camera to this object at the provided position offset
	# The camera can only be attached to one object at a time, this will remove the setting from all other objects
	def set_camera(self, pos: vec2):
		self.cam_vec = pos
		self.set_camera_pos()

# Execute the init script of the loaded mod
importlib.import_module("mods." + mod + ".init")
