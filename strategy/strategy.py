from comms import Robot
from .transform import RealWorldCoordTransformer

ROBOT_ID = 8

# default proportional scaling constant for distance differences
SPEED_SCALE = .35
MAX_SPEED = 150
# how long a command can be run without being updated
COMMAND_DURATION = .2

class Strategy(object):
    """Interface for sending basic commands to the robots, such as moving or
    orienting robots, and kicking. Has access to all robot comms."""

    # TODO: when we get multiple comms, connect to all robots that are available
    def __init__(self, gamestate):
        self.gamestate = gamestate
        self.robots = {}
        self.robots[ROBOT_ID] = Robot()
        # TODO: why is this a class? can we move to a shared utilities folder? - Kendall
        self._trans = RealWorldCoordTransformer()

    def die(self):
        for robot in self.robots:
            robot.die()

    # TODO: orient rotation?
    # tell specific robot to move straight towards given location
    def move_robot(self, robot_id, goal_pos):
        if robot_id not in self.robots:
            print("robot not available")
            return False
        
        if robot_id not in self.gamestate.robot_positions:
            print("robot not seen")
            return False
        
        robot = self.robots[robot_id]
        pos = self.gamestate.robot_positions[robot_id]
        og_x, og_y, og_w = pos
        goal_x, goal_y = goal_pos
        delta = (goal_x - og_x, goal_y - og_y)
        # normalized offsets from robot's perspective
        robot_x, robot_y = self._trans.transform(og_w, delta)

        if False:
            print("Original coordinates", og_x, og_y, og_w)
            print('Delta {}'.format(delta))
            print('(normalized diff) Robot X %f Robot Y %f' % (robot_x, robot_y))

        # move with speed proportional to delta
        speed = min(self._trans.magnitude(delta) * SPEED_SCALE, MAX_SPEED)
        self.gamestate.robot_waypoints[robot_id] = [goal_pos]
        robot.move(speed * robot_y, speed * robot_x, 0, COMMAND_DURATION)
        return True

    # tell robot to move towards goal pos greedily while avoiding obstacles
    # TODO: eventually factor things into different libraries?
    def greedy_path_find(self, robot_id, goal_pos):
        waypoint = goal_pos
        self.move_robot(robot_id, waypoint)
        return True
