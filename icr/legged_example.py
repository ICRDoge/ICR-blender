from legged_gym import LEGGED_GYM_ROOT_DIR
import os

import isaacgym
from legged_gym.envs import *
from legged_gym.utils import  get_args, export_policy_as_jit, task_registry, Logger

import numpy as np
import torch
#! 注意这里设置了一个变量，不然下面调用global的时候会报错
count = 0 
def play(args):
    env_cfg, train_cfg = task_registry.get_cfgs(name=args.task)
    # override some parameters for testing
    env_cfg.env.num_envs = min(env_cfg.env.num_envs, 50)
    env_cfg.terrain.num_rows = 5
    env_cfg.terrain.num_cols = 5
    env_cfg.terrain.curriculum = False
    env_cfg.noise.add_noise = False
    env_cfg.domain_rand.randomize_friction = False
    env_cfg.domain_rand.push_robots = False

    # prepare environment
    env, _ = task_registry.make_env(name=args.task, args=args, env_cfg=env_cfg)
    obs = env.get_observations()
    # load policy
    train_cfg.runner.resume = True
    ppo_runner, train_cfg = task_registry.make_alg_runner(env=env, name=args.task, args=args, train_cfg=train_cfg)
    policy = ppo_runner.get_inference_policy(device=env.device)
    
    # export policy as a jit module (used to run it from C++)
    if EXPORT_POLICY:
        path = os.path.join(LEGGED_GYM_ROOT_DIR, 'logs', train_cfg.runner.experiment_name, 'exported', 'policies')
        export_policy_as_jit(ppo_runner.alg.actor_critic, path)
        print('Exported policy as jit script to: ', path)

    logger = Logger(env.dt)
    robot_index = 0 # which robot is used for logging
    joint_index = 1 # which joint is used for logging
    stop_state_log = 100 # number of steps before plotting states
    stop_rew_log = env.max_episode_length + 1 # number of steps before print average episode rewards
    camera_position = np.array(env_cfg.viewer.pos, dtype=np.float64)
    camera_vel = np.array([1., 1., 0.])
    camera_direction = np.array(env_cfg.viewer.lookat) - np.array(env_cfg.viewer.pos)
    img_idx = 0
    
    to_save = []


    def callback(env):
        global count

        # print(env.episode_length_buf)
        if 1 < env.episode_length_buf < 150 :
            t = np.array([count*env.cfg.sim.dt]) # 记录这一帧的时间
            xpos = env.root_states[0,:3].cpu().numpy()
            xpos[:2] -= env.origin[:2].cpu().numpy() # 在episode=1的时候存一下机器人的初始位置
            quat = env.root_states[0,[6,3,4,5]].cpu().numpy() # w,x,y,z
            jpos = env.dof_pos[0,:12].cpu().numpy()

            save = np.concatenate([t,xpos,quat,jpos])
            to_save.append(save)
        elif env.episode_length_buf == 150 :
            np.save('test.npy', np.array(to_save))
        elif env.episode_length_buf > 150:
            print(np.array(to_save).shape)
        # print(env.episode_length_buf,count,env.cfg.sim.dt)
        count += 1

    for i in range(10*int(env.max_episode_length)):
        actions = policy(obs.detach())
        obs, _, rews, dones, infos = env.step(actions.detach())
        if RECORD_FRAMES:
            if i % 2:
                #print('i=',i)
                filename = os.path.join(LEGGED_GYM_ROOT_DIR, 'logs', train_cfg.runner.experiment_name, 'exported', 'frames', f"{img_idx}.png")
                env.gym.write_viewer_image_to_file(env.viewer, filename)
                img_idx += 1 
        if MOVE_CAMERA:
            camera_position += camera_vel * env.dt
            env.set_camera(camera_position, camera_position + camera_direction)

        if i < stop_state_log:
            logger.log_states(
                {
                    'dof_pos_target': actions[robot_index, joint_index].item() * env.cfg.control.action_scale,
                    'dof_pos': env.dof_pos[robot_index, joint_index].item(),
                    'dof_vel': env.dof_vel[robot_index, joint_index].item(),
                    'dof_torque': env.torques[robot_index, joint_index].item(),
                    'command_x': env.commands[robot_index, 0].item(),
                    'command_y': env.commands[robot_index, 1].item(),
                    'command_yaw': env.commands[robot_index, 2].item(),
                    'base_vel_x': env.base_lin_vel[robot_index, 0].item(),
                    'base_vel_y': env.base_lin_vel[robot_index, 1].item(),
                    'base_vel_z': env.base_lin_vel[robot_index, 2].item(),
                    'base_vel_yaw': env.base_ang_vel[robot_index, 2].item(),
                    'contact_forces_z': env.contact_forces[robot_index, env.feet_indices, 2].cpu().numpy()
                }
            )
        elif i==stop_state_log:
            logger.plot_states()
        if  0 < i < stop_rew_log:
            if infos["episode"]:
                num_episodes = torch.sum(env.reset_buf).item()
                if num_episodes>0:
                    logger.log_rewards(infos["episode"], num_episodes)
        elif i==stop_rew_log:
            logger.print_rewards()

if __name__ == '__main__':
    EXPORT_POLICY = False#True
    RECORD_FRAMES = False
    MOVE_CAMERA = False
    args = get_args()
    play(args)



#上面是play.py的示例

#下面是legged_robot.py里面step函数的改动
from typing import Callable, Dict, List, Optional, Tuple, Union
def step(self, actions,callback: Optional[Callable[[BaseTask],None]] = None):
    """ Apply actions, simulate, call self.post_physics_step()

    Args:
        actions (torch.Tensor): Tensor of shape (num_envs, num_actions_per_env)
    """

    #计算action
    clip_actions = self.cfg.normalization.clip_actions
    self.actions = torch.clip(actions, -clip_actions, clip_actions).to(self.device)
    self.delayed_actions = self.actions.clone().view(self.num_envs, 1, self.num_actions).repeat(1, self.cfg.control.decimation, 1)
    delay_steps = torch.randint(0, self.cfg.control.decimation, (self.num_envs, 1), device=self.device)


    if self.cfg.domain_rand.delay:
        for i in range(self.cfg.control.decimation):
            self.delayed_actions[:, i] = self.last_actions + (self.actions - self.last_actions) * (i >= delay_steps)
    # step physics and render each frame
    self.render()


    if self.episode_length_buf == 1:
        self.origin = self.root_states[0,:3].clone() 


    for _ in range(self.cfg.control.decimation):
        callback(self) if callback is not None else None

        #...
    # ...










