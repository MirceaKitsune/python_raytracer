#!/usr/bin/python3
from lib import *

import random

# Default material function, mods can provide materials that use their own functions if desired
def material_default(ray, mat):
	# Color: Use material color darkened by alpha value, mixing reduces with the number of hits
	col = mat.albedo.mix(rgb(0, 0, 0), 1 - ray.alpha)
	col_mix = 1 / ray.hits
	ray.col = ray.col and ray.col.mix(col, 1 / ray.hits) or col

	# Velocity: Estimate the normal direction of the voxel based on its neighbors, bounce the ray back for solid bounces but not translucent ones
	# Reflections may occur in one or all three axis, diagonal face normals are not supported but corner voxels may act as a 45* mirror
	if mat.translucency < random.random():
		if ray.vel.x > 0 and (not ray.neighbors[0] or ray.neighbors[0].translucency > random.random()):
			ray.vel.x *= -1
		elif ray.vel.x < 0 and (not ray.neighbors[1] or ray.neighbors[1].translucency > random.random()):
			ray.vel.x *= -1
		if ray.vel.y > 0 and (not ray.neighbors[2] or ray.neighbors[2].translucency > random.random()):
			ray.vel.y *= -1
		elif ray.vel.y < 0 and (not ray.neighbors[3] or ray.neighbors[3].translucency > random.random()):
			ray.vel.y *= -1
		if ray.vel.z > 0 and (not ray.neighbors[4] or ray.neighbors[4].translucency > random.random()):
			ray.vel.z *= -1
		elif ray.vel.z < 0 and (not ray.neighbors[5] or ray.neighbors[5].translucency > random.random()):
			ray.vel.z *= -1
	ray.vel += vec3(rand(mat.roughness), rand(mat.roughness), rand(mat.roughness))
	ray.vel.normalize()

class Material:
	def __init__(self, func: callable, **settings):
		self.function = func or material_default
		for s in settings:
			setattr(self, s, settings[s])

class Object:
	def __init__(self, **settings):
		# Origin is always at the center of the object, mins and maxs are updated when moving the object to avoid costly checks during ray tracing
		self.origin = settings["origin"] or vec3(0, 0, 0)
		self.size = settings["size"] or vec3(0, 0, 0)
		self.active = settings["active"] or False
		self.mins = vec3(0, 0, 0)
		self.maxs = vec3(0, 0, 0)
		self.move(self.origin)

		# Voxels are stored in a list within each set, sets can represent different sprites or animation frames
		# The material list is ordered, 3D position is converted from the index to know which position a voxel refers to
		self.sprites = {}
		self.sprite_default = "default"
		self.sprite_active = self.sprite_default
		self.set_sprite(self.sprite_default, None)

	# Check whether a point position is inside the bounding box of this object
	def intersects(self, pos: vec3):
		if pos.x <= self.maxs.x and pos.x > self.mins.x:
			if pos.y <= self.maxs.y and pos.y > self.mins.y:
				if pos.z <= self.maxs.z and pos.z > self.mins.z:
					return True
		return False

	# Check whether another box intersects the bounding box of this object, pos_min and pos_max represent the corners of the other box
	def intersects_box(self, pos_min: vec3, pos_max: vec3):
		if pos_min.x <= self.maxs.x and pos_max.x > self.mins.x:
			if pos_min.y <= self.maxs.y and pos_max.y > self.mins.y:
				if pos_min.z <= self.maxs.z and pos_max.z > self.mins.z:
					return True
		return False

	# Returns position relative to the minimum corner, add range 0 to self.size to get a particular voxel
	def pos_rel(self, pos: vec3):
		return vec3(self.maxs.x - pos.x, self.maxs.y - pos.y, self.maxs.z - pos.z)

	# Moves this object to a new origin, update mins and maxs to represent the bounding box in space
	def move(self, pos):
		self.origin = pos.round()
		size_x = round(self.size.x / 2)
		size_y = round(self.size.y / 2)
		size_z = round(self.size.z / 2)
		self.mins = vec3(self.origin.x - size_x, self.origin.y - size_y, self.origin.z - size_z)
		self.maxs = vec3(self.origin.x + size_x, self.origin.y + size_y, self.origin.z + size_z)

	# Set the given sprite as the voxel sprite to be displayed
	def use_sprite(self, sprite: str):
		if sprite in self.sprites:
			self.sprite_active = sprite

	# Remove a sprite from the sprite list, switch to the default sprite if this was the active sprite
	def del_sprite(self, sprite: str):
		if sprite in self.sprites:
			if self.sprite_active == sprite:
				self.sprite_active = self.sprite_default
			del self.sprites[sprite]

	# Create or redefine a sprite filled with the given material, can be None to initialize an empty sprite
	def set_sprite(self, sprite: str, mat: Material):
		if not sprite in self.sprites:
			self.sprites[sprite] = []
		for i in range(0, self.size.x * self.size.y * self.size.z):
			self.sprites[sprite].append(mat)

	# Get the voxel at this position, returns the material or None if empty
	# Position is in local space, always convert the position with pos_rel before calling this
	# If a sprite isn't specified, the voxel of the active sprite is returned
	def get_voxel(self, sprite: str, pos: vec3):
		spr = sprite or self.sprite_active or self.sprite_default
		if spr in self.sprites:
			i = vec3_index(pos, self.size.x, self.size.y)
			if i < len(self.sprites[spr]):
				return self.sprites[spr][i]
		return None

	# Add or remove a voxel at a single position in a sprite, can be None to clear the voxel
	# Position is local to the object and starts from the minimum corner, each axis should range between 0 and self.size - 1
	def set_voxel(self, sprite: str, pos: vec3, mat: Material):
		if pos.x < 0 or pos.x >= self.size.x or pos.y < 0 or pos.y >= self.size.y or pos.z < 0 or pos.z >= self.size.z:
			print("Warning: Attempted to set voxel outside of object boundaries at position " + pos.string() + ".")
			return

		spr = sprite or self.sprite_active or self.sprite_default
		if spr in self.sprites:
			i = vec3_index(pos, self.size.x, self.size.y)
			if i < len(self.sprites[spr]):
				self.sprites[spr][i] = mat

	# Same as set_voxel but modifies voxels in a cubic area instead of a point
	def set_voxel_area(self, sprite: str, pos_min: vec3, pos_max: vec3, mat: Material):
		spr = sprite or self.sprite_active or self.sprite_default
		for x in range(int(pos_min.x), int(pos_max.x + 1)):
			for y in range(int(pos_min.y), int(pos_max.y + 1)):
				for z in range(int(pos_min.z), int(pos_max.z + 1)):
					self.set_voxel(spr, vec3(x, y, z), mat)
