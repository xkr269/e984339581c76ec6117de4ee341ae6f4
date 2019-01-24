import socket

UDP_IP = "10.0.0.12"
UDP_PORT = 6038
MESSAGE = "Hello, World!"

print("UDP target IP:{}".format(UDP_IP))
print("UDP target port:{}".format(UDP_PORT))
print("message:{}".format(MESSAGE))

sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
sock.sendto(bytes(MESSAGE,"utf-8"), (UDP_IP, UDP_PORT))