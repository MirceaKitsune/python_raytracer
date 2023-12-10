# Python Raytracer

Experimental CPU based voxel raytracing engine written in Python, requires Tkinter. No meshes or textures: Everything is a floating point defined by a material. Materials can define their own functions as custom shaders. Designed for use at low resolutions and frame rates, the ray tracing algorithm is meant to be simple and efficient so expect noise and inaccuracy by design.

## Movement

Use the WASDRF keys to move forward, backward, left, right, up, down. Use the arrow keys to change angle. Camera roll is not supported by the vector class. Mouse support is currently not implemented due to issues with pointer snapping.

## Camera settings

The Window class in init.py is responsible for creating the window and its associated raytracer. When created it takes a voxels database containing registered materials which also holds voxel positions, as well as a list of settings describing how the engine should behave. Settings include:

  - width: Number of horizontal pixels, higher values allow more detail but greatly affect performance.
  - height: Number of vertical pixels.
  - scale: The size of each pixel, acts as a multiplier to width and height.
  - fps: Target number of frames per second, the end result may be lower or higher based on performance.
  - skip: Probabilistically skip recalculating pixels each frame, improves performance at the cost of extra viewport grain since some pixels may take a few frames to refresh.
  - smooth: Each frame the previous color of the pixel is gradually blended with the new color by this amount. Simulates multisampling: 0 disables and will look very rough, higher values reduce noise while improving DOF and simulating motion blur.
  - fov: Field of view in degrees, higher values make the viewport wider.
  - dof: Depth of field in degrees, higher values result in more randomness added to the initial ray velocity and distance blur.
  - hits: Limits the number of times a ray may hit a voxel before sampling stops. 0 disables and is unlimited, 1 only allows direct hits only (no bounces), 2 and above allows this - 1 number of bounces. Note that transparent voxels count as hits, if volumetric fog is decreasing draw distance increase or disable this.
  - dist_min: Minimum ray distance, voxels won't be checked until the ray has preformed this number of steps.
  - dist_max: Maximum ray distance, calculation stops and ray color is returned after this number of steps have been preformed.
  - threads: The number of threads to use for ray tracing by the thread pool, 0 will use all CPU cores.

## Default material settings

A material is registered using the register_material call of the Voxels class with a name, function, and list of settings. This is a list of the properties used to customize the default shader function, see the material programming section below on programming custom material functions.

  - albedo: The color of this material in hex format, eg: `#ff7f00`.
  - roughness: This amount of random roughness is added to the ray velocity when reflected or refracted.
  - translucency: Random chance that a ray will pass through this voxel without being affected, probabilistically simulates transparency.
  - angle: Surface reflection angle in degrees. Voxels are points in space and don't have normals or a face direction so nothing defines which way a ray should bounce back: This is a simplified solution for simulating reflection angles and IOR. If 0 the ray's velocity will not be modified, if 360 the ray is fully inverted and sent back toward the camera... for the most realistic result use 180.

## Material programming

The engine allows creating custom materials which can have their own functions telling light rays how to behave. By default each material uses the material_default function located in data.py which can be customized using the settings documented above, it's recommended to use the default material unless you're an advanced user and need a custom shader to do things not supported by the default ray behavior.

A material function takes two parameters: The ray properties and the material we hit. Each function definition should thus be of the form `material_custom(ray, mat)`. See the default material section for the properties of the default material, eg: `mat.albedo` can be used to read color. Custom material settings are allowed for use in custom functions, as are custom ray properties which can be used to store data between ray hits. The following ray properties are used internally by the raytracer:

  - col: The color the ray has so far. This is usually the most important property to modify. If this is the first bounce col will be None instead of RGB, always check for its existence before preforming modifications.
  - pos: Current ray position. This should not be changed directly unless there's a reason to teleport the ray.
  - vel: Current ray velocity. The speed of light is 1, meaning at least one axis must be precisely -1 or +1 while the other two may be anything in that range: Always run vec3.normalize after making changes unless you're sure you want to change ray speed! If not values > abs(1) can cause voxels to be skipped, while values < abs(1) may cause the same voxel to be calculated twice... draw distance also scales accordingly.
  - step: The number of steps this ray has preformed. 1 is a ray that was just spawned at the camera's minimum draw distance, if `step` equals `life - 1` this is the last move the ray will preform. Can be modified to shorten or prolong the life of a ray.
  - life: The maximum number of steps this ray can preform before the resulting color is drawn. Starts at `dist_max - dist_min`, like `step` it can be modified to make ray life and draw distance shorter or longer.
  - hits: Number of times this voxel has bounced, limited by the `hits` camera setting. Current hit is accounted for so this always starts at 1. Keep in mind that hitting a translucent material may or may not increase this by random chance.
