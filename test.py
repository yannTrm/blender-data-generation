import bpy
import os
from mathutils import Vector
import mathutils
import math

def process_model_for_shadow(model3d_path, background_path, output_path, key, target_size = (2.0, 2.0, 2.0), cam_radius:float = 10, cam_height:float = 3, num_frames:int = 8):

    # 🔥 Step 1: Delete Everything (Objects, Cameras, Lights)
    clear_objects()
    # 🔥 Step 2: Create "main_object" Collection and Move Imported Objects
    collection_name = "main_object"

    # Remove the collection if it already exists
    if collection_name in bpy.data.collections:
        bpy.data.collections.remove(bpy.data.collections[collection_name])

    # 🔥 Step 3: Set Render Engine to CYCLES
    bpy.context.scene.render.engine = "CYCLES"

    # Ensure GPU or CPU rendering
    bpy.context.preferences.addons["cycles"].preferences.compute_device_type = "OPTIX"
    bpy.context.scene.cycles.device = "GPU"

    # 🔥 Step 4: Import 3D Model (.OBJ only)
    obj_path = model3d_path
    bpy.ops.wm.obj_import(filepath=obj_path)
    print(f"✅ Imported OBJ file: {obj_path}")

    # Create new collection
    main_collection = bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(main_collection)

    # Move all imported objects to "main_object" collection
    for obj in bpy.context.selected_objects:
        for col in obj.users_collection:  # Find all collections the object is in
            col.objects.unlink(obj)  # Remove from the current collection
        main_collection.objects.link(obj)  # Add to "main_object"

    print(f"✅ Moved all imported objects to collection: {collection_name}")

    scale_collection_to_fit(main_collection, target_size)

    # 🔥 Step 5: Set a plane under the "main_object" collection
    plane, collection_center = add_background_and_centerlize(background_path = background_path, collection_name="main_object", cam_height=cam_height, cam_radius=cam_radius, offset=0.01)
    # 🔥 Step 6: Add a light source
    add_light_source()

    # 🔥 Step 7: Add Camera at a fixed height
    camera = add_camera(collection_center, radius=cam_radius, height=cam_height)

    # 🔥 Step 8: Disable Transparent Shadows
    bpy.context.scene.render.film_transparent = True

    #Select objs in main_object
    bpy.context.scene.view_layers["ViewLayer"].use_pass_object_index = True
    bpy.ops.object.select_all(action='DESELECT')
    for obj in main_collection.objects:
        obj.pass_index = 255

    bpy.context.scene.use_nodes = True
    tree = bpy.context.scene.node_tree
    nodes = tree.nodes
    links = tree.links

    # Remove existing nodes
    for node in nodes:
        nodes.remove(node)

    # Add Render Layers node
    render_layers = nodes.new(type="CompositorNodeRLayers")
    render_layers.location = (0, 0)

    # Add a divide
    bw_node = nodes.new(type="CompositorNodeMath")
    bw_node.operation = 'DIVIDE'
    bw_node.inputs[1].default_value = 255
    bw_node.location = (200, 0)

    # Add a output node (Final Output)
    output_node = nodes.new(type="CompositorNodeOutputFile")
    output_node.base_path = output_path
    output_node.location = (400, 0)
    output_node.format.color_mode = 'BW'
    output_node.file_slots[0].path = "mask_#"

    # Link the nodes
    links.new(render_layers.outputs["IndexOB"], bw_node.inputs[0])
    links.new(bw_node.outputs[0], output_node.inputs[0])
    

    # Create a new material
    new_material = bpy.data.materials.new(name="MyMaterial")
    new_material.use_nodes = True  # Enable node-based materials

    # Get the Principled BSDF node
    bsdf_node = new_material.node_tree.nodes.get("Principled BSDF")

    if bsdf_node:
        # Set Roughness (input index 2 corresponds to roughness)
        bsdf_node.inputs[2].default_value = 0.1
        bsdf_node.inputs[19].default_value = 0.9
        bsdf_node.inputs[21].default_value = 12
        print("✅ Roughness set to 0.1")
    else:
        print("❌ Principled BSDF node not found!")

    plane.data.materials.append(new_material)

    # 🔥 Step 9: Render 360° images
    render_360(output_path, key, output_node, radius=cam_radius, height=cam_height, num_frames=num_frames, mode="shadow")
    return

def render_360(output_folder, key, output_node, radius: float=10, height: float=3, num_frames: int=180, mode: str=""):
    """
    Renders 360-degree images at 2-degree intervals.
    :param output_folder: Directory to save rendered images.
    :param radius: Distance from object center.
    :param height: Camera height.
    :param num_frames: Number of images to render (default: 180 for 360° at 2° steps).
    """
    camera = bpy.data.objects.get("RenderCamera")
    if not camera:
        print("❌ No camera found. Exiting rendering.")
        return
    if mode == "render":
        if not os.path.exists(output_folder + "/shadow"):
            os.makedirs(output_folder + "/shadow")
        if not os.path.exists(output_folder + "/mask"):
            os.makedirs(output_folder + "/mask")

        for i in range(num_frames):
            frame_output = os.path.join(output_folder, f"shadow/{key}_{i:03d}.png")
            bpy.context.scene.render.filepath = frame_output

            output_node.file_slots[0].path = f"mask/{i:03d}_mask_#"
            bpy.ops.render.render(write_still=True)
            os.rename(output_folder + "/mask" + f"/{i:03d}_mask_1.png", output_folder + "/mask" + f"/{key}_{i:03d}.png")
            print(f"✅ Rendered frame {i+1}/{num_frames}: {frame_output}")

            angle = i * (360 / num_frames)  # Rotate every 2 degrees

            # Compute new camera position using polar coordinates
            x = radius * math.cos(math.radians(angle))
            y = radius * math.sin(math.radians(angle))
            camera.location = (x, y, height)
        return
    elif mode == "shadow":
        if not os.path.exists(output_folder + "/rshadow"):
            os.makedirs(output_folder + "/rshadow")
        for i in range(num_frames):
            frame_output = os.path.join(output_folder, f"rshadow/{key}_{i:03d}.png")
            bpy.context.scene.render.filepath = frame_output
            bpy.ops.render.render(write_still=True)
            angle = i * (360 / num_frames)  # Rotate every 2 degrees

            # Compute new camera position using polar coordinates
            x = radius * math.cos(math.radians(angle))
            y = radius * math.sin(math.radians(angle))
            camera.location = (x, y, height)
        return
    elif mode == "noshadow":
        if not os.path.exists(output_folder + "/noshadow"):
            os.makedirs(output_folder + "/noshadow")
        for i in range(num_frames):
            frame_output = os.path.join(output_folder, f"noshadow/{key}_{i:03d}.png")
            bpy.context.scene.render.filepath = frame_output
            bpy.ops.render.render(write_still=True)
            print(f"✅ Rendered noshadow frame {i+1}/{num_frames}: {frame_output}")
            angle = i * (360 / num_frames)  # Rotate every 2 degrees

            # Compute new camera position using polar coordinates
            x = radius * math.cos(math.radians(angle))
            y = radius * math.sin(math.radians(angle))
            camera.location = (x, y, height)
        return

def clear_objects():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    print("🔥 Deleted all objects, cameras, and lights.")
    return

def add_background_and_centerlize(background_path=None, collection_name:str="", cam_radius:float=10, cam_height:float=3, offset:float=0.01):
    """
    Adds a background object or a plane below the lowest point of all objects in a collection.
    :param background_path: Path to the background 3D model (if provided), otherwise creates a plane.
    :param collection_name: The name of the main object collection.
    :param plane_size: Size of the plane (if created).
    :param offset: Small gap between the object and the plane.
    """
    collection = bpy.data.collections.get(collection_name)
    if not collection:
        print(f"❌ Collection '{collection_name}' not found.")
        return
    
    objects = [obj for obj in collection.objects if obj.type == "MESH"]
    if not objects:
        print(f"❌ No mesh objects found in collection '{collection_name}'.")
        return
    
    # Find bounding box center of all objects
    min_corner = Vector((float("inf"), float("inf"), float("inf")))
    max_corner = Vector((float("-inf"), float("-inf"), float("-inf")))

    # Find the lowest Z-point using the bounding box
    min_z = float("inf")

    for obj in objects:
        for v in obj.bound_box:  # Bounding box in local space
            world_v = obj.matrix_world @ Vector(v)
            min_z = min(min_z, world_v.z)  # Get lowest Z-value
            min_corner = Vector(map(min, min_corner, world_v))
            max_corner = Vector(map(max, max_corner, world_v))

    if min_z == float("inf"):
        print(f"❌ Could not determine lowest point for '{collection_name}'.")
        return

    print(f"✅ Lowest Z-point in collection '{collection_name}': {min_z}")

    # Compute collection center
    collection_center = (min_corner + max_corner) / 2
    print(f"✅ Collection '{collection_name}' Center: {collection_center}")
    bpy.ops.mesh.primitive_plane_add(size=1210, location=(collection_center.x, collection_center.y, min_z - offset))
    plane = bpy.context.object
    plane.location -= collection_center
    plane.name = "GroundPlane"
    plane.is_shadow_catcher = True  # Make it a shadow catcher
    print(f"✅ Created ground plane at {plane.location.z}")
    print(f"✅ Created background.")

    # Move all objects to center the collection at (0,0,0)
    for obj in objects:
        obj.location -= collection_center

    print(f"✅ Moved '{collection_name}' to (0,0,0)")
    return plane, (collection_center.x, collection_center.y, min_z - offset)

def add_light_source(location=(0, 0, 15)):
    """
    Adds a point light source at the specified location.
    """
    intensity = 400
    bpy.ops.object.light_add(type='POINT', location=location)
    light = bpy.context.object
    light.data.energy = intensity
    light.name = "KeyLight"
    light.data.shadow_soft_size = 7

    print(f"✅ Added Point Lights")
    
def add_camera(collection_center, radius:float=8, height:float=3):
    """
    Adds a camera at a set height (z) and a fixed radius (y), rotating around the object.
    """
    bpy.ops.object.camera_add(location=(0, -radius, height))
    camera = bpy.context.object
    camera.name = "RenderCamera"

    # Make the camera look at (0, 0, 0)
    camera_constraint = camera.constraints.new(type='TRACK_TO')
    camera_constraint.target = bpy.data.objects.new("CameraTarget", None)
    bpy.context.scene.collection.objects.link(camera_constraint.target)
    camera_constraint.target.location = collection_center
    camera_constraint.track_axis = 'TRACK_NEGATIVE_Z'
    camera_constraint.up_axis = 'UP_Y'

    bpy.context.scene.camera = camera  # Set as active camera
    print(f"✅ Added Camera at Radius {radius}, Height {height}, Looking at (0,0,0)")
    return camera

def get_collection_bounds(collection):
    """Compute the bounding box dimensions of all objects in the collection."""
    min_corner = mathutils.Vector((float("inf"), float("inf"), float("inf")))
    max_corner = mathutils.Vector((float("-inf"), float("-inf"), float("-inf")))

    for obj in collection.objects:
        if obj.type == 'MESH':  # Only consider mesh objects
            # Get object bounding box in world coordinates
            bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
            
            # Update min/max bounds
            for corner in bbox_corners:
                min_corner.x = min(min_corner.x, corner.x)
                min_corner.y = min(min_corner.y, corner.y)
                min_corner.z = min(min_corner.z, corner.z)

                max_corner.x = max(max_corner.x, corner.x)
                max_corner.y = max(max_corner.y, corner.y)
                max_corner.z = max(max_corner.z, corner.z)

    return min_corner, max_corner

def scale_collection_to_fit(collection, target_size=(1.0, 1.0, 1.0)):
    """Scales all objects in a collection to fit within a bounding box size while maintaining aspect ratio."""
    
    min_corner, max_corner = get_collection_bounds(collection)
    current_size = max_corner - min_corner

    # Compute scale factor
    scale_factors = [target_size[i] / current_size[i] if current_size[i] > 0 else 1.0 for i in range(3)]
    uniform_scale = min(scale_factors)  # Maintain aspect ratio

    # Apply uniform scale to all objects in the collection
    for obj in collection.objects:
        if obj.type == 'MESH':  # Only scale mesh objects
            obj.scale *= uniform_scale
            bpy.ops.object.transform_apply(scale=True)

    print(f"Scaled collection '{collection.name}' with factor: {uniform_scale}")


# Function to iterate through dataset and process 3D models
def process_dataset(dataset_root, output_base, target_size, num_frames = 8):
    for root, dirs, files in os.walk(dataset_root):
        for file in files:
            if file.endswith(".obj"):
                model3d_path = os.path.join(root, file)
                background_path = None
                
                # Get relative path and create a corresponding output folder
                relative_path = os.path.relpath(root, dataset_root) 
                key =  relative_path.replace("/", "_")
                # Call the processing functions
                process_model_for_shadow(model3d_path, background_path, output_base, key, target_size, cam_radius=10, cam_height=3, num_frames=num_frames)
                # process_model_for_mask_and_render(model3d_path, background_path, output_base, key, target_size, cam_radius=10, cam_height=3, num_frames=num_frames)
                # process_model_no_shadow_render(model3d_path, background_path, output_base, key, target_size, cam_radius=10, cam_height=3, num_frames=num_frames)
                return


# Run the dataset processing
dataset_root = "/Users/dattrongnguyen/Documents/3dmodels"
output_base = "/Users/dattrongnguyen/Documents/blenderTest/train"
target_size=(4, 4, 4)
num_frames = 2

process_dataset(dataset_root, output_base, target_size, num_frames)

