#!/USSR/bin/python3

'''
@date 2019-10-15
@author Lukas Huber 
@email lukas.huber@epfl.ch
'''

import time
import numpy as np
from math import sin, cos, pi, ceil
import warnings, sys

import numpy.linalg as LA

from dynamic_obstacle_avoidance.obstacle_avoidance.angle_math import *

from dynamic_obstacle_avoidance.obstacle_avoidance.state import *
from dynamic_obstacle_avoidance.obstacle_avoidance.angle_math import angle_modulo, angle_difference_directional_2pi
from dynamic_obstacle_avoidance.obstacle_avoidance.modulation import *
from dynamic_obstacle_avoidance.obstacle_avoidance.obs_common_section import *
from dynamic_obstacle_avoidance.obstacle_avoidance.obs_dynamic_center_3d import *

from dynamic_obstacle_avoidance.obstacle_avoidance.obstacle import Obstacle

import matplotlib.pyplot as plt
# import quaternion

visualize_debug = False

# class Ellipse(EllipseObstacle):
    # ''' Backwards compatibility. '''
    # pass


class Ellipse(Obstacle):
    ''' Ellipse type obstacle 
    Geometry specifi attributes are
    axes_length: 
    curvature: float / array (list)
    '''
    # self.ellipse_type = dynamic_obstacle_avoidance.obstacle_avoidance.obstacle.Ellipse
    def __init__(self, axes_length=None, curvature=None,
                 a=None, p=None,
                 margin_absolut=0,
                 hull_with_respect_to_reference=False,
                 *args, **kwargs):

        if sys.version_info>(3,0):
            super().__init__(*args, **kwargs)
        else:
            super(Ellipse, self).__init__(*args, **kwargs) # works for python < 3.0?!
        
        if not axes_length is None:
            self.axes_length = np.array(axes_length)
        elif not a is None:
            self.axes_length = np.array(a) # TODO: depreciated, remove
        else:
            warning.warn("No axis length given!")
            self.axes_length = np.ones((self.dim))
            
        if not curvature is None:
            self.curvature = curvature
        elif not p is None:
            self.curvature = p # TODO: depreciated, remove
        else:
            self.curvature = np.ones((self.dim))

        self.margin_absolut = margin_absolut

        self.hull_with_respect_to_reference = hull_with_respect_to_reference

        self.is_convex = True
        
        # Reference to other arrays
        # self.edge_points -- # Points of 'the no-go zone'
        
        # No go zone assuming a uniform margin around the obstacle
        self.edge_margin_points = np.zeros((self.dim, 0))

        # Extended in case that the reference point is outside the obstacle
        self.edge_reference_points = self.edge_margin_points 
        
        # Extended in case that the reference point is outside the obstacle
        # 1st pair of points corresponds to 'extension' of reference point
        # 2nd pair of points are the tangent points on the ellipse
        self.edge_reference_points = self.edge_margin_points
        
        self.ind_edge_ref = 0
        self.ind_edge_tang = 1

        self.margin_absolut = margin_absolut # why again???
        
    @property
    def a(self): # TODO: remove
        warnings.warn("Depreciated use 'axes_length' instead")
        return self.axes_length

    @a.setter # TODO:remove
    def a(self, value):
        warnings.warn("Depreciated use 'axes_length' instead")
        self.axes_length = value

    @property
    def axes(self): # TODO: remove
        return self.axes_length

    @axes.setter # TODO:remove
    def axes(self, value):
        self.axes_length = value

    @property
    def axes_length(self):
        return self._axes_length

    @axes_length.setter
    def axes_length(self, value):
        self._axes_length = value

    @property
    def p(self): # TODO: remove
        warnings.warn("Depreciated use 'curvature' instead")
        return self._curvature

    @p.setter
    def p(self, value): # TODO: remove
        warnings.warn("Depreciated use 'curvature' instead")
        self.curvature = value

    @property
    def curvature(self):
        if len(self._curvature)>1: # TODO: deprciated... remove
            return self._curvature[0]
        return self._curvature

    @curvature.setter
    def curvature(self, value):
        if isinstance(value, (list)): # TODO remove only allow one value...
            self._curvature = np.array(value)
        else:
            self._curvature = value

    @property
    def margin_absolut(self):
        return self._margin_absolut

    @margin_absolut.setter
    def margin_absolut(self, value):
        self._margin_absolut = value

    @property
    def axes_with_margin(self):
        if self.is_boundary:
            return self.axes_length - self.margin_absolut
        else:
            return self.axes_length + self.margin_absolut
    
    def get_minimal_distance(self):
        return np.min(self.a)

    def get_maximal_distance(self):
        # Eucledian
        return np.sqrt(np.sum(self.a*2))
        
    def get_reference_length(self):
        ''' Get a characeteric (or maximal) length of the obstacle. 
        For an ellipse obstacle,the longest axes. '''
        return LA.norm(self.axes_length) + self.margin_absolut

    def calculate_normalVectorAndDistance(self):
        normal_vector = np.zeros((self.dim, self.n_planes))
        normalDistance2center = np.zeros(self.n_planes)

        if self.hull_with_respect_to_reference:
            position = self.reference_point
        else:
            position = np.zeros(self.dim)
        
        for ii in range(self.n_planes):
            normal_vector[:, ii] = (self.edge_reference_points[:,ii, 0]
                                    - self.edge_reference_points[:, ii-1, 1])
                                    
            normal_vector[:, ii] = np.array([normal_vector[1, ii], -normal_vector[0, ii],])

        for ii in range(self.n_planes):
            normalDistance2center[ii] = normal_vector[:, ii].T.dot(self.edge_reference_points[:, ii, 1])

        normal_vector = normal_vector/np.tile(np.linalg.norm(normal_vector, axis=0), (self.dim, 1)) 

        return normal_vector, normalDistance2center
        
    def get_distance_to_hullEdge(self, position, hull_edge=None, in_global_frame=False):
        if in_global_frame:
            position = self.transform_global2relative(position)
        
        if hull_edge is None:
            hull_edge = self.hull_edge
            normal_vector = self.normal_vector
            
        else:
            normal_vector, dist = self.calculate_normalVectorAndDistance(hull_edge)

        hull_edge = hull_edge.reshape(self.dim, -1)
        n_planes = hull_edge.shape[1]
        if len(hull_edge.shape)<2:
            vec_position2edge = np.tile(position-hull_edge, (n_planes, 1)).T
        else:
            vec_position2edge = np.tile(position, (n_planes, 1)).T - hull_edge
                
        distance2plane = np.sum((normal_vector * vec_position2edge), axis=0)

        if False:
            vec_position2edge = np.tile(position, (n_planes, 1)).T - self.tangent_points
            distance2plane = np.sum((self.normal_vector * vec_position2edge), axis=0)
            
        return distance2plane
    

    def position_is_in_direction_of_ellipse(self, position, in_global_frame=False):
        if in_global_frame:
            position = self.transform_global2relative(position)
        
        mag_position = LA.norm(position, axis=0)
        position_dir = position / mag_position
        
        angle_tangents = np.zeros(self.edge_reference_points.shape[2])
            
        for ii in range(self.edge_reference_points.shape[2]):
            angle_tangents[ii] = np.arctan2(self.edge_reference_points[1, self.ind_edge_tang, ii],
                                            self.edge_reference_points[0, self.ind_edge_tang, ii])

        angle_position = np.arctan2(position[1], position[0])

        angle_tang = angle_difference_directional_2pi(angle_tangents[1], angle_tangents[0])
        angle_pos_tang0 = angle_difference_directional_2pi(angle_position, angle_tangents[0])
        angle_tang1_pos = angle_difference_directional_2pi(angle_tangents[1], angle_position)

        margin_subtraction = 1e-12
        
        return abs(angle_tang-(angle_tang1_pos+angle_pos_tang0)) < margin_subtraction


    def get_normal_ellipse(self, position):
        ''' Return normal to ellipse surface '''
        return (2*self.p/self.axes_length*(position/self.axes_length)**(2*self.p-1))
    

    def get_angle2referencePatch(self, position, max_angle=pi, in_global_frame=False):
        '''
        Returns an angle in [0, pi]
        '''
        if in_global_frame:
            position = self.transform_global2relative(position)
            
        n_planes = self.edge_reference_points.shape[1]

        vec_position2edge = np.tile(position, (n_planes,1)).T - self.edge_reference_points[:, :, 0]
        normalDistance2plane = np.sum((self.normal_vector*vec_position2edge), axis=0)
        
        angle2refencePatch = np.ones(n_planes)*max_angle

        for ii in np.arange(n_planes)[normalDistance2plane>0]:
            # vec_position2edge[:, ii] /= LA.norm(vec_position2edge[:, ii])

            # cos_position2edge = vec_position2edge[:, ii].T.dot(self.tangent_vector[:,ii])
            # angle2refencePatch[ii] = np.arccos(cos_position2edge)

            edge_points_temp = np.vstack((self.edge_reference_points[:, ii, 0], self.edge_reference_points[:, ii-1, 1])).T
            # Calculate angle to agent-position
            ind_sort = np.argsort(LA.norm(np.tile(position, (2,1)).T - edge_points_temp, axis=0))
            tangent_line = edge_points_temp[:,ind_sort[1]] - edge_points_temp[:, ind_sort[0]]
            
            position_line = position - edge_points_temp[:, ind_sort[0]]
            angle2refencePatch[ii] = self.get_angle2dir(position_line, tangent_line)

        return angle2refencePatch
    

    def get_normal_direction(self, position, in_global_frame=False, normalize=True):
        if in_global_frame:
            position = self.transform_global2relative(position)

        if self.hull_with_respect_to_reference:
            position = position-self.reference_point
            raise NotImplementedError("Everything needs to be with respect to reference.")

        if self.reference_point_is_inside or self.position_is_in_direction_of_ellipse(position):
            normal_vector = self.get_normal_ellipse(position)
        else:
            if False:
            # if self.margin_absolut:
                angle_ref = np.arctan2(self.edge_reference_points[1, self.ind_edge_ref, 0],
                                       self.edge_reference_points[0, self.ind_edge_ref, 0])

                angle_position = np.arctan2(position[1], position[0])

                if angle_difference_directional(angle_ref, angle_position) > 0:
                    pass
                
                raise NotImplementedError()

            else:
                # normal_distances = np.zeros(self.normal_vectors.shape[1])
                # for ii in range(self.normal_vectors.shape[1]):
                    # normal_distances[ii] = self.normal_vector[:, ii].T.dot(position)

                # normal_distances = normal_distances-self.normalDistance2center

                # for ii in range(normal_distances.shape[0]):
                    # if not normal_distances[ii]:
                        # return self.normal_vector[:, 1-ii]

                angle2referencePlane = self.get_angle2referencePatch(position)
                weights = self.get_angle_weight(angle2referencePlane)

                normal_vector = get_directional_weighted_sum(
                    null_direction=position, directions=self.normal_vector,
                    weights=weights, normalize=False, normalize_reference=True)

        if normalize:
            # TODO: can it be removed?
            vec_norm = np.linalg.norm(normal_vector)
            if vec_norm: # nonzero
                normal_vector = normal_vector/vec_norm

        if in_global_frame:
            normal_vector = self.transform_relative2global_dir(normal_vector)
            
        return normal_vector

    def get_gamma_ellipse(self, position, in_global_frame=False, axes=None, curvature=None):
        if in_global_frame:
            position = self.transform_global2relative(position)
        # import pdb; pdb.set_trace()
        
        if (len(position.shape)>1):
            n_points = position.shape[1]
        else:
            n_points = -1

        if axes is None:
            axes = self.axes_with_margin

        if curvature is None:
            curvature = self.curvature

        if isinstance(curvature, (list, np.ndarray)): # TODO: remove after testing
            warnings.warn("Wrong curvature dimension.")
            curvature = curvature[0]
        
        if n_points>0:
            # Assumption -- zero-norm check already performed
            # norm_position = np.linalg.norm(position, axis=0)
            # np.sum( (position / np.tile(self.axes_with_margin, (n_points,1)).T ) ** (2*np.tile(self.p, (n_points,1)).T), axis=0)
            
            # rad_local = np.sqrt(1.0/np.sum((position/np.tile(self.axes_with_margin, (n_points, 1)).T)**np.tile(self.p, (n_points, 1)).T, axis=0))
            # return np.linalg.norm(position, axis=0)/(rad_local*np.linalg.norm(position, axis=0))
            # return 1.0/rad_local
            return np.sqrt(np.sum((position / np.tile(axes, (n_points, 1)).T)**np.tile(2*curvature, (n_points, self.dim)).T, axis=0))
        
        else:
            norm_position = np.linalg.norm(position)
            if norm_position == 0:
                return 0
            # rad_local = np.sqrt(1.0/np.sum(position/self.axes_with_margin**self.p) )
            # return 1.0/rad_local
            return np.sqrt(np.sum((position/axes)**(2*curvature) ))
    
    def get_surface_derivative_angle(self, angle_space, in_global_frame=False):
        if self.dim ==2:
            if in_global_frame:
                angle_space = angle_space - self.orientation
                # import pdb; pdb.set_trace() ## DEBUG ##
                
            direction = np.array([np.cos(angle_space), np.sin(angle_space)])
            direction_perp = np.array([-direction[1], direction[0]])
            
        else:
            raise NotImplementedError("TODO for d>2")

        # TODO: should this be more general definition
        local_radius = self.get_intersection_with_surface(direction=direction, only_positive_direction=True)
        
        local_radius = np.linalg.norm(local_radius, 2)
        derivative = direction_perp*local_radius - 0.5*direction * (local_radius**3) *self.get_radius_derivative_direction(angle_space)
        
        if in_global_frame:
            derivative = self.transform_relative2global_dir(derivative)
        return derivative
    
    
    def get_radius_derivative_direction(self, angle_space):
        axes = self.axes_with_margin
        if self.dim==2:
            return 2*np.cos(angle_space)*np.sin(angle_space)*(-1.0/(axes[0]*axes[0])+1.0/(axes[1]*axes[1]))
        else:
            raise NotImplementedError("Implement for d>2")
        

    def get_local_radius_point(self, direction, in_global_frame=False):
        return self.get_intersection_with_surface(direction=direction, in_global_frame=in_global_frame, only_positive_direction=True)
    

    def get_local_normal_direction(self, direction, in_global_frame=False):
        if in_global_frame:
            position = self.center_position + direction
        else:
            position = direction

        norm = self.get_normal_ellipse(position)

        if in_global_frame:
            norm = self.transform_relative2global(norm)
            
        return norm


    def get_intersection_with_surface(self, edge_point=None, direction=None, axes=None, center_ellipse=None, only_positive_direction=False, in_global_frame=False):
        ''' Intersection of (x_1/a_1)^2 +( x_2/a_2)^2 = 1 & x_2=m*x_1+c

        edge_point / c : Starting point of line
        direction / m : direction of line

        axes / a1 & a2: Axes of ellipse
        center_ellipse: Center of ellipse '''


        # import pdb; pdb.set_trace()
        if in_global_frame:
            direction = self.transform_global2relative_dir(direction)

        if axes is None:
            axes = self.axes_with_margin

        if edge_point is None:
            # edge_point = np.zeros(self.dim)
            mag_x = 1.0/np.sqrt(np.sum((direction/axes)**2))
            
            intersections = mag_x * direction
            
            if not only_positive_direction:
                intersections =  np.tile(pos, (2,1)).T
                
            if in_global_frame:
                intersections = self.transform_relative2global(intersections)

            return intersections

        elif in_global_frame:
            edge_point = self.transform_global2relative(edge_point)

        # Dimension
        if self.dim > 2:
            raise NotImplementedError("Not yet implemented for D>2")
        
        if not center_ellipse is None:
            edge_point = edge_point - center_ellipse
        
        # x_1^2 * a_2^2 + (m*x_1+c)^2*a_1^2 = a_1^2*a_2^2
        # x_1^2 (a_2^2 + m^2*a_1^2) + x_1*(a_1^2*m*c*2) + c^2*a_1^2 - a_1^2*a_2^2
        if direction[0]==0:
            if only_positive_direction:
                intersections = np.zeros(self.dim)
                intersections[0] = edge_point[0]
                intersections[1] = np.copysign(axes[1], direction[1])
                
            else:
                intersections = np.zeros((2, self.dim))
                intersections[0, 0] = intersections[0, 1] = edge_point[0]
                
                intersections[1, 0] = axes[1]
                intersections[1, 1] = -axes[1]
            
        else:
            m = direction[1]/direction[0]
            c = edge_point[1] - m*edge_point[0]

            A = (axes[0]*m)**2 + axes[1]**2
            B = 2*axes[0]**2*m*c
            C = (axes[0]*c)**2 - (axes[0]*axes[1])**2

            D = B*B - 4*A*C

            if D<0:
                # import pdb; pdb.set_trace() ## DEBUG ##
                warnings.warn("No intersection found.")
                return 

            sqrtD = np.sqrt(D)

            if only_positive_direction:
                intersections = np.zeros(self.dim)
                intersections[0] = (-B+sqrtD)/(2*A)

                if (intersections[0] - edge_point[0])/direction[0]>0:
                    intersections[0] = (-B-sqrtD)/(2*A)
                intersections[1] = intersections[0]*m + c

            else:
                intersections = np.zeros((self.dim, 2))
                intersections[0,:] = np.array([(-B+sqrtD), (-B-sqrt(D))])/(2*A)
                intersections[1,:] = intersections[0,:]*m + c
                # return intersections
        
        if not center_ellipse is None:
            intersections = intersections + np.tile(center_ellipse, (intersections.shape[1],1)).T

        if in_global_frame:
            intersections = self.transform_relative2global(intersections)

        return intersections


    def _get_local_radius_ellipse(self, position, relative_center=None):
        '''
        Get radius of ellipse in direction of position from the reference point
        '''
        # TODO: extend for actual relative center

        if relative_center is None:
            relative_center = np.zeros(self.dim)

        # try:
        direction = position-relative_center
        # except:
            # import pdb; pdb.set_trace()
            
        intersection = self.get_intersection_with_surface(
            relative_center, direction, only_positive_direction=True)

        if (relative_center is None):
            dist = np.linalg.norm(intersection)
        else:
            dist = np.linalg.norm(intersection-relative_center)
        return dist


    
    def _get_local_radius(self, position, relative_center=None):
        # TODO: test for margin / reference point
        # TODO: improve speed
        if relative_center is None:
            relative_center = np.zeros(self.dim)

        # TODO: remove and make actual reference point
        if relative_center is None:
            relative_center = np.zeros(self.dimension)

        margin_absolut = self.margin_absolut
        n_points = position.shape[1]
        radius = np.zeros(position.shape[1])

        # Original Gamma
        if self.dim==2:
            if (self.reference_point_is_inside):
                for pp in range(n_points):
                    # radius[pp] = self._get_local_radius_ellipse(position[:, pp], relative_center)
                    radius[pp] = self._get_local_radius_ellipse(position[:, pp])
            else:
                for pp in range(n_points):
                    if self.position_is_in_direction_of_ellipse(position[:, pp]):
                        # radius[pp] = self._get_local_radius_ellipse(position[:, pp], relative_center)
                        radius[pp] = self._get_local_radius_ellipse(position[:, pp])
                    else:
                        angle_position = np.arctan2(position[1, pp], position[0, pp])

                        dist_intersect = -1
                        for ii, sign in zip(range(self.n_planes), [1,-1]):
                            angle_ref = np.arctan2(
                                self.edge_reference_points[1, self.ind_edge_ref, ii],
                                self.edge_reference_points[0,self.ind_edge_ref, ii])

                            if sign*angle_difference_directional(angle_ref, angle_position) >= 0:
                                surface_dir = (self.edge_reference_points[: ,self.ind_edge_ref, ii] - self.edge_reference_points[:, self.ind_edge_tang, 1-ii])

                                dist_intersect, dist_tangent = LA.lstsq(np.vstack((position[:, pp], -surface_dir)).T, self.edge_reference_points[:, self.ind_edge_ref, ii], rcond=-1)[0]

                                dist_intersect = dist_intersect*np.linalg.norm(position[:, pp])

                        if dist_intersect<0: # 
                            if not margin_absolut:
                                raise ValueError("Negative value not possible.")

                            intersections = self.get_intersection_with_surface(edge_point=np.zeros(self.dim), direction=position[:, pp], axes=np.ones(self.dim)*margin_absolut)
                                
                            # self.get_intersectionWithEllipse()

                            distances = np.linalg.norm(intersections, axis=0)
                            dist_intersect = np.max(distances)
                        radius[pp] = dist_intersect
        return radius

    # def get_gamma(self, position, in_global_frame=False, gamma_type='proportional', margin_absolut=None):
    def get_gamma_old(self, position, in_global_frame=False, gamma_type='proportional', margin_absolut=None):
        '''
        Get distance function from surface
        '''
        # TODO: depreciated... remove
        
        if in_global_frame:
            position = self.transform_global2relative(position)

        multiple_positions = (len(position.shape)>1)
        
        if multiple_positions:
            n_points = position.shape[1]
        else:
            n_points = 1
            position = position.reshape((self.dim, n_points))

        Gamma = np.zeros(n_points)
        intersecting_ind = np.ones(n_points, dtype=bool) # TODO -- still used?

        if margin_absolut is None:
            margin_absolut = self.margin_absolut
        
        # Original Gamma
        if gamma_type=='proportional':
            if self.dim==2:
                if (self.reference_point_is_inside):
                    Gamma = self.get_gamma_ellipse(position)
                    # Gamma[intersecting_ind] = np.sum( (position / np.tile(self.axes_with_margin, (n_points,1)).T ) ** (2*np.tile(self.p, (n_points,1)).T), axis=0)
                else:
                    for pp in range(n_points):
                        if self.position_is_in_direction_of_ellipse(position[:, pp]):
                            # Gamma[intersecting_ind] = np.sum( (position[:, intersecting_ind] / np.tile(self.axes_with_margin, (n_points,1)).T ) ** (2*np.tile(self.p, (n_points,1)).T), axis=0)
                            Gamma[pp] = self.get_gamma_ellipse(position[:, pp])
                        else:
                            angle_position = np.arctan2(position[1, pp], position[0, pp])
                            
                            dist_intersect = -1
                            for ii, sign in zip(range(self.n_planes), [1,-1]):
                                angle_ref = np.arctan2(self.edge_reference_points[1,self.ind_edge_ref, ii], self.edge_reference_points[0,self.ind_edge_ref, ii])

                                # print('angle ref', angle_ref)

                                if sign*angle_difference_directional(angle_ref, angle_position) >= 0:
                                    surface_dir = (self.edge_reference_points[: ,self.ind_edge_ref, ii] - self.edge_reference_points[:, self.ind_edge_tang, 1-ii])

                                    dist_intersect, dist_tangent = LA.lstsq(np.vstack((position[:, pp], -surface_dir)).T, self.edge_reference_points[: ,self.ind_edge_ref, ii], rcond=-1)[0]
                            
                            if dist_intersect<0: # 
                                if not margin_absolut:
                                    import pdb; pdb.set_trace() ## DEBUG ##
                                    raise ValueError("Negative value not possible.")
                                
                                intersections = get_intersectionWithEllipse(
                                    edge_point=np.zeros(self.dim), direction=position,
                                    axes=np.ones(self.dim)*margin_absolut)

                                distances = np.linalg.norm(intersections, axis=0)
                                dist_intersect = np.max(distances)
                            Gamma[pp] = 1.0/dist_intersect

                    if np.sum(intersecting_ind):
                        n_points = np.sum(intersecting_ind)
        else:
            raise NotImplementedError()

        if self.is_boundary:
            Gamma = self.get_boundaryGamma(Gamma,Gamma_ref=self.Gamma_ref)

        if not multiple_positions:
            return Gamma[0] # 1x1-array to value
        return Gamma


    def update_deforming_obstacle(self, radius_new, position, orientation):
        ''' Update an obstacle which can also deform '''
        self.radius_old = copy.deepcopy(self.radius)
        self.radius = radius_new

        self.update_position_and_orientation(position=new_position, orientation=new_orientation)
        
    
    def draw_obstacle(self, numPoints=20, update_core_boundary_points=True, point_density=2*pi/50):
        '''
        Creates points for obstacle and obstacle margin
        '''
        p = self.p
        a = self.axes_length

        if update_core_boundary_points:
            if self.dim==2 :
                theta = np.linspace(-pi,pi, num=numPoints)
                # resolution = numPoints # Resolution of drawing #points
                boundary_points = np.zeros((self.dim, numPoints))
                boundary_points[0,:] = a[0]*np.cos(theta)
                boundary_points[1,:] = np.copysign(a[1], theta)*(1 - np.cos(theta)**(2*p[0]))**(1./(2.*p[1]))
                self.boundary_points = boundary_points

            elif self.dim==3:
                numPoints = [numPoints, ceil(numPoints/2)]
                theta, phi = np.meshgrid(np.linspace(-pi,pi, num=numPoints[0]),np.linspace(-pi/2,pi/2,num=numPoints[1]) ) #
                numPoints = numPoints[0]*numPoints[1]
                # resolution = numPoints # Resolution of drawing #points
                theta = theta.T
                phi = phi.T

                boundary_points = np.zeros((self.dim, numPoints))
                boundary_points[0,:] = (a[0]*np.cos(phi)*np.cos(theta)).reshape((1,-1))
                boundary_points[1,:] = (a[1]*np.copysign(1, theta)*np.cos(phi)*(1 - np.cos(theta)**(2*p[0]))**(1./(2.*p[1]))).reshape((1,-1))
                boundary_points[2,:] = (a[2]*np.copysign(1,phi)*(1 - (np.copysign(1,theta)*np.cos(phi)*(1 - 0 ** (2*p[2]) - np.cos(theta)**(2*p[0]))**(1/(2**p[1])))**(2*p[1]) - (np.cos(phi)*np.cos(theta)) ** (2*p[0])) ** (1/(2*p[2])) ).reshape((1,-1))
                self.boundary_points_local = boundary_points
                
            else:
                raise NotImplementedError("Not yet implemented for dimension >3")

        if self.dim==2:
            boundary_points_margin = np.zeros((self.dim, 0))
            if not self.reference_point_is_inside:
                
                angle_tangents = np.zeros(2)
                for ii in range(angle_tangents.shape[0]):
                    angle_tangents[ii] = np.arctan2(self.edge_reference_points[1, self.ind_edge_tang, ii], self.edge_reference_points[0, self.ind_edge_tang, ii])
                    # angle_tangents[ii] = np.arctan2(self.tangent_points[1, ii], self.tangent_points[0, ii])
                if angle_tangents[0]<angle_tangents[1]:
                    theta = np.arange(angle_tangents[0], angle_tangents[1], point_density)
                else:
                    theta = np.arange(angle_tangents[0], angle_tangents[1]+2*pi, point_density)
                    theta = angle_modulo(theta)

            elif not self.margin_absolut:
                # No boundary and reference point inside
                self.boundary_points_margin_local = self.boundary_points
                return
                
            a = self.axes_with_margin
            
            # Margin points
            cos_theta, sin_theta = np.cos(theta), np.sin(theta)
            power = 2*self.curvature
            factor = 1.0/((cos_theta/a[0])**power + (sin_theta/a[1])**power)**(1.0/power)

            if self.reference_point_is_inside:
                boundary_points_margin = np.hstack(( boundary_points_margin, factor*np.vstack((cos_theta, sin_theta)) ))
                    
            else:
                boundary_points_margin = np.hstack((
                    boundary_points_margin,
                    np.reshape(self.edge_reference_points[:, self.ind_edge_ref, 1], (self.dim, 1)),
                    factor*np.vstack((cos_theta, sin_theta)),
                    np.reshape(self.edge_reference_points[:, self.ind_edge_tang, 1], (self.dim, 1))
                ))
            
            self.boundary_points_margin_local = boundary_points_margin

        if self.dim==3:
            a = a+self.margin_absolut
            boundary_points_margin = np.hstack((
                boundary_points_margin,
                np.vstack((a[0]*np.cos(phi)*np.cos(theta),
                           a[1]*np.copysign(1, theta)*np.cos(phi)*(1 - np.cos(theta)**(2*p[0]))**(1./(2.*p[1])),
                           a[2]*np.copysign(1,phi)*(1 - (np.copysign(1,theta)*np.cos(phi)*(1 - 0 ** (2*p[2]) - np.cos(theta)**(2*p[0]))**(1/(2**p[1])))**(2*p[1]) - (np.cos(phi)*np.cos(theta)) ** (2*p[0])) ** (1/(2*p[2])) )) ))
                
            self.boundary_points_margin_local = boundary_points_margin
        
        return self.transform_relative2global(self._boundary_points_margin)

    
    def get_radius_of_angle(self, angle, in_global_frame=False):
        '''
        Extend the hull of non-boundary, convex obstacles such that the reference point lies in
        inside the boundary again.
        '''
        
        if in_global_frame:
            position =  transform_polar2cartesian(magnitude=10, angle=angle-self.orientation)
        else:
            position = transform_polar2cartesian(magnitude=1, angle=angle)
        
        gamma = self.get_gamma(position, gamma_type='proportional')
        return LA.norm(position)/gamma

    
    def extend_hull_around_reference(self, edge_reference_dist=0.3, relative_hull_margin=0.1):
        ''' Extend the hull of non-boundary, convex obstacles such that the reference point 
        lies in inside the boundary again. '''
        self.reference_point_is_inside = True # Default assumption
        
        dist_max = self.get_maximal_distance()*relative_hull_margin
        mag_ref_point = np.linalg.norm(self.reference_point)
        
        if mag_ref_point:
            reference_point_temp = self.reference_point*(1 + dist_max/mag_ref_point)
            gamma = self.get_gamma(reference_point_temp, np.zeros(self.dim))
        
        if (mag_ref_point and gamma>1):
            tt, tang_points = get_tangents2ellipse(edge_point=reference_point_temp, axes=self.axes_with_margin)

            tang_points = np.flip(tang_points, axis=1)
            if np.cross(tang_points[:, 0], tang_points[:, 1]) > 0: # TODO: remove 
                tang_points = np.flip(tang_points, axis=1)
                warnings.warn('Had to flip. Reverse tangent order [1]<-->[0]! ')
                # TODO: remove if no warning ever shows up...

            self.edge_reference_points = np.zeros((self.dim, 2, 2))
            self.edge_reference_points[:, self.ind_edge_ref, :] = np.tile(reference_point_temp,(2, 1)).T
                
            
            self.edge_reference_points[:, self.ind_edge_tang, :] = tang_points

            self.reference_point_is_inside = False
            self.n_planes = 2
            self.normal_vector, self.normalDistance2center = \
                self.calculate_normalVectorAndDistance()
                
            self.tangent_vector = np.zeros(self.normal_vector.shape)
            for ii in range(self.normal_vector.shape[1]):
                self.tangent_vector[:, ii] = [-self.normal_vector[1, ii],
                                              self.normal_vector[0, ii]]
        else:
            self.n_planes = 0


class CircularObstacle(Ellipse):
    ''' Ellipse obstacle with equal axes'''
    def __init__(self, radius=None, axes_length=None, *args, **kwargs):
        if not radius is None:
            axes_length = np.array([radius, radius])
        elif not radius is None:
            if radius.shape[0]==1:
                axes_length = np.array([axes_length, axes_length])
        else:
            raise RuntimeError("No radius input.")
            
        if sys.version_info>(3,0):
            super().__init__(axes_length=axes_length, *args, **kwargs)
        else:
            super(Ellipse, self).__init__(*args, **kwargs) # works for python < 3.0?!


    # Axes length is equal to radius for an circular obtject
    @property
    def radius(self):
        return self.axes_length[0]

    @property
    def radius_with_margin(self):
        return self.axes_with_margin[0]

