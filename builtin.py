#!/usr/bin/python3
from lib import *

import data

# Default material function, designed as a simplified PBR shader
def material(ray, mat):
	# Hits: Increase the number of hits based on material density, glass and fog have a lower probability of terminating rays sooner
	ray.hits += mat.density

	# Color and absorption:
	# 1: Hitting an emissive surface increases the ray's ability to absorb color, ensures lights transmit their color in reflections
	# 2: Mix the material's albedo to the ray color based on the ray's color absorption, if a ray color doesn't already exist use albedo as is
	# 3: Reduce the ray's absorption by the lack of metalicity scaled by the density of this interaction, a perfect mirror or transparent hit has no effect
	ray.absorption = min(1, ray.absorption + mat.energy)
	ray.col = ray.col and ray.col.mix(mat.albedo, ray.absorption) or mat.albedo
	ray.absorption *= mix(1, mat.metalicity, mat.density)

	# Energy:
	# 1: Cause the ray to lose energy when hitting a surface based on the roughness of the interaction
	# 2: Increase the ray's energy when hitting an emissive surface, this is what makes light shine on other surfaces
	ray.energy *= 1 - mat.roughness
	ray.energy = min(1, ray.energy + mat.energy)

	# Roughness and translucency:
	# 1: Velocity is randomized by the roughness value of the interaction, 0 is perfectly sharp while 1 can send the ray in almost any direction
	# 2: Flip the appropriate axes in the ray velocity based on the normals of the voxel, the flipped velocity is then blended to the old velocity based on ior
	# 3: Normalize ray velocity after making changes, this ensures the speed of light remains 1 and future voxels aren't skipped or calculated twice
	# Note: Reflections may occur in one or all three axis, diagonal normals aren't supported but corner voxels can mirror rays in multiple directions
	ray.vel += vec3(rand(mat.roughness), rand(mat.roughness), rand(mat.roughness))
	if mat.ior:
		vel = vec3(ray.vel.x, ray.vel.y, ray.vel.z)
		if vel.x > 0 and mat.normals[0]:
			vel.x *= -1
		elif vel.x < 0 and mat.normals[1]:
			vel.x *= -1
		if vel.y > 0 and mat.normals[2]:
			vel.y *= -1
		elif vel.y < 0 and mat.normals[3]:
			vel.y *= -1
		if vel.z > 0 and mat.normals[4]:
			vel.z *= -1
		elif vel.z < 0 and mat.normals[5]:
			vel.z *= -1
		ray.vel = ray.vel.mix(vel, mat.ior)
	ray.vel = ray.vel.normalize()

# Default background function, generates a simple sky
def material_sky(ray):
	col = rgb(127, 127 + max(0, +ray.vel.y) * 64, 127 + max(0, +ray.vel.y) * 128)
	ray.col = ray.col and ray.col.mix(col, ray.absorption) or col
	ray.energy = min(1, ray.energy + (0.25 + max(0, +ray.vel.y) * 0.25))

# Test environment used during early engine development, contains basic materials and surfaces
def world():
	mat_opaque_red = data.Material(
		function = material,
		albedo = rgb(255, 0, 0),
		metalicity = 0,
		roughness = 0.1,
		ior = 1,
		density = 1,
		energy = 0,
		group = "solid",
	)
	mat_opaque_green = data.Material(
		function = material,
		albedo = rgb(0, 255, 0),
		metalicity = 0,
		roughness = 0.1,
		ior = 1,
		density = 1,
		energy = 0,
		group = "solid",
	)
	mat_opaque_blue = data.Material(
		function = material,
		albedo = rgb(0, 0, 255),
		metalicity = 0,
		roughness = 0.1,
		ior = 1,
		density = 1,
		energy = 0,
		group = "solid",
	)
	mat_translucent = data.Material(
		function = material,
		albedo = rgb(0, 255, 255),
		metalicity = 0,
		roughness = 0,
		ior = 0.25,
		density = 0.25,
		energy = 0,
		group = "glass",
	)
	mat_light = data.Material(
		function = material,
		albedo = rgb(255, 0, 255),
		metalicity = 0,
		roughness = 0,
		ior = 1,
		density = 1,
		energy = 0.25,
		group = "glass",
	)

	spr = data.Sprite(size = vec3(16, 16, 16))
	spr.set_voxel_area(vec3(0, 0, 0), vec3(15, 15, 0), mat_opaque_red)
	spr.set_voxel_area(vec3(0, 0, 0), vec3(0, 15, 15), mat_opaque_green)
	spr.set_voxel_area(vec3(0, 15, 0), vec3(15, 15, 15), mat_opaque_blue)
	spr.set_voxel_area(vec3(10, 10, 4), vec3(14, 14, 8), mat_translucent)
	spr.set_voxel_area(vec3(4, 10, 10), vec3(8, 14, 14), mat_light)

	obj = data.Object(pos = vec3(0, 0, 0))
	obj.set_sprite("default", spr)
	obj.activate_sprite("default")
