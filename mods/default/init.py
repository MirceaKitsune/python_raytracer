#!/usr/bin/python3
from lib import *

import data

mat_stone = data.Material(
	function = material,
	albedo = rgb(127, 127, 127),
	roughness = 0.5,
	absorption = 1.5,
	ior = 1,
	energy = 0,
	solidity = 1,
	weight = 0.00125,
	friction = 0.25,
	elasticity = 0,
)

mat_stone_marble = data.Material(
	function = material,
	albedo = rgb(255, 255, 255),
	roughness = 0,
	absorption = 1,
	ior = 1,
	energy = 0,
	solidity = 1,
	weight = 0.00125,
	friction = 0.1,
	elasticity = 0,
)

mat_stone_light = data.Material(
	function = material,
	albedo = rgb(191, 191, 191),
	roughness = 0.5,
	absorption = 1,
	ior = 1,
	energy = 0,
	solidity = 1,
	weight = 0.00125,
	friction = 0.25,
	elasticity = 0,
)

mat_stone_dark = data.Material(
	function = material,
	albedo = rgb(63, 63, 63),
	roughness = 0.5,
	absorption = 2,
	ior = 1,
	energy = 0,
	solidity = 1,
	weight = 0.00125,
	friction = 0.25,
	elasticity = 0,
)

mat_metal = data.Material(
	function = material,
	albedo = rgb(0, 0, 0),
	roughness = 0.1,
	absorption = 1,
	ior = 1,
	energy = 0,
	solidity = 1,
	weight = 0.00125,
	friction = 0.25,
	elasticity = 0,
)

mat_player = data.Material(
	function = material,
	albedo = rgb(0, 0, 0),
	roughness = 0.9,
	absorption = 1,
	ior = 1,
	energy = 0,
	solidity = 1,
	weight = 0.0025,
	friction = 0.25,
	elasticity = 0.5,
)

# World object, contains a glass cube and two lights
spr = data.Sprite(size = vec3(128, 64, 128), frames = 1, lod = 1)
spr.from_text(["mods/default/voxels/world.txt"], {"7f7f7f": mat_stone, "ffffff": mat_stone_marble, "bfbfbf": mat_stone_light, "3f3f3f": mat_stone_dark, "000000": mat_metal})
obj = data.Object(pos = vec3(0, 0, 0), rot = vec3(0, 0, 0), vel = vec3(0, 0, 0), physics = False)
obj.set_sprite(spr)

# Player object
spr_player = data.Sprite(size = vec3(12, 16, 12), frames = 1, lod = 1)
spr_player.set_voxels_area(0, vec3(0, 0, 0), vec3(11, 15, 11), mat_player, True)
obj_player = data.Object(pos = vec3(-12, 0, -8), rot = vec3(0, 0, 0), vel = vec3(0, 0, 0), physics = True)
obj_player.set_sprite(spr_player)
obj_player.set_camera(vec2(12, 4))

data.player = obj_player
data.background = material_background
