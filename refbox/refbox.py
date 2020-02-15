import socket
from struct import pack
import binascii
from ipaddress import ip_address
import threading
import time

# from referee_pb2 import SSL_Referee_Game_Event
from .referee_pb2 import SSL_Referee

class RefboxClient:
    
    def __init__(self, ip = '224.5.23.1', port=10003):
        self.ip = ip
        self.port = port


    def connect(self):
        """Binds the client with ip and port and configure to UDP multicast."""

        if not isinstance(self.ip, str):
            raise ValueError('IP type should be string type')
        if not isinstance(self.port, int):
            raise ValueError('Port type should be int type')
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, pack("=4sl", socket.inet_aton(self.ip), socket.INADDR_ANY))
        self.sock.bind((self.ip, self.port))

    def receive(self):
        """Receive package and decode."""
        data, _ = self.sock.recvfrom(1024)
        decoded_data = SSL_Referee.FromString(data)
        return decoded_data

    def disconnect(self):
        if self.sock:
            self.sock.close()

class RefboxDataProvider:
    def __init__(self, gamestate, ip = '224.5.23.1', port=10003):
        self._is_running = False
        self._client = None
        self._receive_data_thread = None
        self._update_gamestate_thread = None
        self._gamestate = gamestate
        self._ip = ip
        self._port = port
        self._latest_packet = None
        self._last_update_time = None
        self._vision_loop_sleep = None

    def start_updating(self, loop_sleep):
        if self._is_running:
            raise Exception('RefboxDataProvider is always running')
        self._is_running = True
        # Connect to client
        self._client = RefboxClient(self._ip, self._port)
        self._client.connect()
        # Receive data thread
        self._receive_data_thread = threading.Thread(
            target=self.receive_data_loop
        )
        self._receive_data_thread.daemon = True
        self._receive_data_thread.start()
        # Update gamestate thread
        self._update_gamestate_thread = threading.Thread(
            target=self.gamestate_update_loop
        )
        self._update_gamestate_thread.daemon = True
        self._update_gamestate_thread.start()

        self._vision_loop_sleep = loop_sleep

    def stop_updating(self):
        if self._client:
            self._client.disconnect()

        if self._is_running:
            self._is_running = False
            self._update_gamestate_thread.join()
            self._update_gamestate_thread = None
            self._receive_data_thread.join()
            self._receive_data_thread = None

        self._latest_packet = None
        

    def receive_data_loop(self):
        while self._is_running:
            self._latest_packet = self._client.receive()

    def gamestate_update_loop(self):
        # wait until game begins (while other threads are initializing)
        self._gamestate.wait_until_game_begins()
        while self._is_running:
            self._gamestate.latest_refbox_message = self._latest_packet

            if self._last_update_time is not None:
                delta = time.time() - self._last_update_time
                # print(delta)
                if delta > self._vision_loop_sleep * 3:
                    print("SSL-vision data loop large delay: " + str(delta))
            self._last_update_time = time.time()

            # yield to other threads
            time.sleep(self._vision_loop_sleep)
