# Python Voxel Raytracer

Experimental CPU based voxel raytracing engine written in Python and based on Pygame. No meshes or textures: Everything is a floating point defined by a material. Materials can define their own functions as custom shaders. Designed for use at low resolutions and frame rates, the ray tracing algorithm is meant to be simple and efficient so expect noise and inaccuracy by design.

![alt text](cover.png)

The code is under the GPL license, created and developed by MirceaKitsune. Execute `python3 ./init.py` to start the engine with the default test scene. Use the mouse to look around with the following keys:

 - `WASDRF`: Move forward, backward, left, right, up, down.
 - `Mouse wheel`: Fast move forward, backward, left, right.
 - `Arrows`: Look up, down, left, right.
 - `Tab`: Toggle mouse look and pointer grabbing.
 - `Shift`: Hold to move 5 times faster with the keyboard.

## Features and TODO

  - [x] Programmable material functions. Each voxel can hold both unique material properties as well as a function that tells light rays how to behave upon collision.
  - [x] Simplified physically accurate material provided by default. Simulates all basic PBR features such as: Accurate reflections and refractions with roughness, plasticity and metalicity with accurate interactions, translucency and anisotropy with IOR support, density for volumetrics, emission via a ray energy system which supports ambient and sky lighting.
  - [ ] Support cammera rolling if this becomes possible. Current vector math doesn't support a third axis of transformation, you can only look horizontally and vertically.
  - [ ] Add perlin noise. May be possible to support an object based chunk system for generating infinite terrain.
  - [ ] Create a script to convert image slices into pixel meshes. This will allow importing 3D sprites from 2D images.
  - [ ] Support sprite animation. Basic support for sprite sets already exists: Once images can be imported as sprites allow changing the mesh periodically to play animations.
  - [ ] Support object movement and a basic physics system. Objects can only move at integer positions, collisions will be checked by finding intersecting voxels. May require a separate thread pool.
  - [ ] Sound support in the form of either audio files or a frequency generator associated with materials. Audio is also intended to be raytraced.

## Camera settings

Settings are stored within the `config.cfg` file and can be used to modify how the engine behaves. A custom config can be used by parsing it as an argument to the main script on launch, eg: `init.py my_config.cfg`. Below is a description of each category and setting:

  - `INPUT`: Input related settings for keyboard and mouse.
    - `speed_move`: Keyboard movement speed, determines how fast the camera moves when using the movement keys.
    - `speed_mouse`: Mouse rotation speed, determines how fast the camera rotates when moving the mouse in mouselook mode.
    - `max_pitch`: Maximum pitch angle in degrees, the camera can't look lower or higher than this amount. 0 disables, use a value below 180, 90 is recommended.
  - `WINDOW`: Window related settings such as resolution and frame rate.
    - `width`: Number of horizontal pixels, higher values allow more detail but greatly affect performance.
    - `height`: Number of vertical pixels.
    - `scale`: The size of each pixel, acts as a multiplier to width and height.
    - `smooth`: If false pixels are always sharp, if true use a bilinear filter when upscaling to the `scale` factor.
    - `fps`: Target number of frames per second, the end result may be lower or higher based on practical performance. FPS will be lowered when the window is not focused.
  - `RENDER`: Renderer related settings used by the camera.
    - `ambient`: Ambient light intensity, light rays start with this amount of energy.
    - `static`: Whether to use the pixel index as random noise seed and have a static pattern, alternative to using random noise each frame which produces flickering. Only affects material functions, effects such as DOF will still be dynamic.
    - `fov`: Field of view in degrees, higher values make the viewport wider.
    - `dof`: Depth of field in degrees, higher values result in more randomness added to the initial ray velocity and distance blur.
    - `skip`: Pixels that are closer to the edge of the screen have a random chance of not being recalculated each frame. Improves performance at the cost of increased grain in the corners of the viewport where pixels may take a few frames to update.
    - `blur`: Simulates motion blur and DOF edge smoothing, also acts as a cheaper alternative to multisampling. Each frame the previous color of the pixel is gradually blended with the new color by this amount. 0 disables and will look very rough, higher values reduce noise and make viewport updates smoother. No performance benefit but looks better.
    - `dist_min`: Minimum ray distance, voxels won't be checked until the ray has preformed this number of steps.
    - `dist_max`: Maximum ray distance, calculation stops and ray color is returned after this number of steps have been preformed.
    - `terminate_hits`: Random chance that sampling stops after this number of hits. 0 disables bounces and allows direct hits only, 0.5 has a 50/50 chance of stopping at any step after the first bounce, 1 guarantees at least one bounce with no stopping, 1.5 adds a 50/50 chance of the second bounce not being stopped, 2 allows two bounces with no stopping, etc. Higher values improve performance at the cost of shorter distances and extra blur for reflections. By default this is multiplied by the `ior` material property and hits are represented by how much the ray was reflected.
    - `terminate_dist`: Probability that sampling stops earlier the further a ray has traveled. 0 disables and lets all rays run at their full lifetime, 0.5 allows probabilistic termination to occur from halfway through a ray's life, 1 may terminate all rays but those just spawned in front of the camera. Improves performance but introduces noise in the distance, distant object will fade into the background gradually which looks better.
    - `threads`: The number of threads to use for ray tracing by the thread pool, 0 will use all CPU cores. The screen is divided in vertical chunks so that each thread processes and draws a different area of the canvas, ensure `height` is larger than and equally divisible by the thread count.

## Default material settings

A material is registered using the register_material call with a list of settings. Below is a list of properties used to customize the default shader function or specify your own, unique properties are supported for use in custom material functions. Note that materials are global, changes done to a material will be immediately reflected on all voxels with that material.

  - `function`: Material function to call when a ray hits this material, use `material_default` unless you want a custom shader. 
  - `albedo`: The color of this material in RGB format, eg: `255, 127, 0`. Blended to the light ray based on the ray's absorption.
  - `roughness`: This amount of random roughness is added to the ray velocity when reflected or refracted, also controls energy reduction. Blurs reflections, if `density` is enabled this also blurs rays passing through. If the `static` setting is enabled this produces a consistent pattern otherwise high values will cause flickering.
  - `absorption`: The ability of this material to absorb color, 0 acts as a perfect mirror while 1 is a perfect absorbant. Controls both transparency and metalicity: Use with an `ior` under 0.5 to get a transparent surface and over 0.5 for a metallic one. If solid use 1 for plastic, 0.5 for metal, 0 for a mirror... if transparent try 1 for painted glass or 0.25 for fog.
  - `ior`: Amount by which light rays are reflected by or pass through the surface. This isn't an accurate IOR value and named that way for familiarity, it multiplies how much the ray is reflected and acts as the real controller for determining translucency. If the material represents an opaque surface this should be 1 for accurate ray bounces, lower slightly to simulate anisotropy... a value close to 0.5 can be used to send rays inward and encourage subsurface scattering... if transparent it should be well below 0.5 to send light rays through, use a low value to simulate IOR or 0 to leave ray velocity unchanged.
  - `energy`: How much energy this material emits. Use 0 for normal surfaces and increase for voxels that emit light. A flame should be roughly 0.25, a standard light bulb 0.5 or lower, the sun should be 1.

Note: The number of hits accounted for by the raytracer increases with `ior`, a value of 0 doesn't count as a hit while 1 is a full hit. Low reflectivity reduces bounce based ray termination controlled by the `terminate_hits` setting, making rays live longer which may degrade performance if a ray gets stuck bouncing inside a solid. An `ior` of 0 can be used to make volumetric fog, but since fog voxels are processed without reducing ray life this should be done sparingly to avoid performance loss.

## Material programming

The engine allows creating custom materials which can have their own functions telling light rays how to behave. By default each material uses the material_default function located in data.py which can be customized using the settings documented above, it's recommended to use the default material unless you're an advanced user and need a custom shader to do things not supported by the default ray behavior.

A material function takes three parameters: The ray properties, the material we hit, and direct neighbors in order of `-X +X -Y +Y -Z +Z` used to calculate face normals. Each function definition should thus be of the form `material_custom(ray, mat, neighbors)`. See the default material section for the properties of the default material, eg: `mat.albedo` can be used to read color. Custom material settings are allowed for use in custom functions, as are custom ray properties which can be used to store data between ray hits. The following ray properties are used internally by the raytracer:

  - `col`: The color the ray has so far. This is usually the most important property to modify. If this is the first bounce col will be None instead of RGB, always check for its existence before preforming modifications.
  - `absorption`: Ability of this ray to change its color, should be modified based on the `absorption` setting of the material being hit. Color mixing should always be done based on this value, eg: `ray.col.mix(mat.albedo, ray.absorption)`. Starts at 1 and should be decreased by opaque hits that lack metalicity. Lower values blend future colors with less intensity, once 0 the color should no longer be changed.
  - `energy`: The amount of light the ray carries. `col` is multiplied by this value when applied to the screen. Starts out at the `ambient` configuration: This should decrease based on material metalicity or roughness, as well as increase when an emissive surface is hit.
  - `pos`: Current ray position. This should not be changed directly unless there's a reason to teleport the ray.
  - `vel`: Current ray velocity. The speed of light is 1, meaning at least one axis must be precisely -1 or +1 while the other two may be anything in that range: Always use `vec3.normalize` after making changes, otherwise values `> abs(1)` will cause voxels to be skipped while values `< abs(1)` can cause the same voxel to be calculated twice!
  - `step`: The number of steps this ray has preformed. 1 is a ray that was just spawned at the camera's minimum draw distance, if `step` equals `life - 1` this is the last move the ray will preform. Only modify this if you want to give the ray a one time boost, change `life` to properly alter the lifetime.
  - `life`: The maximum number of steps this ray can preform before the resulting color is drawn. Starts at `dist_max - dist_min`, modifying this is the recommended way to make ray life shorter or longer.
  - `hits`: Represents the number of times this ray has bounced. The value is checked but not changed by the raytracer: The material function must increment this accordinfly to indicate how many bounces were preformed otherwise some features may not work correctly! Add 1 for a fully opaque bounce, a value between 0 and 1 to represent transparency for translucent voxels.

Sky function: In addition to material functions which are executed when the ray touches a voxel, a background function will preform changes to the ray after it has preformed its last step, parsed as the parameter of the camera object. Unlike conventional materials the sky function doesn't have settings since only one exists and it operates in place, the only parameter is thus the `ray` object. There's no point in changing positional ray properties here as this always runs after the last step: You typically want to use velocity to produce a shape at infinite distance based on ray direction.
