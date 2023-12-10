#!/usr/bin/python3
import math
import random

# Store: Generic data storage, similar to the Python dictionary but allows getting and setting properties with dots (eg: data.prop instead of data["prop"])
class store:
	def __init__(self, **args):
		for a in args:
			setattr(self, a, args[a])

# Vector2: A 2D vector containing X, Y directions, typically used for pixel positions in screen
class vec2:
	def __init__(self, x: float, y: float):
		self.x = x
		self.y = y
	def __add__(self, other):
		return vec2(self.x + other.x, self.y + other.y)
	def __sub__(self, other):
		return vec2(self.x - other.x, self.y - other.y)
	def __mul__(self, other):
		return vec2(self.x * other.x, self.y * other.y)
	def __truediv__(self, other):
		return vec2(self.x / other.x, self.y / other.y)
	def string(self):
		return str(self.x) + "," + str(self.y)
	def clone(self):
		return vec2(self.x, self.y)
	def round(self):
		return vec2(round(self.x), round(self.y))
	def mix(self, other, bias1):
		bias2 = 1 - bias1
		return vec2(self.x * bias2 + other.x * bias1, self.y * bias2 + other.y * bias1)
	def normalize(self):
		ref = max(abs(self.x), abs(self.y))
		if ref > 0:
			self.x = self.x / ref
			self.y = self.y / ref

# Vector3: A 3D vector containing X, Y, Z directions, typically used for positions and rotations in world space
class vec3:
	def __init__(self, x: float, y: float, z: float):
		self.x = x
		self.y = y
		self.z = z
	def __add__(self, other):
		return vec3(self.x + other.x, self.y + other.y, self.z + other.z)
	def __sub__(self, other):
		return vec3(self.x - other.x, self.y - other.y, self.z - other.z)
	def __mul__(self, other):
		return vec3(self.x * other.x, self.y * other.y, self.z * other.z)
	def __truediv__(self, other):
		return vec3(self.x / other.x, self.y / other.y, self.z / other.z)
	def string(self):
		return str(self.x) + "," + str(self.y) + "," + str(self.z)
	def clone(self):
		return vec3(self.x, self.y, self.z)
	def round(self):
		return vec3(round(self.x), round(self.y), round(self.z))
	def mix(self, other, bias1):
		bias2 = 1 - bias1
		return vec3(self.x * bias2 + other.x * bias1, self.y * bias2 + other.y * bias1, self.z * bias2 + other.z * bias1)
	def rotate(self, other):
		return vec3((self.x + other.x) % 360, (self.y + other.y) % 360, (self.z + other.z) % 360)
	def dir(self):
		# Directions X and Z are calculated from rotation Z, direction Y is calculated from rotation Y, rotation X is ignored as roll is currently not supported
		# X: -1 = Left, +1 = Right, Y: -1 = Down, +1 = Up, Z: -1 = Backward, +1 = Forward
		dir_x = math.sin(math.radians(self.z))
		dir_y = math.sin(math.radians(self.y))
		dir_z = math.cos(math.radians(self.z))
		return vec3(dir_x * (1 - abs(dir_y)), dir_y, dir_z * (1 - abs(dir_y)))
	def normalize(self):
		ref = max(abs(self.x), abs(self.y), abs(self.z))
		if ref > 0:
			self.x = self.x / ref
			self.y = self.y / ref
			self.z = self.z / ref

# RGB: Stores color in RGB format, handles conversion between RGB and HEX (eg: "255, 127, 0" = #ff7f00)
class rgb:
	def __init__(self, r: int, g: int, b: int):
		self.r = int(r)
		self.g = int(g)
		self.b = int(b)
	def clone(self):
		return rgb(self.r, self.g, self.b)
	def mix(self, col, bias1):
		bias2 = 1 - bias1
		return rgb(int(self.r * bias2 + col.r * bias1), int(self.g * bias2 + col.g * bias1), int(self.b * bias2 + col.b * bias1))
	def get_hex(self):
		return "%02x" % self.r + "%02x" % self.g + "%02x" % self.b

def hex_to_rgb(s: str):
	return rgb(int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))

# Random: Returns a random number with an amplitude, eg: 1 can be anything between -1 and +1
def rand(amp: float):
	if amp == 0:
		return 0
	return (-1 + random.random() * 2) * amp

# Convert an integer to a vec2, this allows fetching a 2D vector position from its index in a 1D string
def line_to_rect(i: int, width: int):
	return vec2(math.floor(i % width), math.floor(i / width))
