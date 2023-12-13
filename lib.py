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
		if isinstance(other, vec2):
			return vec2(self.x + other.x, self.y + other.y)
		else:
			return vec2(self.x + other, self.y + other)

	def __sub__(self, other):
		if isinstance(other, vec2):
			return vec2(self.x - other.x, self.y - other.y)
		else:
			return vec2(self.x - other, self.y - other)

	def __mul__(self, other):
		if isinstance(other, vec2):
			return vec2(self.x * other.x, self.y * other.y)
		else:
			return vec2(self.x * other, self.y * other)

	def __truediv__(self, other):
		if isinstance(other, vec2):
			return vec2(self.x / other.x, self.y / other.y)
		else:
			return vec2(self.x / other, self.y / other)

	def clone(self):
		return vec2(self.x, self.y)

	def string(self):
		return str(self.x) + "," + str(self.y)

	def int(self):
		return vec2(int(self.x), int(self.y))

	def round(self, digits):
		return vec2(round(self.x, digits), round(self.y, digits))

	def mix(self, other, bias1):
		bias2 = 1 - bias1
		return self * bias2 + other * bias1

	def normalize(self):
		ref = max(abs(self.x), abs(self.y))
		if ref > 0:
			return vec2(self.x, self.y) / ref
		return self

# Vector3: A 3D vector containing X, Y, Z directions, typically used for positions and rotations in world space
class vec3:
	def __init__(self, x: float, y: float, z: float):
		self.x = x
		self.y = y
		self.z = z

	def __add__(self, other):
		if isinstance(other, vec3):
			return vec3(self.x + other.x, self.y + other.y, self.z + other.z)
		else:
			return vec3(self.x + other, self.y + other, self.z + other)

	def __sub__(self, other):
		if isinstance(other, vec3):
			return vec3(self.x - other.x, self.y - other.y, self.z - other.z)
		else:
			return vec3(self.x - other, self.y - other, self.z - other)

	def __mul__(self, other):
		if isinstance(other, vec3):
			return vec3(self.x * other.x, self.y * other.y, self.z * other.z)
		else:
			return vec3(self.x * other, self.y * other, self.z * other)

	def __truediv__(self, other):
		if isinstance(other, vec3):
			return vec3(self.x / other.x, self.y / other.y, self.z / other.z)
		else:
			return vec3(self.x / other, self.y / other, self.z / other)

	def clone(self):
		return vec3(self.x, self.y, self.z)

	def string(self):
		return str(self.x) + "," + str(self.y) + "," + str(self.z)

	def int(self):
		return vec3(int(self.x), int(self.y), int(self.z))

	def round(self, digits):
		return vec3(round(self.x, digits), round(self.y, digits), round(self.z, digits))

	def mix(self, other, bias1):
		bias2 = 1 - bias1
		return self * bias2 + other * bias1

	def rotate(self, other):
		return vec3((self.x + other.x) % 360, (self.y + other.y) % 360, (self.z + other.z) % 360)

	def dir(self, normalize: bool):
		# Directions X and Z are calculated from rotation Z, direction Y is calculated from rotation Y, rotation X is ignored as roll is currently not supported
		# If normalized X and Z scale with Y to maintain a constant magnitude of the direction vector, desired for camera projection but should be off when calculating movement vectors
		# X: -1 = Left, +1 = Right. Y: -1 = Down, +1 = Up. Z: -1 = Backward, +1 = Forward.
		rad_y = math.radians(self.y)
		rad_z = math.radians(self.z)
		dir_x = math.sin(rad_z) * (normalize and math.cos(rad_y) or 1)
		dir_y = math.sin(rad_y)
		dir_z = math.cos(rad_z) * (normalize and math.cos(rad_y) or 1)
		return vec3(dir_x, dir_y, dir_z)

	def normalize(self):
		ref = max(abs(self.x), abs(self.y), abs(self.z))
		if ref > 0:
			return vec3(self.x, self.y, self.z) / ref
		return self

# vec2 and vec3 helpers, most notably the conversion function allowing vectors to be converted to and from an integer
# As ray calculations can be costly, ordered lists are used to store spatial data at integer positions without having to specify a position vector
# The index of the list item can be used to deduce the position in 2D or 3D space via these functions, eg: index 5 is vec2(1, 1) in a 4 x 4 square
def index_vec2(i: int, width: int):
	y, x = divmod(i, width)
	return vec2(int(x), int(y))

def vec2_index(v: vec2, width: int):
	return int(v.x + v.y * width)

def vec2_neighbors(pos: vec2):
	# Neighbor order: -x, +x, -y, +y
	return [pos - vec2(1, 0), pos + vec2(1, 0), pos - vec2(0, 1), pos + vec2(0, 1)]

def index_vec3(i: int, width: int, height: int):
	z, xy = divmod(i, width * height)
	y, x = divmod(xy, width)
	return vec3(int(x), int(y), int(z))

def vec3_index(v: vec3, width: int, height: int):
	return int(v.x + v.y * width + v.z * width * height)

def vec3_neighbors(pos: vec3):
	# Neighbor order: -x, +x, -y, +y, -z, +z
	return [pos - vec3(1, 0, 0), pos + vec3(1, 0, 0), pos - vec3(0, 1, 0), pos + vec3(0, 1, 0), pos - vec3(0, 0, 1), pos + vec3(0, 0, 1)]

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

# Normalize: Returns a 0 to 1 range representing the position of x between x_min and x_max
def normalize(x, x_min, x_max):
	if x_min >= x_max:
		return 0
	return min(1, max(0, (x - x_min) / (x_max - x_min)))
