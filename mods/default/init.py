#!/usr/bin/python3
from lib import *

import data

mat_opaque_red = data.Material(
	function = material,
	albedo = rgb(255, 0, 0),
	roughness = 0.1,
	absorption = 1,
	ior = 1,
	energy = 0,
	solidity = 1,
	weight = 0,
	friction = 0.25,
	elasticity = 0,
)

mat_opaque_green = data.Material(
	function = material,
	albedo = rgb(0, 255, 0),
	roughness = 0.1,
	absorption = 1,
	ior = 1,
	energy = 0,
	solidity = 1,
	weight = 0,
	friction = 0.25,
	elasticity = 0,
)

mat_opaque_blue = data.Material(
	function = material,
	albedo = rgb(0, 0, 255),
	roughness = 0.1,
	absorption = 1,
	ior = 1,
	energy = 0,
	solidity = 1,
	weight = 0,
	friction = 0.25,
	elasticity = 0,
)

mat_rough_white = data.Material(
	function = material,
	albedo = rgb(255, 255, 255),
	roughness = 0.5,
	absorption = 1,
	ior = 1,
	energy = 0,
	solidity = 1,
	weight = 0.0125,
	friction = 0.25,
	elasticity = 0.5,
)

mat_translucent = data.Material(
	function = material,
	albedo = rgb(0, 255, 255),
	roughness = 0,
	absorption = 0.25,
	ior = 0.25,
	energy = 0,
	solidity = 1,
	weight = 0,
	friction = 0,
	elasticity = 0,
)

mat_light = data.Material(
	function = material,
	albedo = rgb(255, 0, 255),
	roughness = 0,
	absorption = 1,
	ior = 1,
	energy = 2.5,
	solidity = 1,
	weight = 0,
	friction = 0.25,
	elasticity = 0.5,
)

spr = data.Sprite(size = vec3(64, 64, 64), frames = 1, lod = 1)
spr.set_voxels_area(0, vec3(0, 0, 0), vec3(63, 63, 0), mat_opaque_red)
spr.set_voxels_area(0, vec3(0, 0, 0), vec3(0, 63, 63), mat_opaque_green)
spr.set_voxels_area(0, vec3(0, 0, 0), vec3(63, 0, 63), mat_opaque_blue)
spr.set_voxels_area(0, vec3(9, 1, 3), vec3(13, 5, 7), mat_translucent)
spr.set_voxels_area(0, vec3(3, 1, 9), vec3(7, 5, 13), mat_light)
obj = data.Object(pos = vec3(0, 0, 0), rot = vec3(0, 0, 0), vel = vec3(0, 0, 0), physics = False)
obj.set_sprite(spr)

spr_player = data.Sprite(size = vec3(2, 4, 2), frames = 1, lod = 1)
spr_player.set_voxels_area(0, vec3(0, 0, 0), vec3(1, 3, 1), mat_rough_white)
obj_player = data.Object(pos = vec3(0, -8, 0), rot = vec3(0, 0, 0), vel = vec3(0, 0, 0), physics = True)
obj_player.set_sprite(spr_player)
obj_player.set_camera(vec2(2, 4))

data.background = material_background
