import bpy
from mathutils import Vector

def update_light_intensity(light: bpy.types.Object, new_intensity: float) -> None:
    """Updates the intensity of the light.

    Args:
        light (bpy.types.Object): The light object to update.
        new_intensity (float): The new intensity value.
    """
    light.data.energy = new_intensity
    print(f"✅ Light intensity updated to {new_intensity}")

def move_light(light: bpy.types.Object, new_location: Vector) -> None:
    """Moves the light to a new location.

    Args:
        light (bpy.types.Object): The light object to move.
        new_location (Vector): The new location for the light.
    """
    light.location = new_location
    print(f"✅ Light moved to {new_location}")