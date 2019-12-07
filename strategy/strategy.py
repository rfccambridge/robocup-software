import sys
import threading
import numpy as np
import time
# import gamestate file to use field dimension constants
# (as opposed to importing the class GameState)
sys.path.append('..')
from gamestate import gamestate as gs


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
        gs = self._gamestate
        if gs.user_selected_robot is not None:
            team, robot_id = gs.user_selected_robot
            if team == self._team:
                commands = gs.get_robot_commands(self._team, robot_id)
                # set goal pos to click location on visualization window
                if gs.user_click_position is not None:
                    x, y = gs.user_click_position
                    if gs.user_drag_vector.any():
                        # face the dragged direction
                        dx, dy = gs.user_drag_vector
                        w = np.arctan2(dy, dx)
                    else:
                        w = None
                    goal_pos = np.array([x, y, w])
                    # self.move_straight(robot_ids[0], np.array(goal_pos))
                    self.append_waypoint(robot_id, np.array(goal_pos))
                # apply other commands
                commands.is_charging = gs.user_charge_command
                commands.is_kicking = gs.user_kick_command
                commands.is_dribbling = gs.user_dribble_command

    # tell specific robot to move straight towards given location
    def move_straight(self, robot_id, goal_pos):
        current_pos = self._gamestate.get_robot_position(self._team, robot_id)
        commands = self._gamestate.get_robot_commands(self._team, robot_id)
        commands.set_waypoints([goal_pos], current_pos)

    def append_waypoint(self, robot_id, goal_pos):
        current_pos = self._gamestate.get_robot_position(self._team, robot_id)
        commands = self._gamestate.get_robot_commands(self._team, robot_id)
        commands.append_waypoint(goal_pos, current_pos)

    def get_ball_interception_point(self, robot_id):
        robot_pos = self._gamestate.get_robot_position(self._team, robot_id)
        delta_t = .05
        time = 0
        while(True):
            interception_pos = self._gamestate.predict_ball_pos(time)
            separation_distance = np.linalg.norm(robot_pos - interception_pos)
            max_speed = self._gamestate.robot_max_speed(self._team, robot_id)
            if separation_distance <= time * max_speed:
                return interception_pos
            else:
                time += delta_t

    def best_goalie_pos(self):
        ball_pos = self._gamestate.get_ball_position()
        goal_top, goal_bottom = self._gamestate.get_defense_goal(self._team)
        goal_center = (goal_top + goal_bottom) / 2
        # for now, look at vector from goal center to ball
        goal_to_ball = ball_pos - goal_center
        if not goal_to_ball.any():
            # should never happen, but good to prevent crash, and for debugging
            print('ball is exactly on goal center w0t')
            return np.array([*goal_center, 0])
        angle_to_ball = np.arctan2(goal_to_ball[1], goal_to_ball[0])
        norm_to_ball = goal_to_ball / np.linalg.norm(goal_to_ball)
        GOALIE_OFFSET = 600  # goalie stays this far from goal center
        x, y = goal_center + norm_to_ball * GOALIE_OFFSET
        best_pos = np.array([x, y, angle_to_ball])
        return best_pos

    # Return angle (relative to the x axis) for robot to face a position
    def face_pos(self, robot_id, pos):
        robot_pos = self._gamestate_get_robot_position(self._team, robot_id)
        dx, dy = pos - robot_pos
        # use atan2 instead of atan because it takes into account x/y signs
        # to give angle from -pi to pi, instead of limiting to -pi/2 to pi/2
        return np.arctan2(dy, dx)

    def face_ball(self, robot_id):
        return self.face_pos(robot_id, self._gamestate.get_ball_position())

    def is_path_blocked(self, s_pos, g_pos):
        if (g_pos == s_pos).all():
            return False
        # Check endpoint first to avoid worrying about step size in the loop
        if not self._gamestate.is_position_open(g_pos):
            return True
        path = g_pos - s_pos
        norm_path = path / np.linalg.norm(path)
        STEP_SIZE = gs.ROBOT_RADIUS
        # step along the path and check if any points are blocked
        for i in range(np.linalg.norm(path) / STEP_SIZE):
            intermediate_pos = s_pos + norm_path * STEP_SIZE * i
            if not self.is_position_open(intermediate_pos):
                return True
        return False

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

# determine best robot position (including rotation) to shoot or pass ie kick given the position or desired future location
# of the ball (x,y) after the kick and before the kick (self, from_pos, to_pos)
# determine location of robot including rotation to recieve as pass given
# rotation to recieve the ball in current pos
# go to the ball (and rotate to receive it)
# assume the ball has already been kicked. add a buffer... "relax" parameter
# min and max distance to ball path while still intercept
# posssible interception points (first_intercept_point, last_intercept point) ****important edge case: ball stops in range
# determine best robot position (including rotation) to shoot or pass ie kick given the position or desired future location
# of the ball (x,y) after the kick and before the kick (self, from_pos, to_pos)
    def best_kick_pos(self, from_pos, to_pos):
        x = from_pos[0]
        y = from_pos[1]
        dx, dy = to_pos - from_pos
        w = np.arctan2(dy, dx)
        return self._gamestate.dribbler_to_robot_pos(from_pos, w)

    def intercept_range(self, robot_id):
        first_intercept_point = self.get_ball_interception_point(robot_id)
        # Now we find the last possible interception point.
        # We start with code very much like get_ball_interception_point so that we can start our time
        # variable at the time when the ball first gets within range.
        robot_pos = self._gamestate.get_robot_position(self._team, robot_id)
        delta_t = .05
        time = 0
        out_of_range = True
        while(out_of_range):
            interception_pos = self._gamestate.predict_ball_pos(time)
            separation_distance = np.linalg.norm(robot_pos - interception_pos)
            max_speed = self._gamestate.robot_max_speed(self._team, robot_id)
            if separation_distance <= time * max_speed:
                out_of_range = False
            else:
                time += delta_t
        while(not out_of_range):
            # Note that time is starting at the time when the ball first got within range.
            interception_pos = self._gamestate.predict_ball_pos(time)
            separation_distance = np.linalg.norm(robot_pos - interception_pos)
            max_speed = self._gamestate.robot_max_speed(self._team, robot_id)
            # We have the opposite criteria to find the end of the window than the beginning.
            if separation_distance > time * max_speed:
                # we need to subtract delta_t because we found the last
                last_intercept_point = self._gamestate.predict_ball_pos(time - delta_t)
                out_of_range = True
            else:
                time += delta_t
        return np.array([first_intercept_point, last_intercept_point])
