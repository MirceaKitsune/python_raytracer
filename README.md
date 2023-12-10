# Python Raytracer

Experimental CPU based voxel raytracing engine written in Python, requires Tkinter. No meshes or textures: Everything is a floating point defined by a material. Materials can define their own functions as custom shaders. Designed for use at low resolutions and frame rates, the ray tracing algorithm is meant to be simple and efficient so expect noise and inaccuracy by design.

## Movement

Use the WASDRF keys to move forward, backward, left, right, up, down. Use the arrow keys to change angle, mouse support is currently not implemented.

## Camera settings

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

  - albedo: The color of this material in hex format, eg: #ff7f00.
  - roughness: This amount of random roughness is added to the ray velocity when reflected or refracted.
  - translucency: Random chance that a ray will pass through this voxel without being affected, probabilistically simulates transparency.
  - angle: Surface reflection angle in degrees. Voxels are points in space and don't have normals or a face direction so nothing defines which way a ray should bounce back: This is a simplified solution for simulating reflection angles and IOR. If 0 the ray's velocity will not be modified, if 360 the ray is fully inverted and sent back toward the camera... for the most realistic result use 180.

## Material programming

The engine allows creating custom materials which can have their own functions telling light rays how to behave. The register_material function takes the material name as its first parameter, the name of its function, and a dictionary of settings used by this function. By default each material uses the material_default function located in data.py which can be customized using the settings above, custom functions can have their own unique settings.

A material function must be defined with the parameters "pos, vel, col, step, data" as follows:

  - col: The color the ray has so far. If this is the first bounce col will be None instead of RGB, always check for its existence before preforming modifications.
  - pos: Current ray position.
  - vel: Current ray velocity.
  - step: Range representing the ray's lifetime. A value close to 0 is a ray that was recently spawned, values close to 1 indicate a distant ray preforming its last movements.
  - hits: Number of times this voxel bounced so far, limited by the hits camera setting. Current hit is counted thus this always starts at 1.
  - data: Material data containing the settings of the material, for example use data["albedo"] to get this material's color.

It needs to return the tuple "pos, vel, col" to apply changes as follows:

  - col: New color the pixel will have.
  - pos: New position of the ray.
  - vel: New velocity of this ray.
