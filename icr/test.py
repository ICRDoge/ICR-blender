import os
import sys
sys.path.append("/home/yhy/anaconda3/envs/blender/lib/python3.10/site-packages")

# check if the system is windows, if so, add the path of blender
# if os.name == "nt":
#     packages_path = r"C:\Users\JC-Ba\AppData\Roaming\Python\Python311\Scripts" + r"\\..\\site-packages"
#     sys.path.insert(0, packages_path )
import pickle
import time

import bpy
import matplotlib as mpl
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector
link_mapper = [
    "base",
    # "FR_foot_target",
    "FR_hip",
    "FR_thigh",
    "FR_calf",
    # "FR_foot",
    # "FL_foot_target",
    "FL_hip",
    "FL_thigh",
    "FL_calf",
    # "FL_foot",
    # "RR_foot_target",
    "RR_hip",
    "RR_thigh",
    "RR_calf",
    # "RR_foot",
    # "RL_foot_target",
    "RL_hip",
    "RL_thigh",
    "RL_calf",
    # "RL_foot",
]
# 删除默认 Cube

# if "Cube" in bpy.data.objects:
#     bpy.data.objects.remove(bpy.data.objects["Cube"], do_unlink=True)

def import_animation():
    dt = 0.02
    Hsample = 80
    Nsample = 8
    Ndiffuse = 4
    Ndownsample = 8 # trajectory downsample rate
    Hdownsample = 4 # frame downsample rate

    exp_name = "isaac_test"
    Hrender_start, Hrender_end = [0, 750]


    Hrender = Hrender_end - Hrender_start

    file_prefix = r"/home/yhy/code/legged_rob/dial-mpc/icr/blender_input"

    link_pos_original = np.load(f"{file_prefix}/{exp_name}_xpos.npy")
    # print('test = ',link_pos_original.shape)
    link_quat_wxyz_original = np.load(f"{file_prefix}/{exp_name}_xquat.npy")
    xsite_feet_original = np.load(
        f"{file_prefix}/{exp_name}_xsite_feet.npy"
    )
    link_quat_xyzw_original = link_quat_wxyz_original[:, :, [1, 2, 3, 0]]
    # Nlink = link_pos.shape[1]
    # for i in range(Nlink):
    #     link_pos[:, i, 0] = np.sin(np.arange(Hrollout) * dt + i / Nlink * np.pi / 2)
    #     link_quat_xyzw[:, i, 0] = np.sin(
    #         np.arange(Hrollout) * dt + i / Nlink * np.pi / 2
    #     )
    #     link_quat_xyzw[:, i, 1] = np.cos(
    #         np.arange(Hrollout) * dt + i / Nlink * np.pi / 2
    #     )
    link_pos = np.transpose(link_pos_original, (1, 0, 2))
    link_quat_xyzw = np.transpose(link_quat_xyzw_original, (1, 0, 2))
    xsite_feet = np.transpose(xsite_feet_original, (1, 0, 2))

    # isaac gym is Y-up Right-handed coordinate system
    # blender is  Z-up left-handed coordinate system
    # so we need to convert the quaternion from isaac gym to blender

    yup_to_zup = Euler((np.pi / 2, 0, 0), "XYZ").to_quaternion()
    for obj in bpy.data.objects:
        print(f"Object Name: {obj.name}, Type: {obj.type}")
    for link_idx, (link_pos_traj, link_quat_traj) in enumerate(
        zip(link_pos, link_quat_xyzw)
    ):
        print(f"Progress: {link_idx}/{len(link_mapper)}")
        print(f"Importing {link_mapper[link_idx]}...")
        link_name = link_mapper[link_idx]
        if link_name not in bpy.data.objects:
            print('hahah')
            continue
        blender_obj = bpy.data.objects[link_name]
        for frame_idx, (pos, quat) in enumerate(zip(link_pos_traj[Hrender_start:Hrender_end], link_quat_traj[Hrender_start:Hrender_end])):
            # insert position keyframe
            blender_obj.location = pos
            blender_obj.keyframe_insert("location", frame=frame_idx)
            # change rotation mode to quaternion
            blender_obj.rotation_mode = "QUATERNION"
            # blender's quaternion constructor is in wxyz format
            # insert quaternion keyframe, applying transform
            blender_obj.rotation_quaternion = (
                Quaternion((quat[3], quat[0], quat[1], quat[2])) @ yup_to_zup
            )
            blender_obj.keyframe_insert("rotation_quaternion", frame=frame_idx)

            mesh = bpy.data.meshes.new(f"trace_{frame_idx}")

            if frame_idx > Hrender:
                break







if __name__ == "__main__":
    import_animation()
