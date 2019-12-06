from socket import socket, AF_INET, SOCK_DGRAM, IPPROTO_IP, IP_ADD_MEMBERSHIP, inet_aton, INADDR_ANY, SOL_SOCKET, SO_REUSEADDR
from struct import pack
import binascii
from ipaddress import ip_address

from referee_pb2 import SSL_Referee

class RefboxClient:
    
    def __init__(self, ip = '224.5.23.1', port=10003):
        self.ip = ip
        self.port = port

    def connect(self):
        """Binds the client with ip and port and configure to UDP multicast."""

        connection_info = (self.ip, self.port)

        if not isinstance(self.ip, str):
            raise ValueError('IP type should be string type')
        if not isinstance(self.port, int):
            raise ValueError('Port type should be int type')
        
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        # For some reason with Ubuntu on Windows (WSL) you need to first bind to 0.0.0.0, before changing the address
        self.sock.bind(('0.0.0.0', connection_info[1]))

        if ip_address(connection_info[0]).is_multicast:
            self.sock.setsockopt(IPPROTO_IP, IP_ADD_MEMBERSHIP, pack('=4sl', inet_aton(connection_info[0]), INADDR_ANY))
        
    def receive(self):
        """Receive package and decode."""
        packet = SSL_Referee()

        data = self.sock.recv(1024)

        packet.ParseFromString(data)
        print(packet)