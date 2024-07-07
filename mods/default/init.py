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

mat_light_gold = data.Material(
	function = material,
	albedo = rgb(255, 255, 0),
	roughness = 0,
	absorption = 1,
	ior = 1,
	energy = 2.5,
	solidity = 1,
	weight = 0,
	friction = 0.25,
	elasticity = 0.5,
)

mat_light_pink = data.Material(
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

mat_glass_cyan = data.Material(
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

mat_item_player = data.Material(
	function = material,
	albedo = rgb(0, 0, 0),
	roughness = 0.9,
	absorption = 1,
	ior = 1,
	energy = 0,
	solidity = 1,
	weight = 0.0125,
	friction = 0.25,
	elasticity = 0.5,
)

mat_item_box = data.Material(
	function = material,
	albedo = rgb(255, 255, 255),
	roughness = 0.9,
	absorption = 1,
	ior = 1,
	energy = 0,
	solidity = 1,
	weight = 0.00125,
	friction = 0.25,
	elasticity = 0,
)

# World object, contains a glass cube and two lights
spr = data.Sprite(size = vec3(64, 64, 64), frames = 1, lod = 1)
spr.set_voxels_area(0, vec3(0, 0, 0), vec3(0, 63, 63), mat_opaque_red)
spr.set_voxels_area(0, vec3(0, 0, 0), vec3(63, 63, 0), mat_opaque_green)
spr.set_voxels_area(0, vec3(0, 0, 0), vec3(63, 0, 63), mat_opaque_blue)
spr.set_voxels_area(0, vec3(3, 1, 9), vec3(7, 5, 13), mat_light_gold)
spr.set_voxels_area(0, vec3(9, 1, 3), vec3(13, 5, 7), mat_light_pink)
spr.set_voxels_area(0, vec3(9, 1, 9), vec3(13, 5, 13), mat_glass_cyan)
obj = data.Object(pos = vec3(0, 0, 0), rot = vec3(0, 0, 0), vel = vec3(0, 0, 0), physics = False)
obj.set_sprite(spr)

# Player object
spr_player = data.Sprite(size = vec3(2, 4, 2), frames = 1, lod = 1)
spr_player.set_voxels_area(0, vec3(0, 0, 0), vec3(1, 3, 1), mat_item_player)
obj_player = data.Object(pos = vec3(0, -8, 0), rot = vec3(0, 0, 0), vel = vec3(0, 0, 0), physics = True)
obj_player.set_sprite(spr_player)
obj_player.set_camera(vec2(2, 4))

# Box object, can be moved and blinks every second
mat_item_box_lit = mat_item_box.copy()
mat_item_box_lit.energy = 2.5
spr_box = data.Sprite(size = vec3(4, 4, 4), frames = 2, lod = 1)
spr_box.set_voxels_area(0, vec3(0, 0, 0), vec3(3, 3, 3), mat_item_box)
spr_box.set_voxels_area(1, vec3(0, 0, 0), vec3(3, 3, 3), mat_item_box_lit)
spr_box.anim_set(0, 1, 1)
obj_box = data.Object(pos = vec3(-8, -8, -8), rot = vec3(0, 0, 0), vel = vec3(0, 0, 0), physics = True)
obj_box.set_sprite(spr_box)

data.player = obj_player
data.background = material_background
