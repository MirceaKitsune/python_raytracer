# Python Voxel Raytracer

Experimental CPU based voxel raytracing engine written in Python and based on Pygame. No meshes or textures: Everything is a floating point defined by a material. Materials can define their own functions as custom shaders. Designed for use at low resolutions and frame rates, the ray tracing algorithm is meant to be simple and efficient so expect noise and inaccuracy by design.

![alt text](cover.png)

The code is under the GPL license, created and developed by MirceaKitsune. Execute `python3 ./init.py` to start the engine with the default test scene. Use the mouse to look around with the following keys:

 - `WASDRF`: Move forward, backward, left, right, up, down. `Space` and `Control` can also be used to jump or descend.
 - `Mouse wheel`: Zoom in and out.
 - `Arrows`: Look up, down, left, right.
 - `Tab`: Toggle mouse look and pointer grabbing.
 - `Shift`: Hold to move 5 times faster with the keyboard.

## Features and TODO

  - [x] Mod loader which allows launching the engine with any data package containing its own config and init script.
  - [x] Programmable material functions. Each voxel can hold both unique material properties as well as a function that tells light rays how to behave upon collision.
  - [x] Physically accurate material provided by default. Simulates all basic PBR features such as: Ray reflection and refraction with roughness, plasticity and metalicity with accurate color interactions, translucency and anisotropy with IOR support, density for volumetrics, emission via a ray energy system which supports ambient and sky lighting.
  - [x] Physics system which supports collisions between individual voxels. Physics properties such as weight friction or elasticity are calculated based on interactions with neighboring materials, allowing different surfaces in any object to have their own specific physical behaviors.
  - [ ] Add perlin noise. May be possible to support an object based chunk system for generating infinite terrain.
  - [ ] Create a script to convert image slices into pixel meshes. This will allow importing 3D sprites from 2D images.
  - [ ] Sound support in the form of either audio files or a frequency generator associated with materials. Audio is also intended to be raytraced.

## Settings

Settings are stored within the mod's `config.cfg` file and can be used to modify how the engine behaves. Below is a description of each category and setting:

  - `WINDOW`: Window related settings such as resolution and frame rate.
    - `width`: Number of horizontal pixels, higher values allow more detail but greatly affect performance.
    - `height`: Number of vertical pixels.
    - `scale`: The size of each pixel, acts as a multiplier to width and height.
    - `smooth`: If false pixels are always sharp, if true use a bilinear filter when upscaling to the `scale` factor.
    - `fps`: Target number of frames per second, the end result may be lower or higher based on practical performance. 0 disables the limit and allows the main loop to run as fast as possible. Rendering is suspended when the window isn't focused.
  - `RENDER`: Renderer related settings used by the camera.
    - `sync`: The window waits for all tiles to be ready before blending them to the canvas. If enabled threads will wait for each other, otherwise each thread will update as soon as possible. Disabling resulting in faster perceived performance at the cost of tearing when render threads are slower than the main window.
    - `culling`: Enables occlusion culling and view frustum culling. Reduces the amount of data used by the renderer by only assigning visible chunks to threads, detected based on which chunk positions rays traveled through during the previous trace: This may causing missing content when the camera moves too fast and new chunks are loaded, which can last for a few frames until the paths adjust and all chunks are detected.
    - `static`: Whether to use the pixel index as random noise seed and have a static pattern, alternative to using random noise each frame which produces flickering. Affects material functions and camera effects such as DOF, pixel skipping is not affected and remains random.
    - `samples`: The number of samples to preform per pixel. Values higher than 1 enable multisampling, this makes each CPU thread process more than one image per frame. Looks softer and reduces roughness by doing multiple traces per pixel, but greatly reduces rendering performance as each pixel is traced multiple times.
    - `shutter`: Camera shutter speed. 0 is the minimum setting, 1 is instant and disables motion blur. Causes bright rays to leave trails over darker parts of the image, uses the alpha channel of tile images.
    - `spill`: Emulates color spill for the camera lens by tinting the canvas with its average color. Higher values produce stronger saturation and darkness. Use low values for realistic results.
    - `iris`: Iris adaptation intensity. Dark areas will be brightened or bright areas will be darkened based on the average luminosity of the image.
    - `iris_time`: Iris adaptation speed, the canvas gradually moves toward its target brightness at this rate.
    - `bloom`: Cover and intensity of bloom. 0 disables bloom, 0.5 produces bloom starting from pixels that are halfway bright, 1 blurs the entire image.
    - `bloom_blur`: The bloom pass is downscaled by this amount, roughly represents the radius in pixels for the bloom effect.
    - `falloff`: The amount by which light tapers off with hits, controls overall brightness. 0 is the brightest settings as it makes rays not lose energy between bounces, increasing this offers more vivid colors but also makes the scene darker.
    - `chunk_rate`: Refresh rate for chunk updates in milliseconds. Limits recalculating updates to renderer chunks, camera movement and object physics still work at the normal FPS. Reduces main thread workload and improves overall performance, but moving objects and animated sprites will be updated slower. Note that this acts as a limiter to the sprite animation rate, animated sprites faster than this setting will skip frames.
    - `chunk_size`: The chunk size used by the renderer. Smaller values result in more small boxes holding less data, larger values store fewer frames containing more voxels, eg: Each chunk holds 64 voxels if this is 4 (4 x 4 x 4). Chunk are recalculated when any object touching them moves or changes sprite, large values result in more recalculations thus lower performance. Must be an even number and less than `dist_max`, 16 is recommended for the best performance.
    - `chunk_lod`: Number of LOD steps for chunks. Values above 1 cause chunks that are further from the camera to be stored at a lower resolution. This reduces data and improves performance, but you may see parts of distant objects become blocky or disappear. Must always be lower than `chunk_size`, the larger the draw distance the safer it is to increase this.
    - `fov`: Field of view in degrees, higher values make the viewport wider.
    - `dof`: Depth of field in degrees, higher values result in more randomness added to the initial ray velocity and distance blur.
    - `batches`: Total number of frames it takes to cover all pixels on the screen, only pixels associated with a batch are updated each frame. Must be at least 1 which disables pixel skipping, small values like 2 or 4 are recommended. Improves perceived performance by allowing some pixels to render faster, but produces a noticeable mosaic pattern as other pixels take extra frames to update.
    - `dist_min`: Minimum ray distance, voxels won't be checked until the ray has preformed this number of steps.
    - `dist_max`: Maximum ray distance, calculation stops and ray color is returned after this number of steps have been preformed.
    - `max_light`: Maximum luminosity level, rays are terminated when reaching this energy level. Since dark areas tend to require more bounces, this improves performance with quality loss around brighter surfaces. 1 or more is recommended.
    - `max_bounces`: Maximum number of bounces. 0 uses direct lighting, higher values allow this number of bounces. By default bounces increase the `absorption` material property per hit.
    - `lod_bounces`: Rays terminate faster with each bounce. 0 disables this optimization, at 1 each opaque bounce will half the life of a ray.
    - `lod_samples`: Subsequent samples have a shorter life. At 1 each sample has half the lifetime of the previous one. Boosts performance but may cause reflections and distant objects to fade sooner as well as induce color banding.
    - `lod_edge`: Rays closer to the edge of the canvas start with a lower lifetime and will render fewer samples. Performance is improved by focusing more detail toward the center, at the cost of some detail loss near the edges. Stacks with other performance optimizations that rely on ray life such as `lod_bounces`.
    - `threads`: The number of threads to use for ray tracing by the thread pool, 0 uses all CPU cores. The screen is evenly divided into boxes totaling this amount so that each thread processes a different portion of the canvas. Ensure `width` and `height` are equally divisible to the resulting grid or borders may be appear near the screen edges.
  - `PHYSICS`: Physics related settings including player movement.
    - `gravity`: Global multiplier for gravity. Default is 1, lower values will make physical objects lighter while higher values make them heavier.
    - `friction`: Global multiplier for friction and elasticity. Default is 1, 0 disables friction and bouncing when objects touch.
    - `friction_air`: Global friction applied to all physical objects regardless of collisions. Can be 0 if the environment contains no air or uses air voxels that have friction.
    - `speed_jump`: Jump speed of the player, determines how fast the player moves vertically.
    - `speed_move`: Keyboard movement speed of the player, determines how fast the camera moves when using the movement keys.
    - `speed_mouse`: Mouse rotation speed of the player, determines how fast the camera rotates when moving the mouse in mouselook mode.
    - `max_velocity`: Terminal velocity of objects, represents the maximum allowed velocity and how many units per tick objects can move. Limits excessive speeds and minimizes performance impact for large velocities.
    - `max_pitch`: Maximum pitch angle in degrees, the camera can't look lower or higher than this amount. 0 disables, use a value below 180, 90 is recommended. When set horizontal movement keys won't affect vertical movement and vice versa.
    - `dist_move`: Object logic is suspended for objects further than this distance. Includes physics as well as updates to sprite animation. Limits expensive collision checks as well as updates to renderer chunks from movement or animated sprites, but distant objects will appear frozen.

## Default material settings

A material is registered using the `register_material` call with a list of settings. Below is a list of properties used to customize the default shader function or specify your own, unique properties are supported for use in custom material functions. Materials contain both visual properties that determine interactions with light rays, as well as physical properties controlling how objects collide with each other. Note that materials are global, changes done to a material will be immediately reflected on all voxels with that material.

  - `function`: Material function to call when a ray hits this material, use `material_default` unless you want a custom shader. 
  - `albedo`: The color of this material in RGB format, eg: `255, 127, 0`. Blended to the light ray based on the ray's absorption.
  - `roughness`: This amount of random roughness is added to the ray velocity when reflected or refracted, also controls energy reduction. Blurs reflections, if `density` is enabled this also blurs rays passing through. If the `static` setting is enabled this produces a consistent pattern otherwise high values will cause flickering.
  - `absorption`: The ability of this material to absorb color, 0 acts as a perfect mirror while 1 is a perfect absorbant. Controls both transparency and metalicity: Use with an `ior` under 0.5 to get a transparent surface and over 0.5 for a metallic one. If solid use 1 for plastic, 0.5 for metal, 0 for a mirror... if transparent try 1 for painted glass or 0.25 for fog.
  - `ior`: Amount by which light rays are reflected by or pass through the surface. This isn't an accurate IOR value and named that way for familiarity, it multiplies how much the ray is reflected and acts as the real controller for determining translucency. If the material represents an opaque surface this should be 1 for accurate ray bounces, lower slightly to simulate anisotropy... a value close to 0.5 can be used to send rays inward and encourage subsurface scattering... if transparent it should be well below 0.5 to send light rays through, use a low value to simulate IOR or 0 to leave ray velocity unchanged.
  - `energy`: How much energy this material emits. Use 0 for normal surfaces and increase for voxels that emit light. Can be greater than 1 which may produce over-brightening. A flame can be roughly 1, a standard light bulb 5, the sun 10, etc.
  - `solidity`: Physics property. Random chance that this material will be considered solid. When solid this voxel is checked during physics interactions and collides with voxels in other objects, otherwise this material is ignored by the physics system. Always use 1 for full solids like walls, 0 for non-solids such as fog, while an intermediary value such as 0.25 is ideal for fluids.
  - `weight`: Physics property used exclusively by physical objects, the cumulative value of all voxels on an object determines its overall weight. Makes an object heavier and pulled down faster by gravity, can be negative to make the object rise instead of falling. Does not affect interactions between different physical objects.
  - `friction`: Physics property used in interactions with physical objects, the property on the object's voxels is calculated against those of neighboring voxels. Influences the amount by which the object loses velocity over time when touching other surfaces. Note that no air friction exists by default and the void won't slow objects down: For air resistance create an invisible or fog material with a `solidity` of 0 and give it a small friction value.
  - `elasticity`: Physics property used in interactions with physical objects, the property on the object's voxels is calculated against those of neighboring voxels. Influences the amount by which an object's velocity is reflected when a solid surface is hit. If elasticity is 0 the object stops completely in that axis, if 1 the object will be bounced back at exactly the same speed it hit the surface with.

Note: The number of hits accounted for by the raytracer increases with `ior`, a value of 0 doesn't count as a hit while 1 is a full hit. Low reflectivity reduces bounce based ray termination controlled by the `max_bounces` setting, making rays live longer which may degrade performance if a ray gets stuck bouncing inside a solid. An `ior` of 0 can be used to make volumetric fog, but since fog voxels are processed without reducing ray life this should be done sparingly to avoid performance loss.

## Material programming

The engine allows creating custom materials which can have their own functions telling light rays how to behave. By default each material uses the material_default function located in data.py which can be customized using the settings documented above, it's recommended to use the default material unless you're an advanced user and need a custom shader to do things not supported by the default ray behavior. Note that ray reflections are handled internally by the raytracer for optimal performance, material functions can make other changes to `ray.vel` after the ray has bounced.

A material function takes three parameters: The ray properties, the material we hit, and the system settings. Each function definition should thus be of the form `material_custom(ray, mat, settings)`. See the default material section for the properties of the default material, eg: `mat.albedo` can be used to read color. Custom material settings are allowed for use in custom functions, as are custom ray properties which can be used to store data between ray hits. The function is expected to return the amount by which the interaction counts as a bounce, 0 being fully transparent while 1 is a full solid. The following ray properties are used internally by the raytracer:

  - `color`: The color of the ray independent of energy. If this is the first bounce it will have the pixel color set during the previous frame. Normally you want to mix the material `albedo` color into the ray color.
  - `energy`: The amount of light the ray carries. `color` should be multiplied by this value by the function before being displayed. Starts at 0, by default it decreases with material `absorption` and increases with material `energy`. Energy values lower than 1 leave longer trails when the `shutter` render setting enables motion blur.
  - `pos`: Current ray position. This should not be changed directly unless there's a reason to teleport the ray.
  - `vel`: Current ray velocity. The speed of light is 1, meaning at least one axis must be precisely -1 or +1 while the other two may be anything in that range: `vec3.normalize` is automatically ran after making changes, otherwise values `> abs(1)` will cause voxels to be skipped while values `< abs(1)` can cause the same voxel to be calculated twice!
  - `step`: The number of steps this ray has preformed. 1 is a ray that was just spawned at the camera's minimum draw distance, if `step` equals `life - 1` this is the last move the ray will preform. Only modify this if you want to give the ray a one time boost, change `life` to properly alter the lifetime.
  - `life`: The maximum number of steps this ray can preform before the resulting color is drawn. Starts at `dist_max - dist_min`, modifying this is the recommended way to make ray life shorter or longer.
  - `bounces`: Records the number of times this ray has bounced. The value is checked by the raytracer and incremented based on the return value of the function: The material function should leave this untouched and only use it to check how many bounces were preformed, only modify if you want the engine to think more or less bounces have been preformed. 1 is added for each opaque bounce, values between 0 and 1 are typically added by translucent voxels.
  - `traversed`: Used internally by the render engine, shouldn't need to be accessed or modified. A list of tuple positions for all chunks the ray traveled through: Used for occlusion culling and view frustum culling, only chunks at positionss listed here will be calculated by rays during the next frame.

Background function: In addition to material functions which are executed when the ray touches a voxel, a background function will preform changes to the ray after it has preformed its last step. Set the background variable in the data script to the default or your custom function such as `data.background = builtin.material_background`, if omitted rays hitting the void will be black. Unlike conventional materials the sky function doesn't have settings since only one exists and it operates in place, the only parameters are thus the `ray` and `settings` objects. By default ray energy is applied to the ray color here. There's no point in changing positional ray properties here as this always runs after the last step: You typically want to use velocity to produce a shape at infinite distance based on ray direction.

## Creating a scene

This describes the procedure for setting up a custom scene. The engine is in early development and anything mentioned here is subject to change! The first step is to setup your own mod: Simply create a new directory in the mods folder, it needs to contain your own copy of `config.cfg` as well as an `init.py` script that will execute before the main window is created, simply run the engine with your mod as an argument for example `init.py default` to launch the default world. At the moment sprites can only be painted via code, importing sprites from image slices is a planned feature.

There are 3 main components to a scene: Materials, sprites, objects. Each acts as a subset of the other: Materials are points with unique properties acting as atoms, sprites are 3D textures storing materials located at different points, objects hold a set of sprites which they express in 3D space. The first step is creating one or more materials as described above and customizing their properties to get the types of surface you want, afterward paint a 3D sprite with your materials by adding each one at the correct location to form a shape, lastly create an object and give it the newly painted sprite. Materials and sprites can be retroactively modified with immediate results, always copy when you wish to customize one independently. Below is a simplified example of setting up a basic scene, does not include the mandatory player object which needs to be set in a similar way (see `object.set_camera`).

```
mat = data.Material(function = builtin.material, albedo = rgb(255, 127, 0))
spr = data.Sprite(size = vec3(16, 16, 16), frames = 1, lod = 1)
spr.set_voxels_area(0, vec3(0, 0, 0), vec3(15, 15, 0), mat)
obj = data.Object(pos = vec3(0, 0, 0))
obj.set_sprite(spr)
```

The above will create an orange wall covering the -Z face of the 16x16x16 sprite. Note that the maximum position we can set a voxel at is 15 although the size is 16, the count starts from 0 so 1 must be subtracted. When created sprites are given a number of animation frames, in this case the sprite is static so only one frame was provided. Sprites can also be given a LOD above 1, this allows them to be stored at a lower resolution which improves performance at the cost of detail. The first parameter of `set_voxel` or `set_voxels_area` is the frame we're editing in this case 0.

Below is a list of functions and variables built into each class which are likely to be used when designing your own world. Read the code comments above every definition inside data.py where each class is defined for more technical information on other builtin functions, as well as the default scene for a full example of how everything is set up.

  - `*.copy`: Works on both materials sprites and objects. Returns a copy of the item which can be edited intependently, if not used changes to any reference of an existing instance will be applied to all instances. Duplicating too many items can decrease performance so use this sparingly and only when necessary.
  - `sprite.mix`: Used to mix another sprite with this one, similar to overlaying two transparent images. Empty spaces in the other sprite are ignored and won't override voxels in this sprite, otherwise each material will be copied to this sprite. Both sprites must have the same size on all axes, sprites of different sizes can't be mixed.
  - `sprite.clear`: Removes all voxels from the given frame, use this to empty a frame before painting a new voxel mesh to it.
  - `sprite.set_voxel`: Sets the material at a single voxel position on the given frame of the sprite. For example `set_voxel(0, vec3(0, 0, 0), material)` will cause the first voxel to become that material. `None` can be provided in place of a material to clear the voxel. It's recommended to use `sprite.set_voxels` instead especially if changing more than one voxel.
  - `sprite.set_voxels`: Similar to `set_voxel` but sets a list of voxels instead of a single voxel. Voxels are provided as a dictionary where each material is indexed by tuple position, eg: `voxels[(0, 0, 0)] = material`. For the best performance, this should be called once when creating the sprite with further changes done sparingly and only if necessary.
  - `sprite.set_voxels_area`: A shortcut for `set_voxels` which fills an entire area with the given material. For example `set_voxel_area(0, vec3(0, 0, 0), vec3(15, 15, 15), material)` will fill a 16 x 16 x 16 cube with the material.
  - `sprite.anim_set`: Sets the animation to be played on the sprite. For performance and efficiency, animations aren't named internally but each frame is stored in a single list: You must note and specify your own range to play animations. Example: `anim_set(10, 20, 0.5)` will play frames 10 through 19 at a rate of 500 ms. Note that the last frame will be ignored. Speed can be negative to play the animation backwards or 0 to make the sprite static again.
  - `object.remove`: Use this to permanently delete an object from the world and stop it from being processed. Materials sprites and objects are removed from memory if every reference to them is also deleted.
  - `object.move`: Teleports the object to the given `vec3` position. If you don't plan on changing the position of the object in real time, provide the desired position as an object parameter on init instead.
  - `object.rotate`: Rotates the object by this `vec3` amount. The sprite will be rotated in steps of 90 degrees, only visible if sprite size is equal in the two axes opposite the axis of rotation. Best used for small dynamic objects, if this is a static object rotating the original sprite is preferred.
  - `object.intersects`: Takes two `vec3` parameters, used to check if another point or box is touching or within the bounding box of this object. If both vectors are equal this is a point, otherwise intersection with another bounding box will be checked.
  - `object.set_sprite`: Used to associate an object with a sprite, use after creating objects if they're meant to be rendered. The function takes a single sprite, if None the object will become disabled.
  - `object.set_camera`: Used to bind the camera and input to an object, takes a `vec2` used to indicate the camera offset. This effectively marks the object as the active player: Must be executed on at least one object for rendering and input to work! Only one object at a time may act as the player.
  - `object.function`: Similar to material functions, objects may have a custom function called when the object is updated. If set the function executes after physics for objects within range of the `dist_move` setting. Requires self as an argument, object functions thus take the form `def func(self)`.

  - `object.physics`: If true the physics engine can preform changes to this object. Collisions are checked against all visible objects but only physical objects will be moved.
  - `object.visible`: Read-only boolean, true if the object has a sprite and is within the camera's view range.

Note: The size of a sprite needs to be an even integer for each direction otherwise slices located on edges may be ignored. For instance `6 4 12` is a valid sprite size, however `7 4 12` is invalid and will be automatically enlarged to `8 4 12`. This is due to voxels being located at integer positions while the center of each objects is always in the middle, size must therefore be equally divisible by two to ensure voxels are never 0.5 units away from the object center.

Physics: To make an object physical, give it the `physics` property on init such as `data.Object(pos = vec3(0, 0, 0), physics = True)`. Only do this for objects intended to move, all physical objects are affected by gravity and subject to processing by the physics engine.
