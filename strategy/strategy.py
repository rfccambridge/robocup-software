import sys
import threading
import numpy as np
import time
from datetime import datetime
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

        # for reducing frequency of expensive calls
        # (this also helps reduce oscillation)
        self._last_RRT_times = {}  # robot_id : timestamp

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
        print("\nRunning strategy for {} team, mode: {}".format(
            self._team, self._mode)
        )
        if self._mode == "UI":
            print("""
            Using UI Controls!
            Robots:
            - Click to select
            - Click to set goal position (drag for direction)
            - 'd' to toggle dribbler
            - 'c' to charge kicker, 'k' to kick
            Ball (IF SIMULATING):
            - Click or 'b' to select
            - Click to place (drag for speed)
            """)

        if self._mode == "entry_video":
            print("2020 Registration Video Procedure!")
            self.video_phase = 1

    def stop_controlling(self):
        if self._is_controlling:
            self._is_controlling = False
            self._control_thread.join()
            self._control_thread = None

    def control_loop(self):
        # wait until game begins (while other threads are initializing)
        self._gamestate.wait_until_game_begins()
        while self._is_controlling:
            # run the strategy corresponding to the given mode
            if self._mode == "UI":
                self.UI()
            elif self._mode == "entry_video":
                self.entry_video()
            else:
                print('(unrecognized mode, doing nothing)')

            # tell all robots to refresh their speeds based on waypoints
            team_commands = self._gamestate.get_team_commands(self._team)
            team_commands = list(team_commands.items())
            for robot_id, robot_commands in team_commands:
                # stop the robot if we've lost track of it
                if self._gamestate.is_robot_lost(self._team, robot_id):
                    robot_commands.set_speeds(0, 0, 0)
                else:
                    # recalculate the speed the robot should be commanded at
                    pos = self._gamestate.get_robot_position(self._team, robot_id)
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
                # apply simple commands
                commands.is_charging = gs.user_charge_command
                commands.is_kicking = gs.user_kick_command
                commands.is_dribbling = gs.user_dribble_command                
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
                    # Use pathfinding
                    self.path_find(robot_id, goal_pos)

    def entry_video(self):
        reception_pos = np.array([3200, 0, 0])
        pass_velocity = 1000
        shoot_velocity = 2000
        if self.video_phase == 1:
            # robot 0 moves to midpoint of interception range to recieve ball
            intercept_range = self.intercept_range(0)
            if intercept_range is None:
                print("intercept Range is none")
                return
            intercept_point = (intercept_range[0]+intercept_range[1])/2
            intercept_angle = self.robot_face_ball(0)
            intercept_point = self._gamestate.dribbler_to_robot_pos(
                intercept_point,
                intercept_angle
            )
            self.set_dribbler(0, True)
            self.path_find(0, intercept_point)
            # robot 1 moves to pos to receive a pass
            reception_pos[2] = self.robot_face_ball(1)
            self.path_find(1, reception_pos)
            # start charging up
            self.charge_up_to(0, pass_velocity)
            if self._gamestate.ball_in_dribbler(self._team, 0):
                self.video_phase += 1
                print("!!! Moving to video phase {}".format(self.video_phase))
        elif self.video_phase == 2:
            # define ideal kicking position
            ball_pos = self._gamestate.get_ball_position()
            kick_pos = self.best_kick_pos(ball_pos, reception_pos)
            # robot 0 moves to ideal kicking position
            self.move_straight(0, kick_pos)
            if self.charge_up_to(0, pass_velocity) and \
               self.is_done_moving(0):  # and self.is_done_moving(1):
                self.video_phase += 1
                self.kick_ball(0)
                print("Moving to video phase {}".format(self.video_phase))
        elif self.video_phase == 3:
            self.set_dribbler(1, True)
            # robot 2 finds best pos to receive
            intercept_range = self.intercept_range(1)
            intercept_point = intercept_range[0]
            intercept_angle = self.robot_face_ball(1)
            intercept_point = self._gamestate.dribbler_to_robot_pos(
                intercept_point,
                intercept_angle
            )
            self.move_straight(1, intercept_point)
            self.charge_up_to(1, shoot_velocity)
            if self._gamestate.ball_in_dribbler(self._team, 1):
                self.video_phase += 1
                print("Moving to video phase {}".format(self.video_phase))
        elif self.video_phase == 4:
            # robot 1 moves to best kick pos to shoot
            goal = self._gamestate.get_attack_goal(self._team)
            center_of_goal = (goal[0]+goal[1]) / 2
            self.pivot_with_ball(1, center_of_goal)
            if self.charge_up_to(1, shoot_velocity) and \
               self._gamestate.ball_in_dribbler(self._team, 1):
                self.video_phase += 1
                print("Moving to video phase {}".format(self.video_phase))
        elif self.video_phase == 5:
            self.set_dribbler(1, False)
            self.kick_ball(1)
            self.video_phase += 1
        else:
            pass

    # returns whether we are done pivoting
    def pivot_with_ball(self, robot_id, face_pos):
        dribbler_pos = self._gamestate.dribbler_pos(self._team, robot_id)
        kick_pos = self.best_kick_pos(dribbler_pos, face_pos)
        robot_pos = self._gamestate.get_robot_position(self._team, robot_id)
        # pivot gradually towards kicking position
        angle = (kick_pos[2] + robot_pos[2]*2) / 3
        waypoint = self._gamestate.dribbler_to_robot_pos(dribbler_pos, angle)
        self.set_waypoints(1, [waypoint])
        if waypoint[2] < 0.001:
            return True
        else:
            return False

    def get_goal_pos(self, robot_id):
        commands = self._gamestate.get_robot_commands(self._team, robot_id)
        if not commands.waypoints:
            return None
        return commands.waypoints[-1]

    def charge_up_to(self, robot_id, kick_speed):
        commands = self._gamestate.get_robot_commands(self._team, robot_id)
        if commands.kick_velocity() < kick_speed:
            commands.is_charging = True
        else:
            commands.is_charging = False
        return not commands.is_charging  # return whether we are done charging

    def kick_ball(self, robot_id):
        commands = self._gamestate.get_robot_commands(self._team, robot_id)
        commands.is_kicking = True

    def set_dribbler(self, robot_id, is_dribbling):
        commands = self._gamestate.get_robot_commands(self._team, robot_id)
        commands.is_dribbling = is_dribbling

    # check if robot has arrived at final waypoint, angle included
    def is_done_moving(self, robot_id):
        robot_pos = self._gamestate.get_robot_position(self._team, robot_id)
        commands = self._gamestate.get_robot_commands(self._team, robot_id)
        waypoints = commands.waypoints
        if waypoints:
            destination = waypoints[-1]
            delta = destination - robot_pos
            linear_delta = np.linalg.norm(delta[:2])
            print(delta)
            LINEAR_THRESHOLD = 50
            ANGLE_THRESHOLD = .1
            return linear_delta < LINEAR_THRESHOLD and \
                abs(delta[2]) < ANGLE_THRESHOLD
        return True

    # tell specific robot to move straight towards given location
    def move_straight(self, robot_id, goal_pos):
        self.set_waypoints(robot_id, [goal_pos])

    def set_waypoints(self, robot_id, waypoints):
        current_pos = self._gamestate.get_robot_position(self._team, robot_id)
        commands = self._gamestate.get_robot_commands(self._team, robot_id)
        # print(waypoints)
        for i, p in enumerate(waypoints):
            assert(len(p) == 2 or len(p) == 3)
            if len(p) == 2:
                waypoints[i] = np.array([p[0], p[1], None])
        commands.set_waypoints(waypoints, current_pos)

    def append_waypoint(self, robot_id, goal_pos):
        current_pos = self._gamestate.get_robot_position(self._team, robot_id)
        commands = self._gamestate.get_robot_commands(self._team, robot_id)
        commands.append_waypoint(goal_pos, current_pos)

    # Deprecated for intercept range?
    def get_ball_interception_point(self, robot_id):
        robot_pos = self._gamestate.get_robot_position(self._team, robot_id)
        delta_t = .05
        time = 0
        while(True):
            interception_pos = self._gamestate.predict_ball_pos(time)
            separation_distance = np.linalg.norm(robot_pos[:2] - interception_pos)
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
    def robot_face_pos(self, robot_id, pos):
        robot_pos = self._gamestate.get_robot_position(self._team, robot_id)
        return self.face_pos(robot_pos, pos)

    def robot_face_ball(self, robot_id):
        return self.robot_face_pos(robot_id, self._gamestate.get_ball_position())

    def face_pos(self, facing_from_pos, facing_towards_pos):
        dx, dy = facing_towards_pos[:2] - facing_from_pos[:2]
        # use atan2 instead of atan because it takes into account x/y signs
        # to give angle from -pi to pi, instead of limiting to -pi/2 to pi/2
        angle = np.arctan2(dy, dx)
        return angle

    def is_path_blocked(self, s_pos, g_pos, robot_id, buffer_dist=50):
        s_pos = np.array(s_pos)[:2]
        g_pos = np.array(g_pos)[:2]

        if (g_pos == s_pos).all():
            return False
        # Check endpoint first to avoid worrying about step size in the loop
        if not self._gamestate.is_position_open(g_pos, self._team, robot_id):
            return True
        path = g_pos - s_pos
        norm_path = path / np.linalg.norm(path)
        STEP_SIZE = gs.ROBOT_RADIUS

        # step along the path and check if any points are blocked
        steps = int(np.floor(np.linalg.norm(path) / STEP_SIZE))
        for i in range(1, steps + 1):
            intermediate_pos = s_pos + norm_path * STEP_SIZE * i
            np.append(intermediate_pos, 0)
            if not self._gamestate.is_position_open(intermediate_pos, self._team, robot_id):
                return True
        return False

    def path_find(self, robot_id, goal_pos):
        if not self._gamestate.is_position_open(goal_pos, self._team, robot_id):
            print("cannot path find to blocked goal")
            return
        start_pos = self._gamestate.get_robot_position(self._team, robot_id)
        # always check if we can just go straight
        if not self.is_path_blocked(start_pos, goal_pos, robot_id, buffer_dist=150):
            self.move_straight(robot_id, np.array(goal_pos))
            return
        # now check if current waypoints are already going where we want
        current_goal = self.get_goal_pos(robot_id)
        is_same_goal = current_goal is not None and \
            np.array_equal(goal_pos[:2], current_goal[:2])
        commands = self._gamestate.get_robot_commands(self._team, robot_id)
        current_waypoints = [start_pos] + commands.waypoints
        current_path_collides = False
        for i in range(len(current_waypoints) - 1):
            wp, next_wp = current_waypoints[i], current_waypoints[i+1]
            if self.is_path_blocked(wp, next_wp, robot_id):
                current_path_collides = True
        # only rerun for same goal if long time has elapsed or path collides
        RRT_INTERVAL = 3  # mainly in case something very strange has happened              
        recently_called = robot_id in self._last_RRT_times and \
            time.time() - self._last_RRT_times[robot_id] < RRT_INTERVAL
        if is_same_goal and recently_called and not current_path_collides:
            return
        else:
            self._last_RRT_times[robot_id] = time.time()
            self.RRT_path_find(start_pos, goal_pos, robot_id)

    # RRT
    def RRT_path_find(self, start_pos, goal_pos, robot_id, lim=1000):
        goal_pos = np.array(goal_pos)
        start_pos = np.array(start_pos)
        graph = {tuple(start_pos): []}
        prev = {tuple(start_pos): None}
        cnt = 0
        while True:
            # use gamestate.random_position()
            new_pos = np.array(
                [np.random.randint(gs.FIELD_MIN_X, gs.FIELD_MAX_X),
                 np.random.randint(gs.FIELD_MIN_Y, gs.FIELD_MAX_Y),
                 0.0])
            if np.random.random() < 0.05:
                new_pos = goal_pos

            if not self._gamestate.is_position_open(new_pos, self._team, robot_id, buffer_dist=100) \
               or tuple(new_pos) in graph:
                continue

            nearest_pos = self.get_nearest_pos(graph, tuple(new_pos))
            extend_pos = self.extend(nearest_pos, new_pos, robot_id=robot_id)
            if extend_pos is None:
                continue

            graph[tuple(extend_pos)] = [nearest_pos]
            graph[nearest_pos].append(tuple(extend_pos))
            prev[tuple(extend_pos)] = nearest_pos

            if np.linalg.norm(extend_pos[:2] - goal_pos[:2]) < gs.ROBOT_RADIUS:
                break

            cnt += 1

        pos = self.get_nearest_pos(graph, goal_pos)  # get nearest position to goal in graph
        path = []
        while not (pos[:2] == start_pos[:2]).all():
            path.append(pos)
            pos = prev[pos]
        path.reverse()
        self.set_waypoints(robot_id, path + [goal_pos])

    def get_nearest_pos(self, graph, new_pos):
        rtn = None
        min_dist = float('inf')
        for pos in graph:
            dist = np.sqrt((new_pos[0] - pos[0]) ** 2 + (new_pos[1] - pos[1]) ** 2)
            if dist < min_dist:
                min_dist = dist
                rtn = pos
        return rtn

    def extend(self, s_pos, g_pos, robot_id=None):
        s_pos = np.array(s_pos)[:2]
        g_pos = np.array(g_pos)[:2]

        if (g_pos == s_pos).all():
            return False

        path = g_pos - s_pos
        norm_path = path / np.linalg.norm(path)
        STEP_SIZE = gs.ROBOT_RADIUS

        # step along the path and check if any points are blocked
        poses = [None]
        steps = int(np.floor(np.linalg.norm(path) / STEP_SIZE))
        for i in range(1, steps + 1):
            intermediate_pos = s_pos + norm_path * STEP_SIZE * i
            np.append(intermediate_pos, 0)
            if not self._gamestate.is_position_open(intermediate_pos, self._team, robot_id):
                break
            if np.linalg.norm(intermediate_pos - s_pos) > 4 * STEP_SIZE:
                break
            poses.append(intermediate_pos)

        return poses[-1]

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
        dx, dy = to_pos[:2] - from_pos[:2]
        w = np.arctan2(dy, dx)
        return self._gamestate.dribbler_to_robot_pos(from_pos, w)

    def intercept_range(self, robot_id):
        #print(f"start time: {datetime.now()}")
        #first_intercept_point = self.get_ball_interception_point(robot_id)
        # Now we find the last possible interception point.
        # We start with code very much like get_ball_interception_point so that we can start our time
        # variable at the time when the ball first gets within range.
        robot_pos = self._gamestate.get_robot_position(self._team, robot_id)
        delta_t = .1
        time = 0
        out_of_range = True
        while(out_of_range):
            interception_pos = self._gamestate.predict_ball_pos(time)
            separation_distance = np.linalg.norm(robot_pos[:2] - interception_pos)
            max_speed = self._gamestate.robot_max_speed(self._team, robot_id)
            if separation_distance <= time * max_speed:
                first_intercept_point = interception_pos
                if not self._gamestate.is_in_play(first_intercept_point):
                    return None
                out_of_range = False
            else:
                time += delta_t
        while(not out_of_range):
            # Note that time is starting at the time when the ball first got within range.
            interception_pos = self._gamestate.predict_ball_pos(time)
            separation_distance = np.linalg.norm(robot_pos[:2] - interception_pos)
            max_speed = self._gamestate.robot_max_speed(self._team, robot_id)
            last_intercept_point = self._gamestate.predict_ball_pos(time - delta_t)
            # We have the opposite criteria to find the end of the window than the beginning.
            cant_reach = (separation_distance > time * max_speed)
            stopped_moving = (last_intercept_point == interception_pos).all()
            in_play = self._gamestate.is_in_play(interception_pos)
            if cant_reach or stopped_moving or not in_play:
                # we need to subtract delta_t because we found the last
                #print(f"end time: {datetime.now()}")
                return first_intercept_point, last_intercept_point
            else:
                time += delta_t
