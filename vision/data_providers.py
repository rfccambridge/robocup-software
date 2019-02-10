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
    _client = None
    _thread = None

    def __init__(self, HOST='224.5.23.2', PORT=10006):
        self.HOST = HOST
        self.PORT = PORT


    def start(self):
        self._client = sslclient.client()
        self._client.connect()
        self._thread = DataThread(self._client)
        self._thread.start()
        # BUG: sensible defaults when data hasn't loaded yet (@dinge)
        time.sleep(0.1)

    def stop(self):
        self._thread.stop()
        self._thread.join()
        self._client = None

    def get_raw_detection_data(self):
        return self._thread.detection_cache

    def get_raw_geometry_data(self):
        return self._thread.geometry_cache

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
            print('More than one ball detected')
            # raise RuntimeError('More than one ball detected')
        return balls[0]

    
