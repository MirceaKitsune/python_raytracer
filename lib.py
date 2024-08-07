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
	__slots__ = "x", "y"

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

	def __pow__(self, other):
		if isinstance(other, vec2):
			return vec2(self.x ** other.x, self.y ** other.y)
		else:
			return vec2(self.x ** other, self.y ** other)

	def __truediv__(self, other):
		if isinstance(other, vec2):
			return vec2(self.x / other.x, self.y / other.y)
		else:
			return vec2(self.x / other, self.y / other)

	def __floordiv__(self, other):
		if isinstance(other, vec2):
			return vec2(self.x // other.x, self.y // other.y)
		else:
			return vec2(self.x // other, self.y // other)

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
		return vec2(-self.x, -self.y)

	def __pos__(self):
		return vec2(+self.x, +self.y)

	def __invert__(self):
		return vec2(~self.x, ~self.y)

	def __abs__(self):
		return vec2(abs(self.x), abs(self.y))

	def __round__(self):
		return vec2(round(self.x), round(self.y))

	def __trunc__(self):
		return vec2(math.trunc(self.x), math.trunc(self.y))

	def __floor__(self):
		return vec2(math.floor(self.x), math.floor(self.y))

	def __ceil__(self):
		return vec2(math.ceil(self.x), math.ceil(self.y))

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
		ref = abs(self).maxs()
		if ref and ref != 1:
			return vec2(self.x, self.y) / ref
		return self

	def snapped(self, unit):
		if isinstance(unit, vec2):
			return vec2((self.x // unit.x) * unit.x, (self.y // unit.y) * unit.y)
		else:
			return vec2((self.x // unit) * unit, (self.y // unit) * unit)

# Vector3: A 3D vector containing X, Y, Z directions, typically used for positions and rotations in world space
class vec3:
	__slots__ = "x", "y", "z"

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

	def __pow__(self, other):
		if isinstance(other, vec3):
			return vec3(self.x ** other.x, self.y ** other.y, self.z ** other.z)
		else:
			return vec3(self.x ** other, self.y ** other, self.z ** other)

	def __truediv__(self, other):
		if isinstance(other, vec3):
			return vec3(self.x / other.x, self.y / other.y, self.z / other.z)
		else:
			return vec3(self.x / other, self.y / other, self.z / other)

	def __floordiv__(self, other):
		if isinstance(other, vec3):
			return vec3(self.x // other.x, self.y // other.y, self.z // other.z)
		else:
			return vec3(self.x // other, self.y // other, self.z // other)

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

	def normalize(self):
		ref = abs(self).maxs()
		if ref and ref != 1:
			return vec3(self.x, self.y, self.z) / ref
		return self

	def snapped(self, unit):
		if isinstance(unit, vec3):
			return vec3((self.x // unit.x) * unit.x, (self.y // unit.y) * unit.y, (self.z // unit.z) * unit.z)
		else:
			return vec3((self.x // unit) * unit, (self.y // unit) * unit, (self.z // unit) * unit)

	def quaternion(self):
		rad_x = math.radians(self.x)
		rad_y = math.radians(self.y)
		rad_z = math.radians(self.z)

		sin_x = math.sin(rad_x / 2)
		cos_x = math.cos(rad_x / 2)
		sin_y = math.sin(rad_y / 2)
		cos_y = math.cos(rad_y / 2)
		sin_z = math.sin(rad_z / 2)
		cos_z = math.cos(rad_z / 2)

		x = sin_x * cos_y * cos_z - cos_x * sin_y * sin_z
		y = cos_x * sin_y * cos_z - sin_x * cos_y * sin_z
		z = cos_x * cos_y * sin_z + sin_x * sin_y * cos_z
		w = cos_x * cos_y * cos_z + sin_x * sin_y * sin_z
		return quaternion(x, y, z, w)

# Quaternion: A special vector used to store and handle quaternion rotations
class quaternion:
	__slots__ = "x", "y", "z", "w"

	def __init__(self, x: float, y: float, z: float, w: float):
		self.x = x
		self.y = y
		self.z = z
		self.w = w

	def dot(self, other):
		return self.x * other.x + self.y * other.y + self.z * other.z + self.w * other.w

	def multiply(self, other):
		x = self.w * other.x + self.z * other.y - self.y * other.z + self.x * other.w
		y = self.z * other.x + self.w * other.y + self.x * other.z + self.y * other.w
		z = self.y * other.x - self.x * other.y + self.w * other.z + self.z * other.w
		w = self.x * other.x - self.y * other.y - self.z * other.z + self.w * other.w
		return quaternion(x, y, z, w)

	def vec_right(self):
		x = 1 - 2 * (self.y ** 2 + self.x ** 2)
		y = 2 * (self.z * self.y + self.w * self.x)
		z = 2 * (self.z * self.x - self.w * self.y)
		return vec3(x, y, z)

	def vec_up(self):
		x = 2 * (self.z * self.y - self.w * self.x)
		y = 1 - 2 * (self.z ** 2 + self.x ** 2)
		z = 2 * (self.y * self.x + self.w * self.z)
		return vec3(x, y, z)

	def vec_forward(self):
		x = 2 * (self.z * self.x + self.w * self.y)
		y = 2 * (self.y * self.x - self.w * self.z)
		z = 1 - 2 * (self.z ** 2 + self.y ** 2)
		return vec3(x, y, z)

# RGB: Stores color in RGB format
class rgb:
	__slots__ = "r", "g", "b"

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

# Returns the width and height of the most even 2D grid possible for the integer provided
def grid(unit: int):
	for i in range(math.isqrt(unit), 0, -1):
		if not unit % i:
			return unit // i, i

# Combine two lists while excluding duplicate items
def merge(items: list, items_new: list):
	result = list(items)
	for item in items_new:
		if not item in result:
			result.append(item)
	return result

# Unpack a list of containers into a single item
def unpack(items: list):
	result = []
	for item in items:
		result += item
	return result

# Returns the average result from a list of equal length
def average(items):
	if len(items[0]) <= 1:
		return items

	result = [0] * len(items[0])
	for slot in range(len(items[0])):
		for item in items:
			result[slot] += item[slot]
		result[slot] /= len(items)
	return result

# Random: Returns a random number with an amplitude, eg: 1 can be anything between -1 and +1
def rand(amp: float):
	if not amp:
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
	absorption = min(1, mat.absorption / ((1 + ray.bounces) ** (1 + settings.falloff)))

	# Color, energy: Translate the material's albedo and emission to ray color and energy, based on the ray's color absorption
	# Life: Scale ray life with absorption and roughness, the rougher or more absorbent a material is the less future bounces will provide noticeable detail
	# Roughness: Velocity is randomized by the roughness value of the interaction, 0 is perfectly sharp while 1 can send the ray in almost any direction
	# Bounces: Return the material absorption as the bounce amount, glass and fog have a lower probability of terminating rays sooner
	ray.color = ray.color.mix(mat.albedo, absorption)
	ray.energy = mix(ray.energy, mat.energy, absorption)
	ray.life *= 1 - (mat.roughness * absorption)
	ray.vel += vec3(rand(mat.roughness), rand(mat.roughness), rand(mat.roughness))
	return mat.absorption

# Builtin background function, generates a simple sky
def material_background(ray, settings):
	# Color and energy absorption falloff based on the number of hits and global falloff setting
	absorption = min(1, 1 / ((1 + ray.bounces) ** (1 + settings.falloff)))

	# Apply sky color and energy to the ray
	color = rgb(127, 127 + max(0, +ray.vel.y) * 64, 127 + max(0, +ray.vel.y) * 128)
	energy = 1 + max(0, +ray.vel.y)
	ray.color = ray.color.mix(color, absorption)
	ray.energy = mix(ray.energy, energy, absorption)

	# Offset ray color intensity based on the ray energy level
	ray.color.r = min(255, round(ray.color.r * ray.energy))
	ray.color.g = min(255, round(ray.color.g * ray.energy))
	ray.color.b = min(255, round(ray.color.b * ray.energy))
