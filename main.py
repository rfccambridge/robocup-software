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
    new_y = 300
    ROBOT_ID = 9
    SPEED = 100
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

        gs.update_robot(ROBOT_ID, np.array([og_x, og_y, og_w]))
        dest = (new_x - og_x, new_y - og_y)
        robot_x, robot_y = trans.transform(og_w, dest)

        if VERBOSE:
            print("Original coordinates", og_x, og_y, og_w)
            print('Dest {}'.format(dest))
            print('Robot X %f Robot Y %f' % (robot_x, robot_y))

        robot.move(SPEED * robot_x, SPEED * robot_y, 0, 0.2)
        gs.render()

    robot.die()
    data.stop()
