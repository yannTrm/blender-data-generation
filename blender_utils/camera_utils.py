import bpy
from mathutils import Vector

def add_camera(location: Vector = Vector((0, 0, 10)), rotation: Vector = Vector((0, 0, 0))) -> bpy.types.Object:
    """Adds a camera to the scene at the specified location and rotation.

    Args:
        location (Vector): The location of the camera.
        rotation (Vector): The rotation of the camera in radians.

    Returns:
        bpy.types.Object: The created camera object.
    """
    bpy.ops.object.camera_add(location=location, rotation=rotation)
    camera = bpy.context.object
    camera.name = "SceneCamera"
    bpy.context.scene.camera = camera  # Set as active camera

    print(f"✅ Camera added at {location} with rotation {rotation}")
    return camera