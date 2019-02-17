import sys
import time
import numpy as np
import logging
import threading
sys.path.append('./vision')
sys.path.append('./move')

from transform import RealWorldCoordTransformer
from comms import JohnRobot
from data_providers import SSLVisionDataProvider
from vision import GameState, Visualizer

def get_random_point():
    SIZE_W = 2400
    SIZE_H = 3200
    random_w = int(np.random.random() * SIZE_W)
    random_h = int(np.random.random() * SIZE_H)
    return random_w, random_h

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)

    robot = JohnRobot()
    print("a;")
    trans = RealWorldCoordTransformer()

    goal_x = 2000
    goal_y = 2000
    ROBOT_ID = 8 # this can change if coordinates are flipped in ssl-vision!
    # proportional scaling constant for distance differences
    SPEED_SCALE = .25
    MAX_SPEED = 50
    VERBOSE = False

    gs = GameState()
    viz = Visualizer(gs)
    viz.render()

    # spin up separate thread for gamestate to poll data
    gs.start_updating()

    while True:
        # tell robot to go to click
        if viz.user_click_field:
            # y and x are flipped for shits
            goal_x, goal_y = viz.user_click_field

        # tell robot to go to goal position
        if ROBOT_ID in gs._robots:
            gs.update_waypoint(ROBOT_ID, np.array([goal_x, goal_y]))
            pos = gs._robots[ROBOT_ID]
            og_x, og_y, og_w = pos
            delta = (goal_x - og_x, goal_y - og_y)
            # normalized offsets from robot's perspective
            robot_x, robot_y = trans.transform(og_w, delta)

            if VERBOSE:
                print("Original coordinates", og_x, og_y, og_w)
                print('Delta {}'.format(delta))
                print('(normalized diff) Robot X %f Robot Y %f' % (robot_x, robot_y))

            # move with speed proportional to delta
            speed = min(trans.magnitude(delta) * SPEED_SCALE, MAX_SPEED)
            robot.move(speed * robot_y, speed * robot_x, 0, 1.0)
        
        start_time = time.time()
        viz.render()
        end_time = time.time()
        print("Visualization overhead: %s s" % str(end_time - start_time))


    robot.die()
    gs.stop_updating()
