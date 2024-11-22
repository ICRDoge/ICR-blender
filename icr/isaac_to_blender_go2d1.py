import numpy as np
import mujoco
from matplotlib import pyplot as plt
from copy import deepcopy


def convert_state():
    # env configs

    exp_name = "dogarm_test"
    file_name = "origin_data/dogarm_test.npy"


    # load the state from the file
    data = np.load(file_name)
    print(data.shape)
    
    timestep = data[:, 0] - data[0, 0]
    qpos = data[:, 1 : 1 + 19 + 6]
    
    xpos = np.zeros((len(timestep), 13+6, 3))
    xquat = np.zeros((len(timestep), 13+6, 4))
    xsite_feet = np.zeros((len(timestep), 4, 3))
    # convert qpos to xpos
    model = mujoco.MjModel.from_xml_path("../model/go2d1.xml")
    data = mujoco.MjData(model)
    FR_foot_id = model.site("FR_foot").id
    FL_foot_id = model.site("FL_foot").id
    RR_foot_id = model.site("RR_foot").id
    RL_foot_id = model.site("RL_foot").id
    for i in range(len(timestep)):
        # run kinematics to get xpos
        data.qpos[:] = qpos[i]
        data.qvel
        mujoco.mj_step(model, data)
        xpos[i] = data.xpos[1:]
        xquat[i] = data.xquat[1:]
        # get feet position
        xsite_feet[i, 0] = data.site_xpos[FR_foot_id]
        xsite_feet[i, 1] = data.site_xpos[FL_foot_id]
        xsite_feet[i, 2] = data.site_xpos[RR_foot_id]
        xsite_feet[i, 3] = data.site_xpos[RL_foot_id]
    # save the xpos and xquat to a file
    np.save(f"blender_input/{exp_name}_xpos.npy", xpos)
    np.save(f"blender_input/{exp_name}_xquat.npy", xquat)
    np.save(f"blender_input/{exp_name}_xsite_feet.npy", xsite_feet)
    print(xquat[500,-1,:])
    # plot xpos[:, 0, [0,2]], xsite_feet[:, 0, [0,2]], xsite_feet[:, 1, [0,2]], xsite_feet[:, 2, [0,2]], xsite_feet[:, 3, [0,2]]
    plt.plot(xpos[:, 0, 0], xpos[:, 0, 2], label="base")
    plt.plot(xsite_feet[:, 0, 0], xsite_feet[:, 0, 2], label="FR_foot")
    plt.plot(xsite_feet[:, 1, 0], xsite_feet[:, 1, 2], label="FL_foot")
    plt.plot(xsite_feet[:, 2, 0], xsite_feet[:, 2, 2], label="RR_foot")
    plt.plot(xsite_feet[:, 3, 0], xsite_feet[:, 3, 2], label="RL_foot")
    plt.plot(xpos[:,-1,0] , xpos[:,-1,2] ,label="ee")
    plt.legend()
    plt.show()


if __name__ == "__main__":
    convert_state()
