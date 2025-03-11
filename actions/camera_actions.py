import bpy
from math import radians, sin, cos
from mathutils import Vector
import random


def move_camera(camera: bpy.types.Object, new_location: Vector) -> None:
    """Moves the camera to a new location.

    Args:
        camera (bpy.types.Object): The camera object to move.
        new_location (Vector): The new location for the camera.
    """
    camera.location = new_location
    print(f"✅ Camera moved to {new_location}")

def rotate_camera(camera: bpy.types.Object, new_rotation: Vector) -> None:
    """Rotates the camera to a new rotation.

    Args:
        camera (bpy.types.Object): The camera object to rotate.
        new_rotation (Vector): The new rotation for the camera in radians.
    """
    camera.rotation_euler = new_rotation
    print(f"✅ Camera rotated to {new_rotation}")

def look_at(camera: bpy.types.Object, target: Vector) -> None:
    """Orients the camera to look at a specific target point.

    Args:
        camera (bpy.types.Object): The camera object.
        target (Vector): The target point to look at.
    """
    direction = target - camera.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    camera.rotation_euler = rot_quat.to_euler()
    print(f"✅ Camera oriented to look at {target}")
    

def rotate_camera_around_object(camera: bpy.types.Object, center: Vector, radius: float, angle_step: float = 5.0, noise: float = 2.5) -> int:
    """Rotate the camera around the object and return the current angle.

    Args:
        camera (bpy.types.Object): The camera object.
        center (Vector): The center of the object to rotate around.
        radius (float): The distance from the camera to the object.
        angle_step (float): The angle step in degrees.
        noise (float): The noise to add to the angle in degrees.

    Returns:
        int: The current angle of the camera.
    """
    for angle in range(0, 360, angle_step):
        # Add noise to the angle
        noisy_angle = angle + random.uniform(-noise, noise)
        rad_angle = radians(noisy_angle)

        # Calculate camera position
        x = center.x + radius * cos(rad_angle)
        y = center.y + radius * sin(rad_angle)
        z = center.z  # Keep the camera at the same height as the object

        # Move the camera
        camera.location = Vector((x, y, z))
        look_at(camera, center)

        # Return the current angle for rendering and annotations
        yield angle