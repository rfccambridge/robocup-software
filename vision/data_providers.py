import socket
import sslclient
import threading
import time
import logging

logger = logging.getLogger(__name__)
'''
A class to provide robot position data from the cameras
'''
from enum import Enum

class PositionDataProvider(object):

    def get_robot_position(self, robot_id, team='blue'):
        raise NotImplementedError()

    def get_raw_detection_data(self):
        raise NotImplementedError()

    def get_raw_geometry_data(self):
        raise NotImplementedError()

    def get_ball_position(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()

    def start(self):
        raise NotImplementedError()


class DataThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, client):
        super(DataThread, self).__init__()
        self._stop_event = threading.Event()
        self.geometry_cache = {}
        self.detection_cache = sslclient.messages_robocup_ssl_detection_pb2.SSL_DetectionFrame()
        self._client = client

    def run(self):
        while not self._stop_event.is_set():
            #received decoded package
            data = self._client.receive()
            if data.HasField('geometry'):
                self.geometry_cache = data.geometry
            
            if data.HasField('detection'):
                self.detection_cache = data.detection

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

class SSLVisionDataProvider(PositionDataProvider):
    def __init__(self, gamestate, HOST='224.5.23.2', PORT=10006):        
        self.HOST = HOST
        self.PORT = PORT

        self._ssl_vision_client = None
        self._ssl_vision_client_thread = None
        
        self._gamestate = gamestate
        self._gamestate_update_thread = None
        self._is_running = False
        self._last_update_time = None

    def gamestate_update_loop(self):
        while self._is_running:
            # update positions of all (blue team) robots seen by data feed
            robot_positions = self.get_robot_positions()
            for robot_id, pos in robot_positions.items():
                loc = pos.x, pos.y, pos.orientation
                self._gamestate.update_robot_position(robot_id, loc)
            # update position of the ball
            ball_data = self.get_ball_position()
            if ball_data:
                self._gamestate.update_ball_position((ball_data.x, ball_data.y))
                
            if self._last_update_time is not None:                
                delta = time.time() - self._last_update_time
                if delta > .1:
                    print("SSL-vision data loop unexpectedly large delay: " + str(delta))
            self._last_update_time = time.time()            
            
            # yield to other threads - run this loop at most 100 times per second
            time.sleep(.01)
        
    def start(self):
        self._is_running = True
        self._ssl_vision_client = sslclient.client()
        self._ssl_vision_client.connect()
        self._ssl_vision_client_thread = DataThread(self._ssl_vision_client)
        self._ssl_vision_client_thread.start()
        # BUG: sensible defaults when data hasn't loaded yet (@dinge)
        time.sleep(0.1)
        self._gamestate_update_thread = threading.Thread(target=self.gamestate_update_loop)
        self._gamestate_update_thread.start()

    def stop(self):
        self._is_running = False
        self._gamestate_update_hread.join()
        self._gamestate_update_thread = None
        self._ssl_vision_client_thread.stop()
        self._ssl_vision_client_thread.join()
        self._ssl_vision_client = None

    def get_raw_detection_data(self):
        return self._ssl_vision_client_thread.detection_cache

    def get_raw_geometry_data(self):
        return self._ssl_vision_client_thread.geometry_cache

    def get_robot_positions(self, team='blue'):
        raw_data = self.get_raw_detection_data()
        if team == 'blue':
            team_data = raw_data.robots_blue
        else:
            team_data = raw_data.robots_yellow
        robot_positions = {}
        for robot_data in team_data:
            robot_positions[robot_data.robot_id] = robot_data
        return robot_positions

    def get_robot_position(self, robot_id, team='blue'):
        raw_data = self.get_raw_detection_data()
        if team == 'blue':
            data = raw_data.robots_blue
        else:
            data = raw_data.robots_yellow

        for robot_data in data:
            if robot_data.robot_id == robot_id:
                return robot_data
        logger.debug("No vision data found for robot id %d" % robot_id)
        return None

    def get_ball_position(self):
        balls = self.get_raw_detection_data().balls
        if len(balls) == 0:
            return None
        elif len(balls) > 1:
            pass
            # print('More than one ball detected')
            # raise RuntimeError('More than one ball detected')
        return balls[0]

    
