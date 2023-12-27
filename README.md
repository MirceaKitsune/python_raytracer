# Python Raytracer

Experimental CPU based voxel raytracing engine written in Python and based on Pygame. No meshes or textures: Everything is a floating point defined by a material. Materials can define their own functions as custom shaders. Designed for use at low resolutions and frame rates, the ray tracing algorithm is meant to be simple and efficient so expect noise and inaccuracy by design.

![alt text](cover.png)

The code is under the GPL license, created and developed by MirceaKitsune. Execute `python3 ./init.py` to start the engine with the default test scene. Use the mouse to look around with the following keys:

 - WASDRF: Move forward, backward, left, right, up, down.
 - Mouse wheel: Fast move forward, backward, left, right.
 - Arrows: Look up, down, left, right.
 - Tab: Toggle mouse look and pointer grabbing.
 - Shift: Hold to move 5 times faster with the keyboard.

## Features and TODO

  - [x] Programmable material functions. Each voxel can hold both unique material properties as well as a function that tells light rays how to behave upon collision.
  - [ ] Finish all basic material properties: Reflection (done), refraction, metalicity, emission, subsurface scattering. Currently there is no lighting system.
  - [ ] Add a skybox system and support environment lighting. Currently everything not hit by a ray is a black void.
  - [ ] Support cammera rolling if this becomes possible. Current vector math doesn't support a third axis of transformation, you can only look horizontally and vertically.
  - [ ] Add perlin noise. May be possible to support an object based chunk system for generating infinite terrain.
  - [ ] Create a script to convert image slices into pixel meshes. This will allow importing 3D sprites from 2D images.
  - [ ] Support sprite animation. Basic support for sprite sets already exists: Once images can be imported as sprites allow changing the mesh periodically to play animations.
  - [ ] Allow object rotation. Fine rotation will likely never be possible, but rotations of 90* / 180* / 270* will be possible to support in the future.
  - [ ] Support object movement and a basic physics system. Objects can only move at integer positions, collisions will be checked by finding intersecting voxels. May require a separate thread pool.
  - [ ] Sound support in the form of either audio files or a frequency generator associated with materials. Audio is also intended to be raytraced.

## Camera settings

Settings are stored within the `config.cfg` file and can be used to modify how the engine behaves. A custom config can be used by parsing it as an argument to the main script on launch, eg: `init.py my_config.cfg`. Below is a description of each category and setting:

  - INPUT: Input related settings for keyboard and mouse.
    - speed_move: Keyboard movement speed, determines how fast the camera moves when using the movement keys.
    - speed_mouse: Mouse rotation speed, determines how fast the camera rotates when moving the mouse in mouselook mode.
    - max_pitch: Maximum pitch angle in degrees, the camera can't look lower or higher than this amount. 0 disables, use a value below 180, 90 is recommended.
  - WINDOW: Window related settings such as resolution and frame rate.
    - width: Number of horizontal pixels, higher values allow more detail but greatly affect performance.
    - height: Number of vertical pixels.
    - scale: The size of each pixel, acts as a multiplier to width and height.
    - smooth: If false pixels are always sharp, if true use a bilinear filter when upscaling to the `scale` factor.
    - fps: Target number of frames per second, the end result may be lower or higher based on practical performance. FPS will be lowered when the window is not focused.
  - RENDER: Renderer related settings used by the camera.
    - fov: Field of view in degrees, higher values make the viewport wider.
    - dof: Depth of field in degrees, higher values result in more randomness added to the initial ray velocity and distance blur.
    - fog: Amount by which distant rays will gradually fade before vanishing. Not to be confused with real volumetric fog, this only affects the alpha value used to indicate ray blending to material functions. 0 disables fog fading, higher values push the effect further while making it sharper.
    - iris: Retinal burn or iris adaptation effect. Improves performance by allowing a probabilistic threshold for pixels to be updated, based on changes in color level during the previous frame which gives priority to noisy pixels. 0 disables and updates all colors immediately, higher values prioritize noticeable differences and delay minor ones, 1 can cause updates to stop permanently so always use a lower value.
    - blur: Simulates motion blur and DOF edge smoothing, also acts as a cheaper alternative to multisampling. Each frame the previous color of the pixel is gradually blended with the new color by this amount. 0 disables and will look very rough, higher values reduce noise and make viewport updates smoother. No performance benefit but looks better.
    - dist_min: Minimum ray distance, voxels won't be checked until the ray has preformed this number of steps.
    - dist_max: Maximum ray distance, calculation stops and ray color is returned after this number of steps have been preformed.
    - terminate_hits: Random chance that sampling stops after this number of hits. 0 disables bounces and allows direct hits only, 0.5 has a 50/50 chance of stopping at any step after the first bounce, 1 guarantees at least one bounce with no stopping, 1.5 adds a 50/50 chance of the second bounce not being stopped, 2 allows two bounces with no stopping, etc. Higher values improve performance at the cost of shorter distances and more blur for reflections.
    - terminate_dist: Probability that sampling stops earlier the further a ray has traveled. 0 disables and lets all rays run at their full lifetime, 0.5 allows probabilistic termination to occur from halfway through a ray's life, 1 may terminate all rays but those just spawned in front of the camera. Improves performance but introduces noise in the distance.
    - threads: The number of threads to use for ray tracing by the thread pool, 0 will use all CPU cores.

The object list is the first property that must be passed to the Window class. Object arguments include:

  - origin: The center of the object will be located at this point in space.
  - size: The bounding box of this object. Light rays will first make sure they're located inside this box before checking voxels. Voxels may only be added within the bounderies of this box, anything else will be ignored and produce a warning.
  - active: Can be set to false to quickly disable this object so it's ignored by the raytracer. This is ideal as checking ray intersections with bounding boxes can be costly.

## Default material settings

A material is registered using the register_material call with a list of settings. Materials can be modified per voxel: A custom object function or external script may change the material properties of a particular voxel without affecting other voxels or the original material definition. Below is a list of properties used to customize the default shader function or specify your own, unique properties are supported for use in custom material functions.

  - function: Material function to call when a ray hits this material, use material_default unless you want a custom shader. 
  - albedo: The color of this material in hex format, eg: `#ff7f00`.
  - roughness: This amount of random roughness is added to the ray velocity when reflected or refracted.
  - translucency: Chance that a ray will pass through this voxel instead of being bounced back, probabilistically simulates transparency. Can be used to create volumetric fog, this is costly and should be done in small areas.
  - group: Builtin material property representing a group other materials should interact with. Voxels will only treat neighbors with the same value as solid when calculating surface normals.
  - normals: Builtin material property set by objects when updating voxels, does not need to be included in the material definition. Represents the directions in which this voxel contains open spaces, used to determine face direction for reflecting rays. Neighbor order is `-x +x -y +y -z +z`.

## Material programming

The engine allows creating custom materials which can have their own functions telling light rays how to behave. By default each material uses the material_default function located in data.py which can be customized using the settings documented above, it's recommended to use the default material unless you're an advanced user and need a custom shader to do things not supported by the default ray behavior.

A material function takes two parameters: The ray properties and the material we hit. Each function definition should thus be of the form `material_custom(ray, mat)`. See the default material section for the properties of the default material, eg: `mat.albedo` can be used to read color. Custom material settings are allowed for use in custom functions, as are custom ray properties which can be used to store data between ray hits. The following ray properties are used internally by the raytracer:

  - col: The color the ray has so far. This is usually the most important property to modify. If this is the first bounce col will be None instead of RGB, always check for its existence before preforming modifications.
  - alpha: Starts at 1 and is lowered by the raytracer based on ray distance and the `fog` setting. Used to indicate how much this ray should blend over the background: The material function can use this to apply transparency accordingly, use this to fade to the world background color.
  - pos: Current ray position. This should not be changed directly unless there's a reason to teleport the ray.
  - vel: Current ray velocity. The speed of light is 1, meaning at least one axis must be precisely -1 or +1 while the other two may be anything in that range: Always use `vec3.normalize` after making changes, otherwise values `> abs(1)` will cause voxels to be skipped while values `< abs(1)` can cause the same voxel to be calculated twice!
  - step: The number of steps this ray has preformed. 1 is a ray that was just spawned at the camera's minimum draw distance, if `step` equals `life - 1` this is the last move the ray will preform. Only modify this if you want to give the ray a one time boost, change `life` to properly alter the lifetime.
  - life: The maximum number of steps this ray can preform before the resulting color is drawn. Starts at `dist_max - dist_min`, modifying this is the recommended way to make ray life shorter or longer.
  - hits: Represents the number of times this ray has bounced. The value is checked but not changed by the raytracer: The material function must increment this accordinfly to indicate how many bounces were preformed otherwise some features may not work correctly! Add 1 for a fully opaque bounce, a value between 0 and 1 to represent transparency for translucent voxels.

Note that while you can modify any of the above properties on the material of a voxel from the material function, such modifications will be lost: Threads don't share changes with each other or the main thread, any modification will only be seen by the same process currently calculating the ray. If you wish to change a property on a voxel's material, do so in a custom function which ensures changes are returned to the main thread.
