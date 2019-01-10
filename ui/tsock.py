import socket
import time
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
port = 6038
sock.bind(('', port))
time.sleep(10)
sock.close()
