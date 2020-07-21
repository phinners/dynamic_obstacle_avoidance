# ....
#
'''
%load_ext autoreload
%autoreload 2
'''
# !/usr/bin/python3
'''
Dynamic Simulation - Obstacle Avoidance Algorithm


'''
# from dynamic_obstacle_avoidance.obstacle_avoidance.obstacle import *
from dynamic_obstacle_avoidance.obstacle_avoidance.modulation import *
# from dynamic_obstacle_avoidance.visualization.animated_simulation_3d import samplePointsAtBorder
# from dynamic_obstacle_avoidance.visualization.animated_simulation_3d import run_animation
from dynamic_obstacle_avoidance.obstacle_avoidance.obstacle_container import ObstacleContainer
from dynamic_obstacle_avoidance.obstacle_avoidance.obstacle_polygon import Ellipse
from dynamic_obstacle_avoidance.obstacle_avoidance.dynamic_boundaries_polygon import DynamicBoundariesPolygon
from dynamic_obstacle_avoidance.visualization.visualization_3d_level import Visualization3dLevel

__author__ = "LukasHuber"
__date__ = "2020-07-21"

import numpy as np
from numpy import pi
import time


print(' ----- Script <<surgery_setup>> started. ----- ')

#############################################################

# Choose a simulation between 0 and 12
simulationNumber = 0

saveFigures = False

#############################################################

def main(simulationNumber=0, saveFigures=False):
    if simulationNumber==0:
        N = 10
        x_init = np.vstack((np.ones(N)*20, np.linspace(-10,10,num=N) ))

        ### Create obstacle ###
        obs = []
        a1 = 0.05
        a2 = 0.20
        d_a = (a2-a1)/2

        l = 0.30
        points = np.array([[-a1, -a1, 0],
                           [a1, -a1, 0],
                           [a1, a1, 0],
                           [-a1, a1, 0],
                           [-a2, -a2, l],
                           [a2, -a2, l],
                           [a2, a2, l],
                           [-a2, a2, l]]).T

        indeces_of_tiles = np.array([
            # [0,1,2,3], # Bottom Part
            # [4,5,6,7], # Lid
            [0,1,4,5],
            [1,2,5,6],
            [2,3,6,7],
            [3,0,7,5]])
        
        # obs.append(DynamicBoundariesPolygon(edge_points=points, indeces_of_tiles=indeces_of_tiles, indeces_of_flexibleTiles=indeces_of_tiles, inflation_parameter=[0.03, 0.03, 0.03, 0.03], th_r=0))
        # obs.append(DynamicBoundariesPolygon(edge_points=points, indeces_of_tiles=indeces_of_tiles, indeces_of_flexibleTiles=indeces_of_tiles, inflation_parameter=[0.03, 0.03, 0.03, 0.03], th_r=0))
        obs = ObstacleContainer([DynamicBoundariesPolygon(is_surgery_setup=True)])

        # obs.append(Ellipse(axes_length=[1, 1, 2], center_position=[0, 0, 0], orientation=[1,0,0,0]))

        
        x_range = [-0.15, 0.15]
        y_range = [-0.15, 0.15]
        z_Range = [-a2, a2*2]

        attractorPos = np.array([0, 0, 0])
        eanimationName = 'surgery_simulation.mp4'

        # inflation_parameter = [0,0,0,0]
        # inflation_parameter = np.ones(4)*0.06
        inflation_parameter = [0, 0.01, 0.05, 0.03]

        static_simulation = True
        if static_simulation:
            visualizer = Visualization3dLevel(obs=obs, x_range=x_range, y_range=y_range, z_range=0)
            obs[0].inflation_parameter = inflation_parameter
            visualizer.vectorfield2d(save_figure=True)
        else:
            x_init = np.array([[-0.1, 0.1, 0.3]])
            visualizer = Visualization3dLevel(obs=obs, x_range=x_range, y_range=y_range, z_range=0)
            visualizer.animate2d(x_init, attractorPos)
        
    print('\n\n---- Script finished ---- \n\n')
    import pdb; pdb.set_trace() ### DEBUG ###

    
if __name__ == "__main__":
    
    if len(sys.argv) > 1:
        simulationNumber = int(sys.argv[1])

    if len(sys.argv) > 2:
        saveFigures = bool(int(sys.argv[2]))

    main(simulationNumber=simulationNumber, saveFigures=saveFigures)