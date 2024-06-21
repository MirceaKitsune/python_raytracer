#!/usr/bin/python3
import sys
import math
import random

# Store: Generic data storage, similar to the Python dictionary but allows getting and setting properties with dots (eg: data.prop instead of data["prop"])
class store:
	def __init__(self, **args):
		for a in args:
			setattr(self, a, args[a])

# Vector2: A 2D vector containing X, Y directions, typically used for pixel positions in screen
class vec2:
	__slots__ = ("x", "y")

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

	def __eq__(self, other):
		if isinstance(other, vec2):
			return self.x == other.x and self.y == other.y
		else:
			return self.x == other and self.y == other

	def __ne__(self, other):
		if isinstance(other, vec2):
			return self.x != other.x or self.y != other.y
		else:
			return self.x != other or self.y != other

	def __lt__(self, other):
		if isinstance(other, vec2):
			return self.x < other.x and self.y < other.y
		else:
			return self.x < other and self.y < other

	def __le__(self, other):
		if isinstance(other, vec2):
			return self.x <= other.x and self.y <= other.y
		else:
			return self.x <= other and self.y <= other

	def __gt__(self, other):
		if isinstance(other, vec2):
			return self.x > other.x and self.y > other.y
		else:
			return self.x > other and self.y > other

	def __ge__(self, other):
		if isinstance(other, vec2):
			return self.x >= other.x and self.y >= other.y
		else:
			return self.x >= other and self.y >= other

	def __neg__(self):
		return vec3(-self.x, -self.y)

	def __pos__(self):
		return vec3(+self.x, +self.y)

	def __invert__(self):
		return vec3(~self.x, ~self.y)

	def __abs__(self):
		return vec3(abs(self.x), abs(self.y))

	def __round__(self):
		return vec3(round(self.x), round(self.y))

	def __trunc__(self):
		return vec3(math.trunc(self.x), math.trunc(self.y))

	def __floor__(self):
		return vec3(math.floor(self.x), math.floor(self.y))

	def __ceil__(self):
		return vec3(math.ceil(self.x), math.ceil(self.y))

	def __str__(self):
		return str(self.x) + "," + str(self.y)

	def array(self):
		return [self.x, self.y]

	def tuple(self):
		return (self.x, self.y)

	def mins(self):
		return min(self.x, self.y)

	def maxs(self):
		return max(self.x, self.y)

	def min(self, other):
		if isinstance(other, vec2):
			return vec2(min(self.x, other.x), min(self.y, other.y))
		else:
			return vec2(min(self.x, other), min(self.y, other))

	def max(self, other):
		if isinstance(other, vec2):
			return vec2(max(self.x, other.x), max(self.y, other.y))
		else:
			return vec2(max(self.x, other), max(self.y, other))

	def distance(self, other):
		return math.dist(self.array(), other.array())

	def total(self):
		return (abs(self.x) + abs(self.y)) / 2

	def mix(self, other, bias1):
		bias2 = 1 - bias1
		return self * bias2 + other * bias1

	def normalize(self):
		ref = max(abs(self.x), abs(self.y))
		if ref:
			return vec2(self.x, self.y) / ref
		return self

	# Snap to a grid unit, offset can be used to control how to snap to the unit (-1 = floor, 0 = round, +1 = ceil)
	def snapped(self, unit, offset: float):
		if isinstance(unit, vec2):
			return vec2(round(self.x / unit.x + offset / 2) * unit.x, round(self.y / unit.y + offset / 2) * unit.y)
		else:
			return vec2(round(self.x / unit + offset / 2) * unit, round(self.y / unit + offset / 2) * unit)

# Vector3: A 3D vector containing X, Y, Z directions, typically used for positions and rotations in world space
class vec3:
	__slots__ = ("x", "y", "z")

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

	def __eq__(self, other):
		if isinstance(other, vec3):
			return self.x == other.x and self.y == other.y and self.z == other.z
		else:
			return self.x == other and self.y == other and self.z == other

	def __ne__(self, other):
		if isinstance(other, vec3):
			return self.x != other.x or self.y != other.y or self.z != other.z
		else:
			return self.x != other or self.y != other or self.z != other

	def __lt__(self, other):
		if isinstance(other, vec3):
			return self.x < other.x and self.y < other.y and self.z < other.z
		else:
			return self.x < other and self.y < other and self.z < other

	def __le__(self, other):
		if isinstance(other, vec3):
			return self.x <= other.x and self.y <= other.y and self.z <= other.z
		else:
			return self.x <= other and self.y <= other and self.z <= other

	def __gt__(self, other):
		if isinstance(other, vec3):
			return self.x > other.x and self.y > other.y and self.z > other.z
		else:
			return self.x > other and self.y > other and self.z > other

	def __ge__(self, other):
		if isinstance(other, vec3):
			return self.x >= other.x and self.y >= other.y and self.z >= other.z
		else:
			return self.x >= other and self.y >= other and self.z >= other

	def __neg__(self):
		return vec3(-self.x, -self.y, -self.z)

	def __pos__(self):
		return vec3(+self.x, +self.y, +self.z)

	def __invert__(self):
		return vec3(~self.x, ~self.y, ~self.z)

	def __abs__(self):
		return vec3(abs(self.x), abs(self.y), abs(self.z))

	def __round__(self):
		return vec3(round(self.x), round(self.y), round(self.z))

	def __trunc__(self):
		return vec3(math.trunc(self.x), math.trunc(self.y), math.trunc(self.z))

	def __floor__(self):
		return vec3(math.floor(self.x), math.floor(self.y), math.floor(self.z))

	def __ceil__(self):
		return vec3(math.ceil(self.x), math.ceil(self.y), math.ceil(self.z))

	def __str__(self):
		return str(self.x) + "," + str(self.y) + "," + str(self.z)

	def array(self):
		return [self.x, self.y, self.z]

	def tuple(self):
		return (self.x, self.y, self.z)

	def mins(self):
		return min(self.x, self.y, self.z)

	def maxs(self):
		return max(self.x, self.y, self.z)

	def min(self, other):
		if isinstance(other, vec3):
			return vec3(min(self.x, other.x), min(self.y, other.y), min(self.z, other.z))
		else:
			return vec3(min(self.x, other), min(self.y, other), min(self.z, other))

	def max(self, other):
		if isinstance(other, vec3):
			return vec3(max(self.x, other.x), max(self.y, other.y), max(self.z, other.z))
		else:
			return vec3(max(self.x, other), max(self.y, other), max(self.z, other))

	def distance(self, other):
		return math.dist(self.array(), other.array())

	def total(self):
		return (abs(self.x) + abs(self.y) + abs(self.z)) / 3

	def mix(self, other, bias1):
		bias2 = 1 - bias1
		return self * bias2 + other * bias1

	def rotate(self, other):
		return vec3((self.x + other.x) % 360, (self.y + other.y) % 360, (self.z + other.z) % 360)

	# Directions X and Z are calculated from rotation Z, direction Y is calculated from rotation Y, rotation X is ignored as roll is currently not supported
	# If normalized X and Z scale with Y to maintain a constant magnitude of the direction vector, desired for camera projection but should be off when calculating movement vectors
	# X: -1 = Left, +1 = Right. Y: -1 = Down, +1 = Up. Z: -1 = Backward, +1 = Forward.
	def dir(self, normalize: bool):
		rad_y = math.radians(self.y)
		rad_z = math.radians(self.z)
		dir_x = math.sin(rad_z) * math.cos(rad_y) if normalize else math.sin(rad_z)
		dir_y = math.sin(rad_y)
		dir_z = math.cos(rad_z) * math.cos(rad_y) if normalize else math.cos(rad_z)
		return vec3(dir_x, dir_y, dir_z)

	def normalize(self):
		ref = max(abs(self.x), abs(self.y), abs(self.z))
		if ref:
			return vec3(self.x, self.y, self.z) / ref
		return self

	# Snap to a grid unit, offset can be used to control how to snap to the unit (-1 = floor, 0 = round, +1 = ceil)
	def snapped(self, unit, offset: float):
		if isinstance(unit, vec3):
			return vec3(round(self.x / unit.x + offset / 2) * unit.x, round(self.y / unit.y + offset / 2) * unit.y, round(self.z / unit.z + offset / 2) * unit.z)
		else:
			return vec3(round(self.x / unit + offset / 2) * unit, round(self.y / unit + offset / 2) * unit, round(self.z / unit + offset / 2) * unit)

# RGB: Stores color in RGB format
class rgb:
	__slots__ = ("r", "g", "b")

	def __init__(self, r: int, g: int, b: int):
		self.r = r
		self.g = g
		self.b = b

	def array(self):
		return [self.r, self.g, self.b]

	def tuple(self):
		return (self.r, self.g, self.b)

	def mix(self, col, bias1):
		bias2 = 1 - bias1
		return rgb(round(self.r * bias2 + col.r * bias1), round(self.g * bias2 + col.g * bias1), round(self.b * bias2 + col.b * bias1))

# Random: Returns a random number with an amplitude, eg: 1 can be anything between -1 and +1
def rand(amp: float):
	if amp == 0:
		return 0
	return (-1 + random.random() * 2) * amp

# Mix: Mixes two values based on a bias
def mix(val1, val2, bias1):
	bias2 = 1 - bias1
	return val1 * bias2 + val2 * bias1

# Normalize: Returns a 0 to 1 range representing the position of x between x_min and x_max
def normalize(x, x_min, x_max):
	if x_min >= x_max:
		return 0
	return min(1, max(0, (x - x_min) / (x_max - x_min)))

# Builtin material function, designed as a simplified PBR shader
def material(ray, mat, settings):
	# Color and energy absorption falloff based on the number of hits and global falloff setting
	absorption = mat.absorption / ((1 + ray.bounces) ** (1 + settings.falloff))

	# Color, energy: Translate the material's albedo and emission to ray color and energy, based on the ray's color absorption
	# Roughness: Velocity is randomized by the roughness value of the interaction, 0 is perfectly sharp while 1 can send the ray in almost any direction
	# Bounces: Return the material absorption as the bounce amount, glass and fog have a lower probability of terminating rays sooner
	ray.color = ray.color.mix(mat.albedo, absorption)
	ray.energy = mix(ray.energy, mat.energy, absorption)
	ray.vel += vec3(rand(mat.roughness), rand(mat.roughness), rand(mat.roughness))
	return mat.absorption

# Builtin background function, generates a simple sky
def material_background(ray, settings):
	# Color and energy absorption falloff based on the number of hits and global falloff setting
	absorption = 1 / ((1 + ray.bounces) ** (1 + settings.falloff))

	# Apply sky color and energy to the ray
	color = rgb(127, 127 + max(0, +ray.vel.y) * 64, 127 + max(0, +ray.vel.y) * 128)
	energy = 1 + max(0, +ray.vel.y) * 1
	ray.color = ray.color.mix(color, absorption)
	ray.energy = mix(ray.energy, energy, absorption)

	# Offset ray color intensity based on the ray energy level
	ray.color.r = min(255, round(ray.color.r * ray.energy))
	ray.color.g = min(255, round(ray.color.g * ray.energy))
	ray.color.b = min(255, round(ray.color.b * ray.energy))
