#!/usr/bin/python3
from lib import *

import data

def material(ray, mat):
	# Color: Use material color darkened by alpha value, mixing reduces with the number of hits as bounces lose energy
	col = mat.albedo.mix(rgb(0, 0, 0), 1 - ray.alpha)
	col_mix = 1 / (1 + ray.hits)
	ray.col = ray.col and ray.col.mix(col, col_mix) or col

	# Roughness: Velocity is randomized with the roughness value, a roughness of 1 can send the ray in almost any direction
	ray.vel += vec3(rand(mat.roughness), rand(mat.roughness), rand(mat.roughness))

	# Velocity: Estimate the normal direction of the voxel based on its neighbors, bounce the ray back for solid bounces but not translucent ones
	# Reflections may occur in one or all three axis, diagonal face normals are not supported but corner voxels may act as a 45* mirror
	if mat.translucency < random.random():
		if ray.vel.x > 0 and mat.normals[0]:
			ray.vel.x *= -1
		elif ray.vel.x < 0 and mat.normals[1]:
			ray.vel.x *= -1
		if ray.vel.y > 0 and mat.normals[2]:
			ray.vel.y *= -1
		elif ray.vel.y < 0 and mat.normals[3]:
			ray.vel.y *= -1
		if ray.vel.z > 0 and mat.normals[4]:
			ray.vel.z *= -1
		elif ray.vel.z < 0 and mat.normals[5]:
			ray.vel.z *= -1
	ray.vel = ray.vel.normalize()

	# Hits: Increase the number of hits based on material translucency
	ray.hits += 1 - mat.translucency

	return True

def world():
	# Test environment used during early engine development, contains basic materials and surfaces
	mat_red = data.Material(
		function = material,
		albedo = rgb(255, 0, 0),
		roughness = 0.1,
		translucency = 0,
		group = "solid",
	)
	mat_green = data.Material(
		function = material,
		albedo = rgb(0, 255, 0),
		roughness = 0.1,
		translucency = 0,
		group = "solid",
	)
	mat_blue = data.Material(
		function = material,
		albedo = rgb(0, 0, 255),
		roughness = 0.1,
		translucency = 0,
		group = "solid",
	)

	obj = data.Object(pos = vec3(0, 0, 0), size = vec3(16, 16, 16), active = True)
	obj.set_voxel_area(vec3(0, 0, 0), vec3(15, 15, 0), mat_red)
	obj.set_voxel_area(vec3(0, 0, 0), vec3(0, 15, 15), mat_green)
	obj.set_voxel_area(vec3(0, 15, 0), vec3(15, 15, 15), mat_blue)
