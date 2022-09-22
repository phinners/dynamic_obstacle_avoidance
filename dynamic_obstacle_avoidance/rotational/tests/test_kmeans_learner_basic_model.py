"""
Tests (and visualizations) for KmeansMotionLearner and KMeansObstacle.
"""

import sys
import copy
import random
import warnings
import math
from math import pi

import numpy as np
from numpy import linalg as LA

from sklearn.cluster import KMeans

import matplotlib.pyplot as plt

from vartools.handwritting_handler import MotionDataHandler, HandwrittingHandler

from dynamic_obstacle_avoidance.rotational.rotational_avoidance import (
    obstacle_avoidance_rotational,
)

from dynamic_obstacle_avoidance.rotational.kmeans_obstacle import KMeansObstacle
from dynamic_obstacle_avoidance.rotational.kmeans_motion_learner import (
    KMeansMotionLearner,
    create_kmeans_obstacle_from_learner,
)

from dynamic_obstacle_avoidance.rotational.base_logger import logger

from dynamic_obstacle_avoidance.rotational.tests.helper_functions import (
    plot_boundaries,
    plot_normals,
    plot_gamma,
    plot_reference_dynamics,
    plot_trajectories,
    plot_region_dynamics,
    plot_partial_dynamcs_of_four_clusters,
    plot_gamma_of_learner,
)

# fig_dir = "/home/lukas/Code/dynamic_obstacle_avoidance/figures/"
# fig_dir = "figures/"

# Chose figures as either png / pdf
fig_type = ".png"
# fig_type = ".pdf"


def test_surface_position_and_normal(visualize=True):
    """Test the intersection and surface points"""
    datahandler = MotionDataHandler(
        # position=np.array([[-1, 0], [1, 0], [1, 2], [-1, 2]])
        position=np.array([[-1, 0], [1, 0], [2, 1], [1, 2]])
    )

    datahandler.velocity = datahandler.position[1:, :] - datahandler.position[:-1, :]
    datahandler.velocity = np.vstack((datahandler.velocity, [[0, 0]]))
    datahandler.attractor = np.array([0.5, 2])
    datahandler.sequence_value = np.linspace(0, 1, 4)

    dimension = 2
    kmeans = KMeans(init="k-means++", n_clusters=4, n_init=2)
    kmeans.fit(datahandler.position)

    kmeans.n_features_in_ = dimension
    kmeans.cluster_centers_ = (
        np.array(datahandler.position).copy(order="C").astype(np.double)
    )

    radius = 1.5
    region_obstacle = KMeansObstacle(radius=radius, kmeans=kmeans, index=0)

    main_learner = KMeansMotionLearner(datahandler)

    if visualize:
        x_lim, y_lim = [-3, 5], [-2.0, 4.0]

        fig, ax = plt.subplots(figsize=(14, 9))
        main_learner.kmeans = kmeans
        main_learner.region_radius_ = radius
        main_learner.plot_kmeans(x_lim=x_lim, y_lim=y_lim, ax=ax)

        ax.axis("equal")

        for ii in range(kmeans.n_clusters):
            # for ii in [1]:
            tmp_obstacle = KMeansObstacle(radius=radius, kmeans=kmeans, index=ii)
            positions = tmp_obstacle.evaluate_surface_points()
            ax.plot(positions[0, :], positions[1, :], color="black", linewidth=3.5)

        region_obstacle = KMeansObstacle(radius=radius, kmeans=kmeans, index=0)

        ff = 1.2
        # Test normal
        positions = get_grid_points(
            region_obstacle.center_position[0],
            region_obstacle.radius * ff,
            region_obstacle.center_position[1],
            region_obstacle.radius * ff,
            n_points=10,
        )

        normals = np.zeros_like(positions)

        for ii in range(positions.shape[1]):
            if region_obstacle.get_gamma(positions[:, ii], in_global_frame=True) < 1:
                continue

            normals[:, ii] = region_obstacle.get_normal_direction(
                positions[:, ii], in_global_frame=True
            )

            if any(np.isnan(normals[:, ii])):
                breakpoint()

        ax.quiver(
            positions[0, :], positions[1, :], normals[0, :], normals[1, :], scale=15
        )

        ax.axis("equal")

    # region_obstacle = KMeansObstacle(radius=radius, kmeans=kmeans, index=0)
    # Test - somewhere in the middle
    index = index = main_learner.kmeans.predict([[-1, 0]])[0]
    region_obstacle = create_kmeans_obstacle_from_learner(main_learner, index=index)
    position = np.array([2, -1])
    surface_position = region_obstacle.get_point_on_surface(
        position, in_global_frame=True
    )
    assert np.isclose(surface_position[0], 0)

    # Surface point of free space should be equal to the radius
    region_obstacle = create_kmeans_obstacle_from_learner(main_learner, index=index)
    position = np.array([-2, 0])
    surface_position = region_obstacle.get_point_on_surface(
        position, in_global_frame=True
    )
    final_position = region_obstacle.center_position.copy()
    final_position[0] = final_position[0] - region_obstacle.radius
    assert np.allclose(surface_position, final_position)

    position = np.array([2, -1])
    normal_direction = region_obstacle.get_normal_direction(
        position, in_global_frame=True
    )
    # Is in between the two vectors
    assert np.cross([-1, 0], normal_direction) > 0
    assert np.cross([0, 1], normal_direction) < 0

    # Test
    position = np.array([0.25, 0])
    surface_position = region_obstacle.get_point_on_surface(
        position, in_global_frame=True
    )
    assert np.allclose(surface_position, [0, 0])

    normal_direction = region_obstacle.get_normal_direction(
        position, in_global_frame=True
    )
    assert np.allclose(normal_direction, [1, 0])

    # Test 3
    position = np.array([-1, -2])
    surface_position = region_obstacle.get_point_on_surface(
        position, in_global_frame=True
    )
    assert np.allclose(surface_position, [-1, -1.5])

    normal_direction = region_obstacle.get_normal_direction(
        position, in_global_frame=True
    )
    assert np.allclose(normal_direction, [0, -1])


def get_grid_points(mean_x, delta_x, mean_y, delta_y, n_points):
    """Returns grid based on input x and y values."""
    x_min = mean_x - delta_x
    x_max = mean_x + delta_x

    y_min = mean_y - delta_y
    y_max = mean_y + delta_y

    xx, yy = np.meshgrid(
        np.linspace(x_min, x_max, n_points),
        np.linspace(y_min, y_max, n_points),
    )

    return np.array([xx.flatten(), yy.flatten()])


def _test_modulation_values(save_figure=False):
    RANDOM_SEED = 1
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    data = HandwrittingHandler(file_name="2D_Ashape.mat")
    main_learner = KMeansMotionLearner(data)

    fig, ax_kmeans = plt.subplots()
    main_learner.plot_kmeans(ax=ax_kmeans)

    x_lim = ax_kmeans.get_xlim()
    y_lim = ax_kmeans.get_ylim()

    ii = 2
    fig, ax = plt.subplots()

    for ii in range(main_learner.kmeans.n_clusters):
        # Plot a specific obstacle
        region_obstacle = KMeansObstacle(
            radius=main_learner.region_radius_, kmeans=main_learner.kmeans, index=ii
        )

        positions = region_obstacle.evaluate_surface_points()
        ax.plot(positions[0, :], positions[1, :], color="black")
        ax.axis("equal")
        ax.set_xlim(x_lim)
        ax.set_ylim(y_lim)

        ff = 1.2

        # Test normal
        positions = get_grid_points(
            main_learner.kmeans.cluster_centers_[ii, 0],
            main_learner.region_radius_ * ff,
            main_learner.kmeans.cluster_centers_[ii, 1],
            main_learner.region_radius_ * ff,
            n_points=10,
        )

        velocities = np.zeros_like(positions)

        for jj in range(positions.shape[1]):
            if region_obstacle.get_gamma(positions[:, jj], in_global_frame=True) < 1:
                continue

            velocities[:, jj] = main_learner._dynamics[ii].evaluate(positions[:, jj])

        ax.quiver(
            positions[0, :],
            positions[1, :],
            velocities[0, :],
            velocities[1, :],
            scale=15,
        )

        plt.show()

    if save_figure:
        fig_name = "consecutive_linear_dynamics"
        fig.savefig("figures/" + fig_name + fig_type, bbox_inches="tight")
        # fig, axs = plt.subplots(2, 2, figsize=(14, 9))
        # for ii in range(main_learner.kmeans.n_clusters):
        # ax = axs[ii % 2, ii // 2]


def test_gamma_kmeans(visualize=False, save_figure=False):
    """Test the intersection and surface points"""
    # TODO: maybe additional check how well gamma is working
    main_learner = create_four_point_datahandler()

    if visualize:
        x_lim = [-3, 5]
        y_lim = [-2.0, 4.0]

        fig, ax = plt.subplots()
        main_learner.plot_kmeans(ax=ax, x_lim=x_lim, y_lim=y_lim)
        ax.axis("equal")

        if save_figure:
            fig_name = "artificial_four_regions_kmeans"
            fig.savefig("figures/" + fig_name + fig_type, bbox_inches="tight")

        fig, ax = _plot_gamma_of_learner(
            main_learner, x_lim, y_lim, hierarchy_passing_gamma=False
        )

        if save_figure:
            fig_name = "gamma_values_without_transition"
            fig.savefig("figures/" + fig_name + fig_type, bbox_inches="tight")

        fig, ax = _plot_gamma_of_learner(
            main_learner, x_lim, y_lim, hierarchy_passing_gamma=True
        )

        if save_figure:
            fig_name = "gamma_values_with_transition"
            fig.savefig("figures/" + fig_name + fig_type, bbox_inches="tight")

    # Check gamma at the boundary
    index = main_learner.kmeans.predict([[-1, 0]])[0]
    region_obstacle = create_kmeans_obstacle_from_learner(main_learner, index)
    region_obstacle.radius = 1.5

    # Check gamma towards the successor
    position = 0.5 * (
        region_obstacle.center_position
        + main_learner.kmeans.cluster_centers_[region_obstacle.successor_index[0], :]
    )
    gamma = region_obstacle.get_gamma(position, in_global_frame=True)
    assert gamma > 1e9, "Gamma is expected to be very large."

    position = region_obstacle.center_position.copy()
    position[0] = position[0] - region_obstacle.radius
    gamma = region_obstacle.get_gamma(position, in_global_frame=True)
    assert np.isclose(gamma, 1), "Gamma is expected to be close to 1."

    region_obstacle = create_kmeans_obstacle_from_learner(main_learner, 3)
    region_obstacle.radius = 1.5
    position = np.array([1.38, 0.44])
    gamma = region_obstacle.get_gamma(position, in_global_frame=True)
    assert gamma < 1

    index = main_learner.kmeans.predict([[-1, 0]])[0]
    region_obstacle = create_kmeans_obstacle_from_learner(main_learner, index)
    region_obstacle.radius = 1.5

    position = np.array([-1.5, 0])
    gamma = region_obstacle.get_gamma(position, in_global_frame=True)
    assert gamma > 1

    position = np.array([-3.0, -1.6])
    gamma = region_obstacle.get_gamma(position, in_global_frame=True)
    assert gamma < 1

    # Test gammas
    position = np.array([-0.4, -0.1])
    gamma = region_obstacle.get_gamma(position, in_global_frame=True)
    assert gamma > 1

    position[0] = position[0] - region_obstacle.radius * 0.1
    gamma = region_obstacle.get_gamma(position, in_global_frame=True)
    assert gamma > 1e9, "Gamma is expected to be very large."

    # Check inside the obstacle
    position = region_obstacle.center_position.copy()
    position[1] = position[1] + 0.5 * region_obstacle.radius
    gamma = region_obstacle.get_gamma(position, in_global_frame=True)
    assert gamma > 1 and gamma < 10, "Gamma is expected to be in lower positive range."


def test_transition_weight(visualize=False, save_figure=False):
    main_learner = create_four_point_datahandler()
    x_lim, y_lim = [-3, 5], [-1.5, 4.5]

    index = main_learner.kmeans.predict([[1, 0]])[0]
    ind_parent = main_learner.get_predecessors(index)[0]

    if visualize:
        x_lim_test = [-2.5, 2.5]
        y_lim_test = [-1.5, 1.5]

        n_grid = 40
        xx, yy = np.meshgrid(
            np.linspace(x_lim_test[0], x_lim_test[1], n_grid),
            np.linspace(y_lim_test[0], y_lim_test[1], n_grid),
        )
        positions = np.array([xx.flatten(), yy.flatten()])
        weights = np.zeros((main_learner.n_clusters, positions.shape[1]))

        for pp in range(positions.shape[1]):
            weights[:, pp] = main_learner._predict_sequence_weights(
                positions[:, pp], index
            )
        # breakpoint()

        fig, ax = plt.subplots()
        main_learner.plot_kmeans(x_lim=x_lim, y_lim=y_lim, ax=ax)

        fig, ax = plt.subplots()
        main_learner.plot_boundaries(ax=ax)

        levels = np.linspace(0, 1, 11)

        cntr = ax.contourf(
            positions[0, :].reshape(n_grid, n_grid),
            positions[1, :].reshape(n_grid, n_grid),
            weights[index].reshape(n_grid, n_grid),
            levels=levels,
            cmap="cool",
            # alpha=0.7,
        )
        fig.colorbar(cntr)
        ax.axis("equal")
        ax.set_xlim(x_lim)
        ax.set_ylim(y_lim)

        if save_figure:
            fig_name = f"transition_weights_{index}"
            fig.savefig("figures/" + fig_name + fig_type, bbox_inches="tight")

        # Plot normal gamma with parent
        fig, ax = plt.subplots()
        region_obstacle = create_kmeans_obstacle_from_learner(main_learner, index)
        gammas = np.zeros(positions.shape[1])
        for pp in range(positions.shape[1]):
            gammas[pp] = region_obstacle.get_gamma(
                positions[:, pp],
                in_global_frame=True,
                ind_transparent=ind_parent,
            )

        levels = np.linspace(1, 10, 10)
        main_learner.plot_boundaries(ax=ax)
        cntr = ax.contourf(
            positions[0, :].reshape(n_grid, n_grid),
            positions[1, :].reshape(n_grid, n_grid),
            gammas.reshape(n_grid, n_grid),
            levels=levels,
            cmap="cool",
            extend="max",
            # alpha=0.7,
        )
        fig.colorbar(cntr)
        ax.axis("equal")
        ax.set_xlim(x_lim)
        ax.set_ylim(y_lim)

        if save_figure:
            fig_name = f"gamma_values_cluster_{index}"
            fig.savefig("figures/" + fig_name + fig_type, bbox_inches="tight")

    # Weight at transition point
    position = np.array([0, 0])
    weights = main_learner._predict_sequence_weights(position, index)
    expected_weights = np.zeros_like(weights)
    expected_weights[ind_parent] = 1
    # breakpoint()
    # assert np.allclose(weights, expected_weights)
    warnings.warn("Check is deactivated..")

    # Weight behind (inside parent-cluster)
    position = np.array([-0.91, 0.60])
    weights = main_learner._predict_sequence_weights(position, index)
    expected_weights = np.zeros_like(weights)
    expected_weights[ind_parent] = 1
    assert np.allclose(weights, expected_weights)

    # Weight at top border (inside index-cluster)
    position = np.array([0.137, -0.625])
    weights = main_learner._predict_sequence_weights(position, index)
    expected_weights = np.zeros_like(weights)
    expected_weights[index] = 1
    assert np.allclose(weights, expected_weights)

    # Weight at parent center
    position = main_learner.kmeans.cluster_centers_[ind_parent, :]
    weights = main_learner._predict_sequence_weights(position, index)
    expected_weights = np.zeros_like(weights)
    expected_weights[ind_parent] = 1
    assert np.allclose(weights, expected_weights)

    # Weight at cluster center point
    position = main_learner.kmeans.cluster_centers_[index, :]
    weights = main_learner._predict_sequence_weights(position, index)
    expected_weights = np.zeros_like(weights)
    expected_weights[index] = 1
    assert np.allclose(weights, expected_weights)


def test_normals(visualize=False, save_figure=False):
    # TODO: some real test
    main_learner = create_four_point_datahandler()
    x_lim, y_lim = [-3.0, 4.5], [-1.5, 3.5]

    if visualize:
        fig, ax_kmeans = plt.subplots()
        main_learner.plot_kmeans(ax=ax_kmeans, x_lim=x_lim, y_lim=y_lim)
        ax_kmeans.axis("equal")
        ax_kmeans.set_xlim(x_lim)
        ax_kmeans.set_ylim(y_lim)

        if save_figure:
            fig_name = "kmeans_shape"
            fig.savefig("figures/" + fig_name + fig_type, bbox_inches="tight")

        fig, axs = plt.subplots(2, 2, figsize=(14, 9))
        for ii in range(main_learner.kmeans.n_clusters):
            ax = axs[ii % 2, ii // 2]

            main_learner.plot_kmeans(ax=ax, x_lim=x_lim, y_lim=y_lim)

            # Plot a specific obstacle
            region_obstacle = KMeansObstacle(
                radius=main_learner.region_radius_, kmeans=main_learner.kmeans, index=ii
            )

            ff = 1.2
            # Test normal
            positions = get_grid_points(
                main_learner.kmeans.cluster_centers_[ii, 0],
                main_learner.region_radius_ * ff,
                main_learner.kmeans.cluster_centers_[ii, 1],
                main_learner.region_radius_ * ff,
                n_points=10,
            )

            normals = np.zeros_like(positions)

            for ii in range(positions.shape[1]):
                if (
                    region_obstacle.get_gamma(positions[:, ii], in_global_frame=True)
                    < 1
                ):
                    continue

                normals[:, ii] = region_obstacle.get_normal_direction(
                    positions[:, ii], in_global_frame=True
                )

                if any(np.isnan(normals[:, ii])):
                    breakpoint()

            ax.quiver(
                positions[0, :], positions[1, :], normals[0, :], normals[1, :], scale=15
            )
            ax.axis("equal")

        if save_figure:
            fig_name = "kmeans_obstacles_multiplot_normal"
            fig.savefig("figures/" + fig_name + fig_type, bbox_inches="tight")


def create_four_point_datahandler(RANDOM_SEED=1) -> KMeansMotionLearner:
    """Helper function to create handler"""
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    datahandler = MotionDataHandler(
        position=np.array([[-1, 0], [1, 0], [2, 1], [1, 2]])
    )
    datahandler.velocity = datahandler.position[1:, :] - datahandler.position[:-1, :]
    datahandler.velocity = np.vstack((datahandler.velocity, [[0, 0]]))
    datahandler.attractor = np.array([0.5, 2])
    datahandler.sequence_value = np.linspace(0, 1, 4)

    return KMeansMotionLearner(datahandler, radius_factor=0.55)


if (__name__) == "__main__":
    plt.ion()
    plt.close("all")

    # test_surface_position_and_normal(visualize=True)
    # test_gamma_kmeans(visualize=True, save_figure=False)
    # test_transition_weight(visualize=True, save_figure=False)
    # test_normals(visualize=True)

    # _test_evaluate_partial_dynamics(visualize=True, save_figure=True)

    # _test_local_deviation(save_figure=True)

    print("Tests finished.")