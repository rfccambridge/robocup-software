from comms import JohnRobot
from .transform import RealWorldCoordTransformer

ROBOT_ID = 8 # this can change if coordinates are flipped in ssl-vision!
# proportional scaling constant for distance differences
SPEED_SCALE = .25
MAX_SPEED = 50
COMMAND_DURATION = .2

class Commands(object):
    """Interface for sending basic commands to the robots, such as orienting the
    robot, kicking, or ref commands. Has access to all robot comms."""

    # TODO: connect to all robots that are available
    def __init__(self, gamestate):
        self.gamestate = gamestate
        self.robots = {}
        self.robots[ROBOT_ID] = JohnRobot()

    def die(self):
        for robot in self.robots:
            robot.die()

    # TODO: orient rotation, parameterize constants such as speed
    # tell specific robot to move towards given location
    def move_robot(self, robot_id, goal_pos):
        trans = RealWorldCoordTransformer()
        if robot_id not in self.robots:
            print("robot not available")
            return False
        
        if robot_id not in self.gamestate._robots:
            print("robot not seen")
            return False

        pos = self.gamestate._robots[robot_id]
        og_x, og_y, og_w = pos
        goal_x, goal_y = goal_pos
        delta = (goal_x - og_x, goal_y - og_y)
        # normalized offsets from robot's perspective
        robot_x, robot_y = trans.transform(og_w, delta)

        if False:
            print("Original coordinates", og_x, og_y, og_w)
            print('Delta {}'.format(delta))
            print('(normalized diff) Robot X %f Robot Y %f' % (robot_x, robot_y))

        # move with speed proportional to delta
        speed = min(trans.magnitude(delta) * SPEED_SCALE, MAX_SPEED)
        #robot.move(speed * robot_y, speed * robot_x, 0, COMMAND_DURATION)
        return True