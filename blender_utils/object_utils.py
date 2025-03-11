import bpy
from mathutils import Vector

def clear_scene() -> None:
    """Clear all objects, cameras, and lights from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    print("Scene cleared.")
    

def get_collection_bounds(collection: bpy.types.Collection) -> tuple[Vector, Vector]:
    """Compute the bounding box dimensions of all objects in the collection.

    Args:
        collection (bpy.types.Collection): The collection to compute bounds for.

    Returns:
        tuple[Vector, Vector]: The min and max corners of the bounding box.
    """
    min_corner = Vector((float("inf"), float("inf"), float("inf")))
    max_corner = Vector((float("-inf"), float("-inf"), float("-inf")))

    for obj in collection.objects:
        if obj.type == 'MESH':
            bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
            for corner in bbox_corners:
                min_corner = Vector(map(min, min_corner, corner))
                max_corner = Vector(map(max, max_corner, corner))
    collection_height = max_corner.z - min_corner.z
    return min_corner, max_corner, collection_height

def center_collection(collection: bpy.types.Collection, offset: float = 0.0) -> None:
    """Center the collection at the origin (0, 0, 0) and apply an optional offset.

    Args:
        collection (bpy.types.Collection): The collection to center.
        offset (float): The vertical offset to apply after centering.
    """
    min_corner, max_corner, collection_height = get_collection_bounds(collection)
    collection_center = (min_corner + max_corner) / 2

    for obj in collection.objects:
        obj.location -= collection_center
        obj.location.z += offset + collection_height/2 

    print(f"Collection '{collection.name}' centered at origin with offset {offset}.")
    
def apply_transforms(obj):
    """Apply location, rotation, and scale transformations to an object."""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj.select_set(False)
    
def reset_origin_to_geometry(obj):
    """Reset the origin of an object to the center of its geometry."""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    obj.select_set(False)

def scale_collection(collection: bpy.types.Collection, target_size: float = 1.0) -> None:
    """Scale the collection uniformly to fit within a target size.

    Args:
        collection (bpy.types.Collection): The collection to scale.
        target_size (float): The target size for the collection.
    """
    # Reset origin and apply transformations to all objects in the collection
    for obj in collection.objects:
        reset_origin_to_geometry(obj)
        apply_transforms(obj)

    # Calculate the bounding box of the collection
    min_corner, max_corner, _ = get_collection_bounds(collection)
    dimensions = max_corner - min_corner
    print(f"Dimensions before scaling: {dimensions}")

    # Calculate the scale factor
    scale_factor = target_size / max(dimensions) if max(dimensions) > 0 else 1.0
    print(f"Scale factor: {scale_factor}")

    # Apply the scale to each object
    for obj in collection.objects:
        obj.scale = (scale_factor, scale_factor, scale_factor)
        bpy.ops.object.transform_apply(scale=True)  # Apply the scale transformation

    # Verify dimensions after scaling
    min_corner, max_corner, _ = get_collection_bounds(collection)
    dimensions = max_corner - min_corner
    print(f"Dimensions after scaling: {dimensions}")

    print(f"Collection '{collection.name}' scaled to fit within size {target_size}.")
    
    
def add_ground_plane(collection_center: Vector, offset: float = 0.01) -> bpy.types.Object:
    """Adds a ground plane below the collection center.

    Args:
        collection_center (Vector): The center of the collection.
        offset (float): The offset from the lowest point of the collection.

    Returns:
        bpy.types.Object: The created ground plane object.
    """
    bpy.ops.mesh.primitive_plane_add(size=1210, location=(collection_center.x, collection_center.y, collection_center.z - offset))
    plane = bpy.context.object
    plane.name = "GroundPlane"
    plane.is_shadow_catcher = True 
    

    print(f"✅ Ground plane created at {plane.location.z}")
    return plane