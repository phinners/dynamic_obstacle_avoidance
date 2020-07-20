#!/USSR/bin/python3
'''
Container encapsulates all obstacles.
Gradient container finds the dynamic reference point through gradient descent.
'''

from dynamic_obstacle_avoidance.obstacle_avoidance.obs_common_section import *
from dynamic_obstacle_avoidance.obstacle_avoidance.obs_dynamic_center_3d import *
from dynamic_obstacle_avoidance.obstacle_avoidance.obstacle_container import ObstacleContainer
from dynamic_obstacle_avoidance.obstacle_avoidance.angle_math import *
from dynamic_obstacle_avoidance.obstacle_avoidance.modulation import get_reference_weight

__author__ = "LukasHuber"
__date__ =  "2020-06-30"
__email__ =  "lukas.huber@epfl.ch"

import warnings, sys
import numpy as np
# if not sys.version_info>(3,0): # Python 2
    # import pdb; pdb.set_trace()
    # import itertools.zip as izip


class GradientContainer(ObstacleContainer):
    '''Obstacle Container which can be used with gradient search. It additionally stores 
    the closest boundary point between obstacles. '''
    def __init__(self, obs_list=None):
        if sys.version_info>(3,0): # Python 3
            super().__init__(obs_list)
        else: # Python 2 compatibility
            super(ObstacleContainer, self).__init__(obs_list)

        self._obstacle_is_updated = np.ones(self.number , dtype=bool)

        if len(self):
            self._boundary_reference_points = np.zeros((self.dim, len(self), len(self)))
            self._distance_matrix = DistanceMatrix(n_obs=len(self))
        else:
            self._boundary_reference_points = None
            self._distance_matrix = None

    def append(self, value): # Compatibility with normal list.
        ''' Add new obstacle to the end of the container. '''
        # self._obstacle_list.append(value)
        
        # if value.is_boundary:
        #     if not self.index_wall is None:
        #         warnings.warn("Two wall obstacles in container.")
        #     self.index_wall = len(self._obstacle_list)-1
        if sys.version_info>(3,0): # Python 3
            super().append(value)
        else: # Python 2 compatibility
            super(ObstacleContainer, self).append(value)
        

        if len(self)==1:
            self._boundary_reference_points = np.zeros((self.dim, len(self), len(self)))
            self._distance_matrix = DistanceMatrix(n_obs=len(self))
        else:
            
            self._boundary_reference_points = np.dstack(( np.zeros((self.dim, len(self), 1)), np.hstack((self._boundary_reference_points, np.zeros((self.dim, 1, len(self)-1))))  ))

            new_dist_matr = DistanceMatrix(n_obs=len(self))
            for ii in range(len(self)-1):
                for jj in range(ii+1, len(self)-1):
                    new_dist_matr[ii, jj] = self._distance_matrix[ii, jj]
                    
            self._distance_matrix = new_dist_matr

    def get_distance(self, ii, jj=None):
        '''Distance between obstacles ii and jj'''
        dist = self._distance_matrix[ii, jj]
        
        return -1 if (dist is None or dist<0) else dist
    
    def set_distance(self, ii, jj, value):
        '''Distance between obstacles ii and jj'''
        self._distance_matrix[ii, jj] = value
        
    def reset_obstacles_have_moved(self):
        ''' Resets obstacles in list such that they have NOT moved.'''
        for obs in self._obstacle_list:
            obs.has_moved = False

    def reset_reference_points(self):
        ''' Set the reference points at the center of the obstacle to not 
        interfer with any evaluation.'''
        for obs in self._obstacle_list:
            obs.set_reference_point(np.zeros(obs.dim), in_global_frame=False)

    def get_if_obstacle_is_updated(self, ii):
        return self._obstacle_is_updated[ii]

    def get_boundary_reference_point(self, ii, jj):
        """ Closest point on boundary of obstacle ii with respect to obstacle jj """
        value = self._boundary_reference_points[:, ii, jj]
        return self[ii].transform_relative2global(value)
        # return self._boundary_reference_points[ii, jj]

    def set_boundary_reference_point(self, ii, jj, value):
        """ Closest point on boundary of obstacle ii with respect to obstacle jj """
        value = self[ii].transform_global2relative(value)
        self._boundary_reference_points[:, ii, jj] = value
    
    def get_dynamic_reference_points(self, ii):
        raise NotImplementedError("TODO!") # TODO:
    
    def update_reference_points(self):
        """Update the reference point for all obstacles stored in (this) 
        container based on distance"""

        self.intersection_matrix = Intersection_matrix(len(self))
        
        self.reset_reference_points()
        self.update_boundary_reference_points(self)

        obs_reference_size = np.zeros(len(self))

        for ii in range(len(self)):
            obs_reference_size[ii] = self[ii].get_reference_length()

        for ii in range(len(self)):
            # Boundaries have constant center
            if self[ii].is_boundary:
                continue
            
            distances = np.zeros(len(self))
            for jj in range(len(self)):
                if ii==jj:
                    # DistanceMatrix[ii, jj] = \
                    distances[jj] = -1
                else:
                    # DistanceMatrix[ii, jj] =
                    distances[jj] = self.get_distance(ii, jj)

            weights = get_reference_weight(distances, obs_reference_size)

                
            if np.sum(weights):
                reference_point = np.zeros(self[ii].dim)
                for jj in range(len(self)):
                    if ii==jj:
                        continue
                    
                    ref = self.get_boundary_reference_point(ii, jj)
                    reference_point = (reference_point 
                                       + self[ii].transform_global2relative(ref)*weights[jj])
                self[ii].set_reference_point(reference_point, in_global_frame=False)
                
            else:
                self[ii].set_reference_point(np.zeros(self[ii].dim), in_global_frame=False)

        # TODO: create a more smooth transition between 'free' obstacles and 'clustered ones'
        # TODO: include the 'extended' hull as a deformation parameter
        
        # Combine reference points of obstacles in each cluster
        intersection_err = 1e-9
        
        intersecting_obs = get_intersection_cluster(self.intersection_matrix, self)
        self.assign_sibling_groups(intersecting_obs)

        if False: # Repetition
        # for cluster_intersecting in intersecting_obs:
            weight_obs = np.zeros(len(cluster_intersecting))
            ref_points_obs = np.zeros((self.dim, len(cluster_intersecting)))

            for oo, ii in zip(cluster_intersecting, range(len(cluster_intersecting))):
                ref_points_obs[:, ii] = self[oo].center_position
                weight_obs[ii] = self[oo].get_reference_length()

            weight_obs = weight_obs/np.sum(weight_obs)

            ref_point = np.sum(ref_points_obs * np.tile(weight_obs, (self.dim, 1)), axis=1)
            
            for oo in cluster_intersecting:
                self[oo].set_reference_point(ref_point, in_global_frame=True)

        # Indicate that no obstacle has moved (since last reference-point search).
        self.reset_obstacles_have_moved()

        
    def update_boundary_reference_points(self, max_it=100, convergence_err=1e-3, contact_err=1e-3, step_size=2):
        ''' Boundary reference point refers to the closest point on the obstacle surface 
        to another obstacle. '''
        
        dim = self[0].dim
        if dim<2:
            raise ValueError("No obstacle avoidance possible in d=2.")

        # Compare two (2) obstacles to each other
        n_com = 2

        # Iterate over all obstacles (but last element, because nothing to compare to)
        for ii in range(len(self)-1):
            for jj in range(ii+1, len(self)):
                # Only update if either of the obstacles has 'moved/updated' previously
                if not (self[ii].has_moved or self[jj].has_moved):
                    continue

                center_dists = np.zeros((self.dim, n_com))
                center_dists[:, 1] = self[ii].center_position-self[jj].center_position
                
                if self[jj].is_boundary:
                    # If compare to the boundary, then the obstacle has to look outwards (wall)
                    center_dists[:, 0] = center_dists[:, 1]
                else:
                    center_dists[:, 0] = (-1)*center_dists[:, 1]
                    
                if np.linalg.norm(center_dists[:, 0])>1e10 and not self.is_boundary:
                    # TODO: Check & Test this exception!
                    self.set_distance(ii, jj, 0)
                    self.intersection_matrix[ii, jj] = self[ii].center_position
                    continue
                
                elif self.get_distance(ii, jj) < 0:
                    is_close_for_the_first_time = True
                    
                else:
                    is_close_for_the_first_time = False

                angles = np.zeros((dim-1)*2)
                surf_points = np.zeros((dim, 2))
                
                # Gamma based descent
                if is_close_for_the_first_time:
                    surf_points[:, 0] = self[ii].get_local_radius_point(direction=center_dists[:, 0], in_global_frame=True)
                        
                    surf_points[:, 1] = self[jj].get_local_radius_point(direction=center_dists[:, 1], in_global_frame=True) 
                        
                else:
                    surf_points[:, 0] = self.get_boundary_reference_point(ii, jj)
                    surf_points[:, 1] = self.get_boundary_reference_point(jj, ii)

                # Check if any of the surface points is inside the other object
                margin = 1e-4
                if ((self[ii].get_gamma(surf_points[:, 1], in_global_frame=True)<=1+margin
                    or self[jj].get_gamma(surf_points[:, 0], in_global_frame=True)<=1+margin)
                ):
                    # The obstacle is intersecting
                    print("Touching initially -- Gamma Descent")

                    self[ii].get_gamma(surf_points[:, 1], in_global_frame=True)

                    reference_point = self.gamma_gradient_descent(
                        self[ii], self[jj], common_point=np.mean(surf_points, axis=1))

                    # Set the boundary reference point on for the obstacle-pair
                    self.set_boundary_reference_point(ii, jj, reference_point)
                    self.set_boundary_reference_point(jj, ii, reference_point)
                    self.intersection_matrix[ii, jj] = reference_point
                    self.set_distance(ii, jj, 0)
                    
                else:
                    NullMatrices = np.zeros((n_com, dim, dim))
                    NullMatrices[0, :, :] = get_orthogonal_basis(center_dists[:, 0])
                    NullMatrices[1, :, :] = get_orthogonal_basis(center_dists[:, 1])

                    # Get angles and do iteration
                    if not is_close_for_the_first_time:
                        for kk, obstacle in zip(range(2), (self[ii], self[jj])):
                            angles[kk*(dim-1):(kk+1)*(dim-1)] = get_angle_space(
                                directions=surf_points[:, kk]-obstacle.center_position,
                                OrthogonalBasisMatrix=NullMatrices[kk, :, :])
                                
                            # Reset if too far out
                            if np.linalg.norm(angles[kk*(dim-1):(kk+1)*(dim-1)]) > pi:
                                angles[kk*(dim-1):(kk+1)(dim-1)] = 0

                    cent_points = np.zeros((dim, 2))

                    dist, ref_point1, ref_point2 = self.angle_gradient_descent(
                        self[ii], self[jj], angles=angles, NullMatrices=NullMatrices
                    )

                    self.set_distance(ii, jj, dist)
                    
                    # if dist>0:
                    self.set_boundary_reference_point(ii, jj, ref_point1)
                    self.set_boundary_reference_point(jj, ii, ref_point2)
                        
                    if dist <= 0:
                        # Distance==0, i.e. intersecting & ref_point1==ref_point2
                        self.intersection_matrix[ii, jj] = ref_point1
                        

    def angle_gradient_descent(self, obs0, obs1, angles, NullMatrices, contact_err=1e-4, convergence_err=1e-3, max_it=100):
        ''' Find closest point of obstacles using gradient descent in direction space. 
        Gradient Descent is performed in the angle space of the obstacle. '''
        
        dim = obs0.dim
        
        surface_points = np.zeros((dim, 2))
        surface_derivatives = np.zeros((dim, 2))

        # Setup for numerical gradient descent
        step_size = 0.03 
        it_count = 0

        # Obstacles intersecting
        is_intersecting = False

        while not is_intersecting:
            # Gradient descent in the angle space of the obstacle
            for obs, ii in zip([obs0, obs1], [0, 1]):
                angle = angles[ii*(dim-1):(ii+1)*(dim-1)]
                if np.linalg.norm(angle) > pi:
                    angle[:] = 0
                surface_derivatives[:, ii] = obs.get_surface_derivative_angle_num(
                    angle, NullMatrix=NullMatrices[ii, :, :], in_global_frame=True)
            
                direction_angle = get_angle_space_inverse(
                    angle, NullMatrix=NullMatrices[ii, :, :])

                surface_points[:, ii] = obs.get_local_radius_point(
                    direction=direction_angle, in_global_frame=True)

            dist_dir = (surface_points[:, 1] - surface_points[:, 0])
            dist_magnitude = np.linalg.norm(dist_dir)

            if dist_magnitude < contact_err:
                is_intersecting = True
                print("Points are intersecting. Switching to Gamma-descent.")
                continue

            delta_angle = (0.5/dist_magnitude*
                           np.array([-dist_dir.dot(surface_derivatives[:, 0]),
                                     dist_dir.dot(surface_derivatives[:, 1])]))

            angles = angles - step_size*delta_angle
            it_count += 1

            # Gradient descent step
            if it_count>max_it or np.linalg.norm(step_size*delta_angle) < convergence_err:
                print("Convergence of angle descent reached after {} iterations.".format(it_count))
                break

        reference_points = np.zeros((dim, 2))
        for obs, ii in zip((obs0, obs1), [0, 1]):
            angle = angles[ii*(dim-1):(ii+1)*(dim-1)]
            dir0 = get_angle_space_inverse(angle, NullMatrix=NullMatrices[ii, :, :])

            reference_points[:, ii] = obs.get_local_radius_point(direction=dir0,
                                                                 in_global_frame=True)
        
        if is_intersecting:
            # Is intersecting
            reference_point = self.gamma_gradient_descent(
                obs0, obs1, common_point=np.mean(reference_points, axis=1)
            )

            dist = 0

            # print('center obs1 & obs2', obs0.center_position, obs1.center_position)
            # print('ref_pos obs1 & obs2', reference_point, reference_point)
            # print('same-same \n')
            
            return dist, reference_point, reference_point
        
        else:
            # print('center obs1 & obs2', obs0.center_position, obs1.center_position)
            # print('ref_pos obs1 & obs2', reference_points[:, 0], reference_points[:, 1])
            # print('diff-diff \n')
            
            return dist_magnitude, reference_points[:, 0], reference_points[:, 1]

        
    def gamma_gradient_descent(self, obs0, obs1, common_point, convergence_err=1e-3, max_it=100):
        ''' Find closest point of obstacles using gradient descent in direction space. '''
        step_size = 0.09

        it_count = 0
        while True:
            # Gradient descent step
            delta_gamma = self.derivative_gamma_sum(common_point, obs0, obs1)

            # TODO: smart step size
            common_point = common_point - step_size* delta_gamma
            it_count += 1
            
            if it_count>max_it or np.linalg.norm(step_size*delta_gamma) < convergence_err:
                break
            
        print("Convergence of Gamma-descent reached after {} iterations.".format(it_count))

        # print('center obs1 & obs2', obs0.center_position, obs1.center_position)
        # print('common point', common_point)
        # print('same & same \n')
        
        return common_point

    
    def derivative_gamma_sum(self, position, obs0, obs1, grad_pow=4,
                             delta_dist=1e-6, gamma_type="proportional"):
        ''' Derive a function based on gamma to find a reasonable center 
        which lies strictly inside the obstacles'''
        dim = obs0.dim

        derivative = np.zeros(dim)

        for dd in range(dim):
            delta = np.zeros(dim)
            delta[dd] = delta_dist

            gamma_high = obs0.get_gamma(position+delta, in_global_frame=True, gamma_type=gamma_type)
                                        
            gamma_low = obs0.get_gamma(position-delta, in_global_frame=True, gamma_type=gamma_type)

            delta_gamma = (self.get_gamma_cost_function(gamma_high)
                           - self.get_gamma_cost_function(gamma_low))

            # print('')
            # print('gamma0_high', gamma_high, '--- gamma0_low', gamma_high)
            # print('mean gamma', (gamma_high+gamma_low)/2.0)
            
            
            gamma_high = obs1.get_gamma(position+delta, in_global_frame=True, gamma_type=gamma_type)
                                        
            
            gamma_low = obs1.get_gamma(position-delta, in_global_frame=True, gamma_type=gamma_type)

            delta_gamma += (self.get_gamma_cost_function(gamma_high, obs1.is_boundary)
                            - self.get_gamma_cost_function(gamma_low, obs1.is_boundary))
            
            derivative[dd] = (delta_gamma)/(2*delta_dist)

            # print('mean boundary gamma', (gamma_high+gamma_low)/2.0)
            
        return derivative

    
    def get_gamma_cost_function(self, gamma, is_boundary=False, margin=1e-2):
        ''' This functions maps [0, 1] to [1, - infinity]
        ! A margin is added to compensate for cases where  '''
        if is_boundary:
            # TODO: cost function which enforces lying outside (make constant distance)
            # Gamma is relative
            # print('boundary')
            return np.abs(gamma-0.9)**2*10
        else:
            # TODO: cost function which enforces it to lie inside!
            # return 1/(1-gamma+margin)
            return np.abs(gamma)**3
        
# BUGS to solve:
#    - far-far away, the automatic-extension of the hull of the ellipse does not work
#    - Gradient descent change function