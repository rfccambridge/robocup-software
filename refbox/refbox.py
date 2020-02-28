import socket
from struct import pack
import binascii
from ipaddress import ip_address
import threading
import time
from coordinator import Provider

# from referee_pb2 import SSL_Referee_Game_Event
from .referee_pb2 import SSL_Referee

class RefboxClient:
    """
    A client class to get information from the refbox.
    """
    def __init__(self, ip='224.5.23.1', port=10003):
        """
        Creates a RefboxClient object

        Args:
            ip (str, optional): The ip to listen to refbox messages on. Defaults to '224.5.23.1'.
            port (int, optional): The port to listen for refbox messages on. Defaults to 10003.
        """
        self.ip = ip
        self.port = port


    def connect(self):
        """
        Connects to the socket but doesn't start receiving packets yet

        Raises:
            ValueError: If IP is not string
            ValueError: If port is not int type
        """

        if not isinstance(self.ip, str):
            raise ValueError('IP type should be string type')
        if not isinstance(self.port, int):
            raise ValueError('Port type should be int type')

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.settimeout(0.1)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, pack("=4sl", socket.inet_aton(self.ip), socket.INADDR_ANY))
        self.sock.bind((self.ip, self.port))

    def receive(self):
        """
        Receive a single packet from the refbox

        Returns:
            SSL_Referee: The protobuf message from the refbox
        
        Raises:
            socket.timeout exception if no packets are received
        """
        data, _ = self.sock.recvfrom(1024)
        decoded_data = SSL_Referee.FromString(data)
        return decoded_data

    def disconnect(self):
        """
        Closes the socket
        """
        if self.sock:
            self.sock.close()

class RefboxDataProvider(Provider):
    """
    A wrapper around a RefboxClient to help update a gamestate object
    """
    def __init__(self, ip='224.5.23.1', port=10003):
        """
        Creates a RefboxDataProvider object

        Args:
            gamestate (GameState): The gamestate object which we should update the state of
            ip (str, optional): The IP address to listen for messages on. Defaults to '224.5.23.1'.
            port (int, optional): The port to listen for messages. Defaults to 10003.
        """
        super().__init__()
        self._client = None
        self._receive_data_thread = None
        self._ip = ip
        self._port = port
        self._owned_fields = ['latest_refbox_message_string']

    def pre_run(self):
        """
        Start updating the gamestate with the latest info.
        """
        # Connect to client
        try:
            self._client = RefboxClient(self._ip, self._port)
            self._client.connect()
        except Exception:
            self.logger.exception("failed to connect to refbox")
            raise

    def post_run(self):
        """
        Stop updating the gamestate and close the client
        """
        if self._client:
            self._client.disconnect()
        self._client = None

    def run(self):
        """
        A loop to receive the latest packets.
        """
        try:
            self.gs.latest_refbox_message_string = self._client.receive().SerializeToString()
        except socket.timeout:
            pass