import site
import sys

user_site_packages = site.getusersitepackages()
sys.path.append(user_site_packages)

import os
import bpy
import yaml
import math
import random
from mathutils import Vector
import pandas as pd

project_path = os.path.dirname(os.path.abspath(__file__))
if project_path not in sys.path:
    sys.path.append(project_path)
    

from blender_utils.object_utils import center_collection, scale_collection, add_ground_plane, get_collection_bounds
from blender_utils.lighting import add_light_source, setup_shadows_and_reflections
from blender_utils.camera_utils import add_camera
from models.model_loader import load_model
from actions.camera_actions import move_camera, rotate_camera, look_at
from actions.lighting_actions import update_light_intensity, move_light


def clear_scene():
    """Supprime tous les objets de la scène."""
    bpy.ops.object.select_all(action='SELECT')  # Sélectionne tous les objets
    bpy.ops.object.delete(use_global=False)    # Supprime les objets sélectionnés
    
    # Supprime également les matériaux, textures, etc. pour éviter l'accumulation
    for material in bpy.data.materials:
        bpy.data.materials.remove(material)
    for texture in bpy.data.textures:
        bpy.data.textures.remove(texture)
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)

def get_common_car_colors():
    """Returns a list of common car colors in RGBA format."""
    return [
        (1.0, 1.0, 1.0, 1.0),  # White
        (0.0, 0.0, 0.0, 1.0),  # Black
        (0.5, 0.5, 0.5, 1.0),  # Gray Metallic
        (0.75, 0.75, 0.75, 1.0),  # Silver
        (1.0, 0.0, 0.0, 1.0),  # Red
        (0.0, 0.0, 0.5, 1.0),  # Dark Blue
        (0.3, 0.5, 1.0, 1.0),  # Light Blue
        (0.0, 0.3, 0.0, 1.0),  # Dark Green
        (0.9, 0.8, 0.6, 1.0),  # Beige
        (1.0, 0.85, 0.0, 1.0),  # Yellow Taxi
    ]
    
    
def assign_random_car_color():
    """Assigns a random realistic car color to car paint materials."""
    colors = get_common_car_colors()
    chosen_color = random.choice(colors)
    
    for mat in bpy.data.materials:
        if "carpaint" in mat.name.lower():
            mat.use_nodes = True
            bsdf_node = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf_node:
                bsdf_node.inputs[0].default_value = chosen_color
    return chosen_color

def prepare_model(filepath: str, target_size: float = 1.0, collection_name: str = "Vehicle", offset: float = 0.1) -> tuple:
    # Charger le modèle
    vehicle_collection = load_model(filepath, collection_name)
    if not vehicle_collection:
        return None, None, None

    # Centrer et redimensionner le modèle
    center_collection(vehicle_collection, offset)
    scale_collection(vehicle_collection, target_size)
    
    # Configurer l'éclairage, le sol, la caméra, etc.
    min_corner, max_corner, collection_height = get_collection_bounds(vehicle_collection)
    vehicle_center = (min_corner + max_corner) / 2
    vehicle_center.z += collection_height

    light_height = max_corner.z + 10
    light = add_light_source(location=Vector((vehicle_center.x, vehicle_center.y, light_height)), intensity=400, shadow_soft_size=7)

    ground_plane = add_ground_plane(Vector((0, 0, 0)), 0)
    setup_shadows_and_reflections(ground_plane, roughness=0.1, specular=0.9, clearcoat=0.9, clearcoat_roughness=0.1)
    
    # Positionner la caméra
    camera_distance = 2
    camera_height = vehicle_center.z 
    camera = add_camera(location=Vector((vehicle_center.x, (vehicle_center.y + camera_distance), camera_height)))
    look_at(camera, Vector((0,0,0.15)))
    
    # Assigner une couleur aléatoire au véhicule
    chosen_color = assign_random_car_color()
    
    return vehicle_collection, light, camera, chosen_color, vehicle_center





def car_part_segmentation_mask_assign(collection_name: str="Vehicle", file_name: str=""):
    with open("class_gray_levels.yaml", 'r') as file:
        f = yaml.safe_load(file)
    bpy.context.scene.view_layers["ViewLayer"].use_pass_object_index = True
    if collection_name in bpy.data.collections:
        vehicle_collection = bpy.data.collections.get(collection_name)
        for obj in vehicle_collection.objects:
            if obj.name.split('.')[0]  not in f.keys():
                pass
            else:
                obj.pass_index = f[obj.name.split('.')[0]] 
                if obj.active_material:
                    material = obj.active_material
                    if material.use_nodes:
                        bsdf_node = material.node_tree.nodes.get("Principled BSDF")
                        if bsdf_node:
                            bsdf_node.inputs[21].default_value = 1.0 
          
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
            output_node.location = (400, 0)
            output_node.format.color_mode = 'RGB'

            # Link the nodes
            links.new(render_layers.outputs["IndexOB"], bw_node.inputs[0])
            links.new(bw_node.outputs[0], output_node.inputs[0])
    else: 
        return
    return output_node

def render_360(output_folder, key, output_node, radius: float=10, height: float=3, 
               num_frames: int=180, start_frame: int=0,
               data_frame: pd.DataFrame=None, light=None, color=None):
    """
    Renders 360-degree images at 2-degree intervals.
    :param output_folder: Directory to save rendered images.
    :param radius: Distance from object center.
    :param height: Camera height.
    :param num_frames: Number of images to render (default: 180 for 360° at 2° steps).
    """
    camera = bpy.data.objects.get("SceneCamera")
    
    if not camera:
        print("❌ No camera found. Exiting rendering.")
        return
    
    if not os.path.exists(output_folder + "/img"):
        os.makedirs(output_folder + "/img")
    if not os.path.exists(output_folder + "/mask"):
        os.makedirs(output_folder + "/mask")

    for i in range(start_frame, num_frames):
        frame_output = os.path.join(output_folder, f"img/{key}_{i:03d}.png")
        bpy.context.scene.render.filepath = frame_output

        output_node.base_path = output_folder
        output_node.file_slots[0].path = f"mask/{i:03d}_mask_#"

        angle = i * (360 / num_frames)  # Rotate every 2 degrees

        # Compute new camera position using polar coordinates
        x = radius * math.cos(math.radians(angle + 90))
        y = radius * math.sin(math.radians(angle + 90))
        camera.location.x = x
        camera.location.y = y
        camera.location.z = random.uniform(height-0.4, height- 0.3)
        look_at(camera, Vector((0,0,0.15)))
        
        bpy.ops.render.render(write_still=True)
        os.rename(output_folder + "/mask" + f"/{i:03d}_mask_1.png", output_folder + "/mask" + f"/{key}_{i:03d}.png")
        print(f"✅ Rendered frame {i+1}/{num_frames}: {frame_output}")
        
        new_row = pd.DataFrame([{
            'file_name': f"/{key}_{i:03d}.png",
            'folder': os.path.basename(output_folder),
            'x_angle': math.degrees(camera.rotation_euler.x),  
            'y_angle': math.degrees(camera.rotation_euler.y),  
            'z_angle': math.degrees(camera.rotation_euler.z),  
            'color': color,  
            'distance': radius,  
            'height': camera.location.z,  
            'light_intensity': light.data.energy  
        }])

        # Use pd.concat() to append the new row
        data_frame = pd.concat([data_frame, new_row], ignore_index=True)

    return data_frame


    
def get_last_rendered_frame(output_base, key, num_frames):
    """
    Finds the last successfully rendered frame in the output directory.
    Returns the next frame to start from.
    """
    shadow_dir = os.path.join(output_base, "shadow")
    last_frame = -1

    for i in range(num_frames):
        frame_path = os.path.join(shadow_dir, f"{key}_{i:03d}.png")
        if os.path.exists(frame_path):
            last_frame = i

    return last_frame + 1  # Start from the next frame


def process_dataset(dataset_root, output_base, num_frames=8):
    # Parcourir tous les sous-dossiers et fichiers dans dataset_root
    df = pd.DataFrame(columns=['file_name', 'folder', 'x_angle', 'y_angle', 'z_angle', 'color', 'distance', 'height', 'light_intensity'])
    for root, dirs, files in os.walk(dataset_root):
        for file in files:
            if file.endswith(".obj"):
                # Chemin complet du fichier .obj
                obj_path = os.path.join(root, file)
                
                # Créer un dossier de sortie basé sur le nom du sous-dossier (véhicule)
                relative_path = os.path.relpath(root, dataset_root)
                vehicle_output_folder = os.path.join(output_base, relative_path)
                
                # Créer les dossiers de sortie s'ils n'existent pas
                os.makedirs(vehicle_output_folder, exist_ok=True)
                os.makedirs(os.path.join(vehicle_output_folder, "img"), exist_ok=True)
                os.makedirs(os.path.join(vehicle_output_folder, "mask"), exist_ok=True)
                
                # Nom du fichier sans extension (utilisé comme clé)
                key = os.path.splitext(file)[0]
                
                # Vérifier si le rendu est déjà complet
                last_frame_path = os.path.join(vehicle_output_folder, "img", f"{key}_{num_frames-1}.png")
                if os.path.exists(last_frame_path):
                    print(f"✅ Skipping {file}, all frames exist.")
                    continue  # Passer au fichier suivant
                
                # Nettoyer la scène avant de charger un nouveau véhicule
                clear_scene()
                
                # Charger le modèle et préparer la scène
                vehicle_collection, light, camera, chosen_color, vehicle_center = prepare_model(obj_path, target_size=1.0,
                                                                                                collection_name="Vehicle", 
                                                                                                offset=0.01)
                
                #Set up output node
                output_node = car_part_segmentation_mask_assign(file_name="class_gray_levels.yaml")

                if not vehicle_collection:
                    print(f"❌ Failed to load model: {obj_path}")
                    continue
                
                # Trouver la dernière frame rendue
                last_rendered_frame = get_last_rendered_frame(vehicle_output_folder, key, num_frames)
                
                # Rendre les images
                df = render_360(vehicle_output_folder, key, output_node, radius=math.sqrt(1.1), height=vehicle_center.z, 
                           num_frames=num_frames, start_frame=last_rendered_frame, 
                           data_frame=df, light=light, color=chosen_color)

                print(f"✅ Finished processing {file} in {relative_path}")
    df.to_csv(os.path.join(output_base, "metadata.csv"), index=False)
    print("✅ All files processed.")



def main():
    #Clear default objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Select GPU mode
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.preferences.addons["cycles"].preferences.compute_device_type = "CUDA"
    bpy.context.scene.cycles.device = "GPU"
    
    #Transparent Shadow catcher - denoisiing off for 4.0 blender
    bpy.context.scene.cycles.use_denoising = False
    bpy.context.scene.render.film_transparent = True
    
    
    bpy.context.scene.render.resolution_x = 608   # Largeur
    bpy.context.scene.render.resolution_y = 1080  # Hauteur (portrait)

    output_base = "/home/yannou/OneDrive/Documents/deeplearning/data/output"
    dataset_root = "/home/yannou/OneDrive/Documents/deeplearning/data/car_3d"

    process_dataset(dataset_root, output_base, num_frames=8)       
    
if __name__ == "__main__":
    main()
    
    
    
    
    
    
    
    
