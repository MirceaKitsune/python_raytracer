# Python Raytracer

Experimental CPU based voxel raytracing engine written in Python. No meshes or textures: Everything is a floating point defined by a material. Materials can define their own functions as custom shaders. Designed for low resolutions and frame rates.

## Camera settings
  - width: Number of horizontal pixels, higher values allow more detail but greatly affect performance.
  - height: Number of vertical pixels.
  - scale: The size of each pixel, acts as a multiplier to width and height.
  - fps: Target number of frames per second, the end result may be lower or higher based on performance.
  - samples_min: Minimum number of samples per pixel to preform each draw, zero or negative values are allowed to probabilistically skip pixels.
  - samples_max: Maximum number of samples per pixel to preform each draw, fixed if equal to samples_min otherwise random.
  - fov: Field of view in degrees, higher values make the viewport wider.
  - dof: Depth of field in degrees, higher values result in more randomness added to the initial ray velocity and distance blur.
  - dist_min: Minimum ray distance, voxels won't be checked until the ray has preformed this number of steps.
  - dist_max: Maximum ray distance, calculation stops and ray color is returned after this number of steps have been preformed.
  - threads: The number of threads to use for ray tracing, 0 causes the CPU count to be used.

## Default material settings

  - albedo: The color of this material in hex format, eg: #ff7f00.
  - roughness: This amount of random roughness is added to the ray velocity when reflected or refracted.
