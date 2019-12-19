import sslclient
import threading
import time
import logging
import numpy as np

logger = logging.getLogger(__name__)
'''
A class to provide robot position data from the cameras
'''


class SSLVisionDataProvider():
    def __init__(self, gamestate, HOST='224.5.23.2', PORT=10006):
        self.HOST = HOST
        self.PORT = PORT

        self._ssl_vision_client = None
        self._ssl_vision_thread = None
        # cache data from different cameras so we can merge them
        # camera_id : latest raw data
        self._raw_camera_data = {
            0: sslclient.messages_robocup_ssl_detection_pb2.SSL_DetectionFrame(),
            1: sslclient.messages_robocup_ssl_detection_pb2.SSL_DetectionFrame(),
            2: sslclient.messages_robocup_ssl_detection_pb2.SSL_DetectionFrame(),
            3: sslclient.messages_robocup_ssl_detection_pb2.SSL_DetectionFrame(),
        }

        self._gamestate = gamestate
        self._gamestate_update_thread = None
        self._is_running = False
        self._vision_loop_sleep = None
        self._last_update_time = None

    def start_updating(self, loop_sleep):
        self._is_running = True
        self._ssl_vision_client = sslclient.client()
        self._ssl_vision_client.connect()
        self._ssl_vision_thread = threading.Thread(
            target=self.receive_data_loop
        )
        # set to daemon mode so it will be easily killed
        self._ssl_vision_thread.daemon = True
        self._ssl_vision_thread.start()

        self._vision_loop_sleep = loop_sleep
        self._gamestate_update_thread = threading.Thread(
            target=self.gamestate_update_loop
        )
        # set to daemon mode so it will be easily killed
        self._gamestate_update_thread.daemon = True
        self._gamestate_update_thread.start()

    def stop_updating(self):
        if self._is_running:
            self._is_running = False
            self._gamestate_update_thread.join()
            self._gamestate_update_thread = None
            self._is_receiving = False
            self._ssl_vision_thread.join()
            self._ssl_vision_thread = None

    # loop for reading messages from ssl vision, otherwise they pile up
    def receive_data_loop(self):
        while self._is_running:
            data = self._ssl_vision_client.receive()
            # get a detection packet from any camera, and store it
            if data.HasField('detection'):
                self._raw_camera_data[data.detection.camera_id] = data.detection

    def gamestate_update_loop(self):
        # wait until game begins (while other threads are initializing)
        self._gamestate.wait_until_game_begins()
        while self._is_running:
            # update positions of all robots seen by data feed
            for team in ['blue', 'yellow']:
                robot_positions = self.get_robot_positions(team)
                # print(robot_positions)
                for robot_id, pos in robot_positions.items():
                    loc = np.array([pos.x, pos.y, pos.orientation])
                    self._gamestate.update_robot_position(team, robot_id, loc)
            # update position of the ball
            ball_data = self.get_ball_position()
            if ball_data:
                ball_pos = np.array([ball_data.x, ball_data.y])
                self._gamestate.update_ball_position(ball_pos)

            if self._last_update_time is not None:
                delta = time.time() - self._last_update_time
                # print(delta)
                if delta > self._vision_loop_sleep * 3:
                    print("SSL-vision data loop large delay: " + str(delta))
            self._last_update_time = time.time()

            # yield to other threads
            time.sleep(self._vision_loop_sleep)

    def get_robot_positions(self, team='blue'):
        robot_positions = {}
        for camera_id, raw_data in self._raw_camera_data.items():
            if team == 'blue':
                team_data = raw_data.robots_blue
            else:
                assert(team == 'yellow')
                team_data = raw_data.robots_yellow
            for robot_data in team_data:
                robot_id = robot_data.robot_id
                confidence = 0
                if robot_id in robot_positions:
                    confidence = robot_positions[robot_id].confidence
                # only update data if it has higher confidence
                if robot_data.confidence > confidence:
                    robot_positions[robot_id] = robot_data
                else:
                    # TODO: average?
                    pass
        return robot_positions

    def get_ball_position(self):
        # TODO: merge
        raw_data = self._raw_camera_data[0]
        balls = raw_data.balls
        if len(balls) == 0:
            return None
        elif len(balls) > 1:
            pass
            # print('More than one ball detected')
            # raise RuntimeError('More than one ball detected')
        return balls[0]
