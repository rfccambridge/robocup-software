import threading
import numpy as np
import time


class Strategy(object):
    """Logic for playing the game. Uses data from gamestate to calculate desired
       robot actions, and enters commands into gamestate to be sent by comms"""
    def __init__(self, gamestate, team):
        assert(team in ['blue', 'yellow'])
        self._team = team
        self._gamestate = gamestate

        self._is_controlling = False
        self._control_thread = None
        self._control_loop_sleep = None
        self._last_control_loop_time = None
        self._mode = None

    def start_controlling(self, mode, loop_sleep):
        self._mode = mode
        self._control_loop_sleep = loop_sleep
        self._is_controlling = True
        self._control_thread = threading.Thread(target=self.control_loop)
        # set to daemon mode so it will be easily killed
        self._control_thread.daemon = True
        self._control_thread.start()

    def stop_controlling(self):
        if self._is_controlling:
            self._is_controlling = False
            self._control_thread.join()
            self._control_thread = None

    def control_loop(self):
        # wait until game begins (while other threads are initializing)
        self._gamestate.wait_until_game_begins()
        print("\nRunning strategy for {} team, mode: {}".format(
            self._team, self._mode)
        )
        while self._is_controlling:
            # run the strategy corresponding to the given mode
            if self._mode == "UI":
                self.UI()
            else:
                print('(unrecognized mode, doing nothing)')

            # tell all robots to refresh their speeds based on waypoints
            team_commands = self._gamestate.get_team_commands(self._team)
            team_commands = list(team_commands.items())
            for robot_id, robot_commands in team_commands:
                pos = self._gamestate.get_robot_position(self._team, robot_id)
                # stop the robot if we've lost track of it
                if self._gamestate.is_robot_lost(self._team, robot_id):
                    robot_commands.set_speeds(0, 0, 0)
                else:
                    # recalculate the speed the robot should be commanded at
                    robot_commands.derive_speeds(pos)

            if self._last_control_loop_time is not None:
                delta = time.time() - self._last_control_loop_time
                if delta > self._control_loop_sleep * 3:
                    print("Control loop large delay: " + str(delta))
            self._last_control_loop_time = time.time()
            # yield to other threads
            time.sleep(self._control_loop_sleep)

    # follow the user-input commands through visualizer
    def UI(self):
        # set goal pos to click location on visualization window
        if self._gamestate.user_click_position is not None:
            goal_pos = self._gamestate.user_click_position
            if self._gamestate.user_selected_robot is not None:
                team, robot_id = self._gamestate.user_selected_robot
                if team == self._team:
                    # self.move_straight(robot_ids[0], np.array(goal_pos))
                    self.append_waypoint(robot_id, np.array(goal_pos))

    # tell specific robot to move straight towards given location
    def move_straight(self, robot_id, goal_pos):
        current_pos = self._gamestate.get_robot_position(self._team, robot_id)
        commands = self._gamestate.get_robot_commands(self._team, robot_id)
        commands.set_waypoints([goal_pos], current_pos)

    def append_waypoint(self, robot_id, goal_pos):
        current_pos = self._gamestate.get_robot_position(self._team, robot_id)
        commands = self._gamestate.get_robot_commands(self._team, robot_id)
        commands.append_waypoint(goal_pos, current_pos)

    # RRT
    def RRT_path_find(self, robot_id, goal_pos, lim=1000):
        print("TODO: UPDATE RRT FUNCTION")
        assert(False)
        start_pos = self._gamestate.get_robot_position(robot_id)
        graph = {start_pos: []}
        prev = {start_pos: None}
        cnt = 0
        while cnt < lim:
            # use gamestate.random_position()
            new_pos = (np.random.randint(0, FIELD_W), np.random.randint(0, FIELD_H))
            if np.random.random() < 0.05:
                new_pos = goal_pos

            # use gamestate.is_pos_valid
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
        waypoints = [pos for pos in path]
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
