import sys
import time
sys.path.append('./vision')
sys.path.append('./move')

from transform import RealWorldCoordTransformer
from comms import JohnRobot
from data_providers import SSLVisionDataProvider

if __name__ == '__main__':
    data = SSLVisionDataProvider()
    data.start()
    robot = JohnRobot()
    trans = RealWorldCoordTransformer()
    new_x = 2000
    new_y = 300
    while True:
        pos = data.get_robot_position(9)
        og_x, og_y, og_w = pos.x, pos.y, pos.orientation
        print("Original coordinates", og_x, og_y, og_w)
        
        
        dest = (new_x - og_x, new_y - og_y)
        print('Dest {}'.format(dest))
        robot_x, robot_y = trans.transform(og_w, dest)
        print('Robot X %f Robot Y %f' % (robot_x, robot_y))

        robot.move(30 * robot_x, 30 * robot_y, 0, 0.2)

    # robot.move(50, 0, 0, 1.0)
    # time.sleep(2)
    #print(data.get_robot_position(9))
    # robot.move(0, 50, 0, 1.0)
    # time.sleep(0.5)
    # print(data.get_robot_position(9))
    # robot.move(-50, 0, 0, 1.0)
    # time.sleep(0.5)
    # print(data.get_robot_position(9))
    # robot.move(0, -50, 0, 1.0)
    # time.sleep(0.5)
    # print(data.get_robot_position(9))

    robot.die()
    data.stop()
