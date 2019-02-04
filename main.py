import sys
import time
sys.path.append('./vision')
sys.path.append('./comms')

from johnrobot import JohnRobot
from data_providers import SSLVisionDataProvider


if __name__ == '__main__':
    data = SSLVisionDataProvider()
    data.start()
    pos = data.get_robot_position(9)
    og_x, og_y, og_w = pos.x, pos.y, pos.orientation
    robot = JohnRobot()
    print("Original coordinates", og_x, og_y)
    
    new_x = 0
    new_y = 0

    # robot.move(dir_x, dir_y, 0, 1.0)

    # robot.move(50, 0, 0, 1.0)
    # time.sleep(2)
    print(data.get_robot_position(9))
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
