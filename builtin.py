#!/usr/bin/python3
from lib import *

import data

# Default material function, designed as a simplified PBR shader
def material(ray, mat):
	# Hits: Increase the number of hits based on material ior, glass and fog have a lower probability of terminating rays sooner
	ray.hits += mat.ior

	# Color and absorption:
	# 1: Hitting an emissive surface increases the ray's ability to absorb color, ensures lights transmit their color in reflections
	# 2: Mix the material's albedo to the ray color based on the ray's color absorption, if a ray color doesn't already exist use albedo as is
	# 3: Reduce the ray's absorption by the lack of metalicity scaled by the density of this interaction, a perfect mirror or transparent hit has no effect
	ray.absorption = min(1, ray.absorption + mat.energy)
	ray.col = ray.col and ray.col.mix(mat.albedo, ray.absorption) or mat.albedo
	ray.absorption *= 1 - mat.absorption

	# Energy:
	# 1: Cause the ray to lose energy when hitting a surface based on the roughness of the interaction
	# 2: Increase the ray's energy when hitting an emissive surface, this is what makes light shine on other surfaces
	ray.energy *= 1 - mat.roughness
	ray.energy = min(1, ray.energy + mat.energy)

	# Roughness and translucency:
	# 1: Velocity is randomized by the roughness value of the interaction, 0 is perfectly sharp while 1 can send the ray in almost any direction
	ray.vel += vec3(rand(mat.roughness), rand(mat.roughness), rand(mat.roughness))

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
		roughness = 0.1,
		absorption = 1,
		ior = 1,
		energy = 0,
		solid = True,
	)
	mat_opaque_green = data.Material(
		function = material,
		albedo = rgb(0, 255, 0),
		roughness = 0.1,
		absorption = 1,
		ior = 1,
		energy = 0,
		solid = True,
	)
	mat_opaque_blue = data.Material(
		function = material,
		albedo = rgb(0, 0, 255),
		roughness = 0.1,
		absorption = 1,
		ior = 1,
		energy = 0,
		solid = True,
	)
	mat_rough_white = data.Material(
		function = material,
		albedo = rgb(255, 255, 255),
		roughness = 0.5,
		absorption = 1,
		ior = 1,
		energy = 0,
		solid = True,
	)
	mat_translucent = data.Material(
		function = material,
		albedo = rgb(0, 255, 255),
		roughness = 0,
		absorption = 0.25,
		ior = 0.25,
		energy = 0,
		solid = True,
	)
	mat_light = data.Material(
		function = material,
		albedo = rgb(255, 0, 255),
		roughness = 0,
		absorption = 1,
		ior = 1,
		energy = 0.25,
		solid = True,
	)

	spr = data.Sprite(size = vec3(16, 16, 16), frames = 1)
	spr.set_voxel_area(0, vec3(0, 0, 0), vec3(15, 15, 0), mat_opaque_red)
	spr.set_voxel_area(0, vec3(0, 0, 0), vec3(0, 15, 15), mat_opaque_green)
	spr.set_voxel_area(0, vec3(0, 15, 0), vec3(15, 15, 15), mat_opaque_blue)
	spr.set_voxel_area(0, vec3(10, 10, 4), vec3(14, 14, 8), mat_translucent)
	spr.set_voxel_area(0, vec3(4, 10, 10), vec3(8, 14, 14), mat_light)
	obj = data.Object(pos = vec3(0, 0, 0), rot = vec3(0, 0, 0), vel = vec3(0, 0, 0), actor = False)
	obj.set_sprite(spr)

	spr_player = data.Sprite(size = vec3(2, 4, 2), frames = 1)
	spr_player.set_voxel_area(0, vec3(0, 0, 0), vec3(1, 3, 1), mat_rough_white)
	obj_player = data.Object(pos = vec3(0, -2, 0), rot = vec3(0, 0, 0), vel = vec3(0, 0, 0), actor = True)
	obj_player.set_sprite(spr_player)
	obj_player.set_camera(vec2(2, 4))

	data.background = material_sky
