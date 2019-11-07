import numpy as np

FIELD_W = 9000
FIELD_H = 6000


class Strategy(object):
    """Logic for playing the game. Uses data from gamestate to calculate desired
       robot actions, and enters commands into gamestate to be sent by comms"""
    def __init__(self, gamestate, team):
        assert(team in ['blue', 'yellow'])
        self._team = team
        self._gamestate = gamestate

    # TODO: orient rotation?
    # tell specific robot to move straight towards given location
    def move_straight(self, robot_id, goal_pos):
        robot_commands = self._gamestate.get_robot_commands(self._team, robot_id)
        robot_commands.waypoints = [(goal_pos, None, None)]

    # RRT
    def RRT_path_find(self, robot_id, goal_pos, lim=1000):
        print("TODO: UPDATE RRT FUNCTION")
        assert(False)
        start_pos = self._gamestate.get_robot_position(robot_id)
        graph = {start_pos: []}
        prev = {start_pos: None}
        cnt = 0
        while cnt < lim:
            new_pos = (np.random.randint(0, FIELD_W), np.random.randint(0, FIELD_H))
            if np.random.random() < 0.05:
                new_pos = goal_pos

            if not self._gamestate.is_position_open(new_pos) or new_pos in graph:
                continue

            nearest_pos = get_nearest_pos(graph, new_pos)

            graph[new_pos].append(nearest_pos)
            graph[nearest_pos].append(new_pos)
            prev[new_pos] = nearest_pos

            if new_pos[:2] == goal_pos[:2]:
                break

            cnt += 1

        pos = get_nearest_pos(graph, goal_pos)  # get nearest position to goal in graph
        path = []
        while pos[:2] != start_pos[:2]:
            path.append(pos)
            pos = prev[pos]
        path.reverse()
        waypoints = [(pos, None, None) for pos in path]
        robot_commands = self._gamestate.get_robot_commands(self._team, robot_id)
        robot_commands.waypoints = waypoints

    def get_nearest_pos(graph, new_pos):
        rtn = None
        min_dist = float('inf')
        for pos in graph:
            dist = np.sqrt((new_pos[0] - pos[0]) ** 2 + (new_pos[1] - pos[1]) ** 2)
            if dist < min_dist:
                min_dist = dist
                rtn = pos
        return rtn
