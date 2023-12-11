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
  - fov: Field of view in degrees, higher values make the viewport wider.
  - dof: Depth of field in degrees, higher values result in more randomness added to the initial ray velocity and distance blur.
  - fog: Amount by which distant rays will gradually fade before vanishing. Not to be confused with real volumetric fog, this only affects the alpha value used to indicate ray blending to material functions. 0 disables fog fading, higher values push the effect further while making it sharper.
  - color_blur: Simulates motion blur and DOF edge smoothing, also acts as a cheaper alternative to multisampling. Each frame the previous color of the pixel is gradually blended with the new color by this amount. 0 disables and will look very rough, higher values reduce noise and make viewport updates smoother. No performance benefit but looks better.
  - color_burn: Retinal burn / iris adaptation effect. Since updates to the canvas can be costly, this improves performance by allowing a probabilistic threshold for pixels to be updated based on changes in color level. 0 disables and updates all colors immediately, higher values prioritize noticeable differences and delay minor ones. Produces temporary smudges and helps further smoothen out sudden noise.
  - dist_min: Minimum ray distance, voxels won't be checked until the ray has preformed this number of steps.
  - dist_max: Maximum ray distance, calculation stops and ray color is returned after this number of steps have been preformed.
  - terminate_hits: Limits the number of times a ray may hit a voxel before sampling stops. 0 disables and is unlimited, 1 only allows direct hits (no bounces), 2 and above allows `this - 1` number of bounces. Note that transparent voxels count as hits, if volumetric fog is decreasing draw distance increase or disable this.
  - terminate_random: Probability that sampling stops earlier the further a ray has traveled. 0 disables and lets all rays run at their full lifetime, 0.5 allows probabilistic termination to occur from halfway through a ray's life, 1 may terminate all rays but those just spawned in front of the camera. Improves performance but introduces noise in the distance.
  - threads: The number of threads to use for ray tracing by the thread pool, 0 will use all CPU cores.

## Default material settings

A material is registered using the register_material call of the Voxels class with a name, function, and list of settings. This is a list of the properties used to customize the default shader function, see the material programming section below on programming custom material functions.

  - albedo: The color of this material in hex format, eg: `#ff7f00`.
  - roughness: This amount of random roughness is added to the ray velocity when reflected or refracted.
  - translucency: Chance that a ray will pass through this voxel instead of being bounced back, probabilistically simulates transparency. Can be used to create volumetric fog, this is very costly and should only be done in small areas.

## Material programming

The engine allows creating custom materials which can have their own functions telling light rays how to behave. By default each material uses the material_default function located in data.py which can be customized using the settings documented above, it's recommended to use the default material unless you're an advanced user and need a custom shader to do things not supported by the default ray behavior.

A material function takes two parameters: The ray properties and the material we hit. Each function definition should thus be of the form `material_custom(ray, mat)`. See the default material section for the properties of the default material, eg: `mat.albedo` can be used to read color. Custom material settings are allowed for use in custom functions, as are custom ray properties which can be used to store data between ray hits. The following ray properties are used internally by the raytracer:

  - col: The color the ray has so far. This is usually the most important property to modify. If this is the first bounce col will be None instead of RGB, always check for its existence before preforming modifications.
  - alpha: Starts at 1 and is lowered by the raytracer based on ray distance and the `fog` setting. Used to indicate how much this ray should blend over the background: The material function can use this to apply transparency accordingly, use this to fade to the world background color.
  - pos: Current ray position. This should not be changed directly unless there's a reason to teleport the ray.
  - vel: Current ray velocity. The speed of light is 1, meaning at least one axis must be precisely -1 or +1 while the other two may be anything in that range: Always run vec3.normalize after making changes unless you're sure you want to change ray speed! If not values > abs(1) can cause voxels to be skipped, while values < abs(1) may cause the same voxel to be calculated twice... draw distance also scales accordingly.
  - step: The number of steps this ray has preformed. 1 is a ray that was just spawned at the camera's minimum draw distance, if `step` equals `life - 1` this is the last move the ray will preform. Can be modified to shorten or prolong the life of a ray.
  - life: The maximum number of steps this ray can preform before the resulting color is drawn. Starts at `dist_max - dist_min`, like `step` it can be modified to make ray life and draw distance shorter or longer.
  - hits: Number of times this voxel has bounced, limited by the `hits` camera setting. Current hit is accounted for so this always starts at 1. Keep in mind that hitting a translucent material may or may not increase this by random chance.
  - neighbors: A list of 6 entries containing the materials of direct neighbors of this voxel in the order: -x, +x, -y, +y, -z, +z. Primarily used to estimate face direction for ray reflection or refraction. Readonly, this is overwritten by the raytracer each hit.
