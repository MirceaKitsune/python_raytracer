#!/usr/bin/python3
from lib import *

import data

mat_stone_marble = data.Material(
	function = material,
	albedo = rgb(255, 255, 255),
	roughness = 0,
	absorption = 1,
	ior = 1,
	energy = 0,
	solidity = 1,
	weight = 0.0025,
	friction = 0.125,
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
	weight = 0.0025,
	friction = 0.25,
	elasticity = 0,
)

mat_stone_gray = data.Material(
	function = material,
	albedo = rgb(127, 127, 127),
	roughness = 0.5,
	absorption = 1.5,
	ior = 1,
	energy = 0,
	solidity = 1,
	weight = 0.0025,
	friction = 0.375,
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
	weight = 0.0025,
	friction = 0.5,
	elasticity = 0,
)

mat_metal = data.Material(
	function = material,
	albedo = rgb(0, 0, 0),
	roughness = 0.1,
	absorption = 0.5,
	ior = 1,
	energy = 0,
	solidity = 1,
	weight = 0.0025,
	friction = 0.125,
	elasticity = 0,
)

mat_material = data.Material(
	function = material,
	albedo = rgb(127, 127, 127),
	roughness = 0.25,
	absorption = 1,
	ior = 1,
	energy = 0,
	solidity = 1,
	weight = 0.0005,
	friction = 0.5,
	elasticity = 0,
)

mat_material_rough = data.Material(
	function = material,
	albedo = rgb(255, 0, 0),
	roughness = 0.5,
	absorption = 1,
	ior = 1,
	energy = 0,
	solidity = 1,
	weight = 0.0005,
	friction = 1,
	elasticity = 0.25,
)

mat_material_light = data.Material(
	function = material,
	albedo = rgb(255, 255, 0),
	roughness = 0.5,
	absorption = 1,
	ior = 1,
	energy = 2,
	solidity = 1,
	weight = 0.00025,
	friction = 0.5,
	elasticity = 0.25,
)

mat_material_scatter = data.Material(
	function = material,
	albedo = rgb(0, 255, 0),
	roughness = 0.25,
	absorption = 0.5,
	ior = 0.5,
	energy = 0,
	solidity = 1,
	weight = 0.0005,
	friction = 1,
	elasticity = 0.5,
)

mat_material_glass = data.Material(
	function = material,
	albedo = rgb(0, 255, 255),
	roughness = 0,
	absorption = 0.25,
	ior = 0.25,
	energy = 0,
	solidity = 1,
	weight = 0.00125,
	friction = 0,
	elasticity = 0,
)

mat_material_shiny = data.Material(
	function = material,
	albedo = rgb(0, 0, 255),
	roughness = 0,
	absorption = 1,
	ior = 1,
	energy = 0,
	solidity = 1,
	weight = 0.00125,
	friction = 0.25,
	elasticity = 0,
)

mat_material_mist = data.Material(
	function = material,
	albedo = rgb(255, 0, 255),
	roughness = 0,
	absorption = 0.25,
	ior = 0,
	energy = 0,
	solidity = 1,
	weight = 0.00025,
	friction = 0,
	elasticity = 1,
)

mat_player = data.Material(
	function = material,
	albedo = rgb(127, 127, 127),
	roughness = 0.5,
	absorption = 1,
	ior = 1,
	energy = 0,
	solidity = 1,
	weight = 0.0005,
	friction = 0.1,
	elasticity = 0.5,
)

castle_spr = data.Sprite(size = vec3(128, 64, 128), frames = 1, lod = 0)
castle_spr.load(["mods/default/voxels/castle.txt.gz"], {"000000": mat_metal, "3f3f3f": mat_stone_dark, "7f7f7f": mat_stone_gray, "bfbfbf": mat_stone_light, "ffffff": mat_stone_marble})
castle_obj = data.Object(pos = vec3(0, 0, 0), rot = vec3(0, 0, 0), vel = vec3(0, 0, 0), physics = False)
castle_obj.set_sprite(castle_spr)

material_rough_spr = data.Sprite(size = vec3(12, 12, 12), frames = 1, lod = 0)
material_rough_spr.load(["mods/default/voxels/material.txt.gz"], {"7f7f7f": mat_material, "ffffff": mat_material_rough})
material_rough_obj = data.Object(pos = vec3(-56, -16, 56), rot = vec3(0, 0, 0), vel = vec3(0, 0, 0), physics = True)
material_rough_obj.set_sprite(material_rough_spr)

material_light_spr = data.Sprite(size = vec3(12, 12, 12), frames = 1, lod = 0)
material_light_spr.load(["mods/default/voxels/material.txt.gz"], {"7f7f7f": mat_material, "ffffff": mat_material_light})
material_light_obj = data.Object(pos = vec3(12, -24, 24), rot = vec3(0, 0, 0), vel = vec3(0, 0, 0), physics = True)
material_light_obj.set_sprite(material_light_spr)

material_scatter_spr = data.Sprite(size = vec3(12, 12, 12), frames = 1, lod = 0)
material_scatter_spr.load(["mods/default/voxels/material.txt.gz"], {"7f7f7f": mat_material, "ffffff": mat_material_scatter})
material_scatter_obj = data.Object(pos = vec3(48, -24, -48), rot = vec3(0, 0, 0), vel = vec3(0, 0, 0), physics = True)
material_scatter_obj.set_sprite(material_scatter_spr)

material_glass_spr = data.Sprite(size = vec3(12, 12, 12), frames = 1, lod = 0)
material_glass_spr.load(["mods/default/voxels/material.txt.gz"], {"7f7f7f": mat_material, "ffffff": mat_material_glass})
material_glass_obj = data.Object(pos = vec3(-4, 18, 16), rot = vec3(0, 0, 0), vel = vec3(0, 0, 0), physics = True)
material_glass_obj.set_sprite(material_glass_spr)

material_shiny_spr = data.Sprite(size = vec3(12, 12, 12), frames = 1, lod = 0)
material_shiny_spr.load(["mods/default/voxels/material.txt.gz"], {"7f7f7f": mat_material, "ffffff": mat_material_shiny})
material_shiny_obj = data.Object(pos = vec3(-56, 18, 16), rot = vec3(0, 0, 0), vel = vec3(0, 0, 0), physics = True)
material_shiny_obj.set_sprite(material_shiny_spr)

material_mist_spr = data.Sprite(size = vec3(12, 12, 12), frames = 1, lod = 0)
material_mist_spr.load(["mods/default/voxels/material.txt.gz"], {"7f7f7f": mat_material, "ffffff": mat_material_mist})
material_mist_obj = data.Object(pos = vec3(-36, 18, -36), rot = vec3(0, 0, 0), vel = vec3(0, 0, 0), physics = True)
material_mist_obj.set_sprite(material_mist_spr)

player_spr = data.Sprite(size = vec3(12, 16, 12), frames = 1, lod = 0)
player_spr.load(["mods/default/voxels/player.txt.gz"], {"7f7f7f": mat_player})
player_obj = data.Object(pos = vec3(-12, 0, -8), rot = vec3(0, 0, 0), vel = vec3(0, 0, 0), physics = True)
player_obj.set_sprite(player_spr)
player_obj.set_camera(vec2(12, 4))

data.player = player_obj
data.background = material_background
