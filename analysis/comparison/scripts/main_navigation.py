"""
Replicating the paper of
'Safety of Dynamical Systems With MultipleNon-Convex Unsafe Sets UsingControl Barrier Functions'
"""
# Author: Lukas Huber
# License: BSD (c) 2021
from dataclasses import dataclass

from math import pi

import numpy as np
from numpy import linalg as LA

import matplotlib.pyplot as plt
from matplotlib import cm

from vartools.states import ObjectPose
from vartools.math import get_numerical_gradient

from dynamic_obstacle_avoidance.obstacles import Obstacle, Ellipse, Sphere
# from dynamic_obstacle_avoidance.containers import ObstacleContainer
from dynamic_obstacle_avoidance.containers import BaseContainer

from dynamic_obstacle_avoidance.visualization.vector_field_visualization import Simulation_vectorFields

from navigation import NavigationContainer


def plot_star_and_sphere_world():
    """ Sphere world & sphere-world."""
    x_lim = [-5, 5]
    y_lim = [-5, 5]

    obstacle_container = NavigationContainer()
    obstacle_container.attractor_position = np.array([0, 5])
    obstacle_container.append(
        Ellipse(
            center_position=np.array([2, 0]), 
            axes_length=np.array([2, 1]),
            )
        )

    obstacle_container.append(
        Ellipse(
            center_position=np.array([-2, 2]), 
            axes_length=np.array([2, 1]),
            orientation=30./180*pi,
            )
        )

    obstacle_container.append(
        Ellipse(
            center_position=np.array([-1, -2.5]), 
            axes_length=np.array([2, 1]),
            orientation=-50./180*pi,
            )
        )

    n_resolution = 50
    # velocities = np.zeros(positions.shape)

    fig, ax = plt.subplots(figsize=(7.5, 6))
    
    for it_obs in range(obstacle_container.n_obstacles):
        obstacle_container[it_obs].draw_obstacle(n_grid=n_resolution)
        boundary_points = obstacle_container[it_obs].boundary_points_global
        ax.plot(boundary_points[0, :], boundary_points[1, :], 'k-')
        ax.plot(obstacle_container[it_obs].center_position[0],
                obstacle_container[it_obs].center_position[1], 'k+')

        boundary_displaced = np.zeros(boundary_points.shape)
        for ii in range(boundary_points.shape[1]):
            boundary_displaced[:, ii] = obstacle_container.transform_to_sphereworld(
                boundary_points[:, ii])
                
            # collisions[ii] = obstacle_container.check_collision(positions[:, ii])
            
        ax.plot(boundary_displaced[0, :], boundary_displaced[1, :], 'b')

        ax.plot(obstacle_container[it_obs].center_position[0],
                obstacle_container[it_obs].center_position[1], 'b+')
            
    ax.set_xlim(x_lim)
    ax.set_ylim(y_lim)

    ax.plot(obstacle_container.attractor_position[0],
            obstacle_container.attractor_position[1], 'k*')
    
    ax.set_aspect('equal', adjustable='box')
    
    plt.ion()
    plt.show()

    # cbar = fig.colorbar(cs, ticks=np.linspace(-10, 0, 11))
    
    # for ii in range(n_resolution):
        # obstacle_container.check_collision(positions[:, ii])
        # n_resolution =
        # pass


def plot_sphere_world_and_nav_function():
    dimension = 2
    x_lim = [-5.5, 5.5]
    y_lim = [-5.5, 5.5]
    
    obstacle_container = NavigationContainer()
    
    obstacle_container.attractor_position = np.array([4.9, 0])

    rot_matr = get_rotation_matrix(rotation=45./180*pi)
    obstacle_container.attractor_position = rot_matr @ np.array([4.9, 0])
    obstacle_container.append(
        Sphere(
            radius=5,
            center_position=np.array([0, 0]),
            is_boundary=True,
            )
        )

    positions_minispheres = [
        [2, 2], [2, -2], [-2, -2], [-2, 2]]

    for pos in positions_minispheres:
        obstacle_container.append(
            Sphere(radius=0.75,
                   center_position=np.array(pos),
                   ))

    obstacle_container.append(
        Sphere(radius=0.5,
               center_position=np.array([0, 0]),
               ))
               
    # obstacle_container.append(
        # Sphere(radius=0.2,
               # center_position=np.array([3, 3]),
               # ))

    plot_obstacles = False
    if plot_obstacles:
        Simulation_vectorFields(
            x_range=x_lim, y_range=y_lim,
            obs=obstacle_container,
            draw_vectorField=False,
            automatic_reference_point=False,
            )
    ####################################
    # FOR DEBUGGING
    obstacle_container.default_kappa_factor = 5
    ####################################
            
    fig, ax = plt.subplots(figsize=(7.5, 6))

    n_grid_surf = 100
    x_vals, y_vals = np.meshgrid(np.linspace(x_lim[0], x_lim[1], n_grid_surf),
                                 np.linspace(y_lim[0], y_lim[1], n_grid_surf))
    positions = np.vstack((x_vals.reshape(1, -1), y_vals.reshape(1, -1)))
    navigation_values = np.zeros(positions.shape[1])
    collisions = obstacle_container.check_collision_array(positions)
    
    for ii in range(positions.shape[1]):
        if collisions[ii]:
            continue
        
        navigation_values[ii] = obstacle_container.evaluate_navigation_function(
            positions[:, ii])

    n_grid = n_grid_surf
    # cs = ax.contourf(positions[0, :].reshape(n_grid, n_grid),
                    # positions[1, :].reshape(n_grid, n_grid),
                    # navigation_values.reshape(n_grid, n_grid),
                    # np.linspace(1e-6, 10.0, 41),
                    # cmap=cm.YlGnBu,
                    # linewidth=0.2, edgecolors='k'
                    # )

    cs = ax.contour(positions[0, :].reshape(n_grid, n_grid),
                    positions[1, :].reshape(n_grid, n_grid),
                    navigation_values.reshape(n_grid, n_grid),
                    levels=41,
                    # levels=np.linspace(1e-6, 5.0, 41),
                    # cmap=cm.YlGnBu,
                    linewidth=0.2, edgecolors='k'
                    )

    n_grid_quiver = 40
    x_vals, y_vals = np.meshgrid(np.linspace(x_lim[0], x_lim[1], n_grid_quiver),
                                 np.linspace(y_lim[0], y_lim[1], n_grid_quiver))
    positions = np.vstack((x_vals.reshape(1, -1), y_vals.reshape(1, -1)))
    velocities = np.zeros(positions.shape)
    collisions = obstacle_container.check_collision_array(positions)
    
    for ii in range(positions.shape[1]):
        if collisions[ii]:
            continue
        velocities[:, ii] = obstacle_container.evaluate_dynamics(positions[:, ii])

        norm_vel = LA.norm(velocities[:, ii])
        if norm_vel:
            velocities[:, ii] = velocities[:, ii] / norm_vel

    show_quiver = True
    if show_quiver:
        ax.quiver(positions[0, :], positions[1, :],
                  velocities[0, :], velocities[1, :], color="black")
    else:
        n_grid = n_grid_quiver
        ax.streamplot(x_vals, y_vals,
                      velocities[0, :].reshape(n_grid, n_grid),
                      velocities[1, :].reshape(n_grid, n_grid), color="blue")

    n_obs_resolution = 50
    for it_obs in range(obstacle_container.n_obstacles):
        obstacle_container[it_obs].draw_obstacle(n_grid=n_obs_resolution)
        boundary_points = obstacle_container[it_obs].boundary_points_global
        ax.plot(boundary_points[0, :], boundary_points[1, :], 'k-')
        ax.plot(obstacle_container[it_obs].center_position[0],
                obstacle_container[it_obs].center_position[1], 'k+')
    
    cbar = fig.colorbar(cs,
                        # ticks=np.linspace(-10, 0, 11)
                        )

    plot_trajcetory = True
    if plot_trajcetory:
        n_traj = 10000
        delta_time = 0.01
        positions = np.zeros((dimension, n_traj))
        start_position = np.array([-3.23, 2.55])
        start_position = np.array([-0.76, 0.93])
        start_position = np.array([-0.59, 1.45])
        
        positions[:, 0] = start_position
        for ii in range(positions.shape[1]-1):
            vel = obstacle_container.evaluate_dynamics(positions[:, ii])
            positions[:, ii+1] = delta_time*vel + positions[:, ii]

            if LA.norm(vel) < 1e-2:
                positions = positions[:, :ii+1]
                print(f"Zero veloctiy - stop loop at it={ii}")
                break

        plt.plot(positions[0, :], positions[1, :], 'r-')
        plt.plot(positions[0, 0], positions[1, 0], 'ro')
            
    ax.set_aspect('equal', adjustable='box')

    ax.set_xlim(x_lim)
    ax.set_ylim(y_lim)

    

if (__name__) == "__main__":
    plt.close('all')
    # plot_star_and_sphere_world()
    plot_sphere_world_and_nav_function()
    print('Done')
    pass
