import bpy
from mathutils import Vector

def add_light_source(location: Vector = Vector((0, 0, 15)), intensity: float = 400, shadow_soft_size: float = 7) -> bpy.types.Object:
    """Adds a light source at the specified location.

    Args:
        location (Vector): The location of the light source.
        intensity (float): The intensity of the light.
        shadow_soft_size (float): The softness of the shadows.

    Returns:
        bpy.types.Object: The created light object.
    """
    bpy.ops.object.light_add(type='POINT', location=location)
    light = bpy.context.object
    light.data.energy = intensity
    light.name = "KeyLight"
    light.data.shadow_soft_size = shadow_soft_size

    print(f"✅ Light source added at {location}")
    return light


def setup_shadows_and_reflections(plane: bpy.types.Object, roughness: float = 0.1, specular: float = 0.9, clearcoat: float = 0.9, clearcoat_roughness: float = 0.1) -> None:
    """Sets up shadows and reflections on the ground plane.

    Args:
        plane (bpy.types.Object): The ground plane object.
        roughness (float): The roughness of the material.
        specular (float): The specular intensity of the material.
        clearcoat (float): The clearcoat intensity of the material.
        clearcoat_roughness (float): The clearcoat roughness of the material.
    """
    # Create a new material
    new_material = bpy.data.materials.new(name="GroundMaterial")
    new_material.use_nodes = True  # Enable node-based materials

    # Get the Principled BSDF node
    bsdf_node = new_material.node_tree.nodes.get("Principled BSDF")

    if bsdf_node:
        # # Configure material properties - for Blender 4.0
        # bsdf_node.inputs["Roughness"].default_value = roughness
        # bsdf_node.inputs["Specular"].default_value = specular
        # bsdf_node.inputs["Clearcoat"].default_value = clearcoat
        # bsdf_node.inputs["Clearcoat Roughness"].default_value = clearcoat_roughness

        #For 4.3 Blender
        bsdf_node.inputs[2].default_value = roughness
        bsdf_node.inputs[13].default_value = specular
        bsdf_node.inputs[21].default_value = clearcoat
        bsdf_node.inputs[20].default_value = clearcoat_roughness

    plane.data.materials.append(new_material)
    print(f"✅ Shadows and reflections set up on the ground plane.")
    return bsdf_node