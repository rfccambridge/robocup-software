import socket
from struct import pack
import binascii
from ipaddress import ip_address

# from referee_pb2 import SSL_Referee_Game_Event
from referee_pb2 import SSL_Referee

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

       
    """
        host = socket.gethostbyname(socket.gethostname())
        self.sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(host))
        self.sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, 
                socket.inet_aton(self.ip) + socket.inet_aton(host))
 """

    def receive(self):
        """Receive package and decode."""

        data, _ = self.sock.recvfrom(1024)
        decoded_data = SSL_Referee.FromString(data)
        return decoded_data