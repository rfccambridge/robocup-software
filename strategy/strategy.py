class Strategy(object):
    """Logic for playing the game. Uses data from gamestate to calculate desired
       robot actions, and enters commands into the gamestate to be sent by comms"""
    def __init__(self, gamestate):
        self._gamestate = gamestate

    # TODO: orient rotation?
    # tell specific robot to move straight towards given location
    def move_straight(self, robot_id, goal_pos):
        self._gamestate.robot_waypoints[robot_id] = [(goal_pos, None, None)]
        
    # tell robot to move towards goal pos greedily while avoiding obstacles
    # TODO: eventually factor things into different libraries?
    def greedy_path_find(self, robot_id, goal_pos):
        waypoint = (goal_pos, None, None)
        self.move_straight(robot_id, waypoint)
        return True
