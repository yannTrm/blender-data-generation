import bpy
import os
from typing import Optional
from mathutils import Vector


def load_model(filepath: str, collection_name: str = "Vehicle") -> Optional[bpy.types.Collection]:
    """Load a 3D model from the specified filepath and group all objects into a collection.

    Args:
        filepath (str): The path to the 3D model file.
        collection_name (str): The name of the collection to create.

    Returns:
        Optional[bpy.types.Collection]: The created collection containing all objects, or None if loading failed.
    """
    if not filepath.endswith(".obj"):
        print("Only .obj files are supported.")
        return None

    if not os.path.exists(filepath):
        print(f"Error: File '{filepath}' does not exist.")
        return None

    if collection_name in bpy.data.collections:
        bpy.data.collections.remove(bpy.data.collections[collection_name])

    vehicle_collection = bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(vehicle_collection)

    bpy.ops.import_scene.obj(filepath=filepath)

    imported_objects = bpy.context.selected_objects
    for obj in imported_objects:
        for col in obj.users_collection:
            col.objects.unlink(obj) 
        vehicle_collection.objects.link(obj)  

    print(f"Model loaded and grouped into collection '{collection_name}'.")
    return vehicle_collection




