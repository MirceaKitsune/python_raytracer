#!/usr/bin/python3
from lib import *

import data

# Default material function, designed as a simplified PBR shader
def material(ray, mat):
	# Color: Apply the material color, mixing reduces with the number of hits as bounces lose energy
	if not ray.col:
		ray.col = mat.albedo
	elif ray.absorption:
		ray.col = ray.col.mix(mat.albedo, ray.absorption)
	ray.absorption *= (1 - mat.density) + (mat.metalicity / (1 + ray.hits)) * mat.density

	# Energy: Cause the ray to lose energy when hitting a surface that absorbs light, determined by metalicity
	# Increase energy when hitting an emissive surface
	ray.energy /= 2 - mat.metalicity
	ray.energy = min(1, ray.energy + mat.energy)

	# Roughness: Velocity is randomized with the roughness value, a roughness of 1 can send the ray in almost any direction
	# Translucency: Estimate the normal direction of the voxel based on its neighbors, bounce the ray back based on the amount of transparency
	# Reflections may occur in one or all three axis, diagonal face normals are not supported but corner voxels may act as a 45* mirror
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

	# Hits: Increase the number of hits based on material density
	ray.hits += mat.density

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
		albedo = rgb(255, 255, 255),
		metalicity = 0,
		roughness = 0,
		ior = 0.25,
		density = 0.1,
		energy = 0,
		group = "glass",
	)
	mat_light = data.Material(
		function = material,
		albedo = rgb(255, 255, 255),
		metalicity = 0,
		roughness = 0,
		ior = 1,
		density = 1,
		energy = 1,
		group = "glass",
	)

	obj = data.Object(pos = vec3(0, 0, 0), size = vec3(16, 16, 16), active = True)
	obj.set_voxel_area(vec3(0, 0, 0), vec3(15, 15, 0), mat_opaque_red)
	obj.set_voxel_area(vec3(0, 0, 0), vec3(0, 15, 15), mat_opaque_green)
	obj.set_voxel_area(vec3(0, 15, 0), vec3(15, 15, 15), mat_opaque_blue)
	obj.set_voxel_area(vec3(10, 10, 4), vec3(14, 14, 8), mat_translucent)
	obj.set_voxel_area(vec3(4, 10, 10), vec3(8, 14, 14), mat_light)
