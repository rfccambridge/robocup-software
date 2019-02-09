import sys
import time
import numpy as np
import logging
sys.path.append('./vision')
sys.path.append('./move')

from transform import RealWorldCoordTransformer
from comms import JohnRobot
from data_providers import SSLVisionDataProvider
from vision import GameState



def get_random_point():
    SIZE_W = 2400
    SIZE_H = 3200
    random_w = int(np.random.random() * SIZE_W)
    random_h = int(np.random.random() * SIZE_H)
    return random_w, random_h

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)

    data = SSLVisionDataProvider()
    data.start()
    robot = JohnRobot()
    print("a;")
    trans = RealWorldCoordTransformer()

    new_x = 2000
    new_y = 2000
    ROBOT_ID = 9
    # proportional scaling constant for distance differences
    SPEED_SCALE = .25
    MAX_SPEED = 50
    VERBOSE = False

    gs = GameState()
    gs.render()
    gs.update_waypoint(ROBOT_ID, np.array([new_x, new_y]))
    while True:
        pos = data.get_robot_position(ROBOT_ID)
        if not pos:
            continue
        # print(pos)
        og_x, og_y, og_w = pos.x, pos.y, pos.orientation


        if gs.user_click_field:
            # y and x are flipped for shits
            new_y, new_x = gs.user_click_field
            gs.update_waypoint(ROBOT_ID, np.array([new_x, new_y]))

        # update ball
        ball_data = data.get_ball_position()
        if ball_data and ball_data.confidence > .9:
            ball_pos = ball_data.x, ball_data.y
            gs.update_ball(ball_pos)
            new_x, new_y = ball_pos

        gs.update_robot(ROBOT_ID, np.array([og_x, og_y, og_w]))
        delta = (new_x - og_x, new_y - og_y)
        # normalized offsets from robot's perspective
        robot_x, robot_y = trans.transform(og_w, delta)

        if VERBOSE:
            print("Original coordinates", og_x, og_y, og_w)
            print('Delta {}'.format(delta))
            print('(normalized diff) Robot X %f Robot Y %f' % (robot_x, robot_y))

        speed = min(trans.magnitude(delta) * SPEED_SCALE, MAX_SPEED)

        robot.move(speed * robot_x, speed * robot_y, 0, 0.2)
        gs.render()

    robot.die()
    data.stop()
