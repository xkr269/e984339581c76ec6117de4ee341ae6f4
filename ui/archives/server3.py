import socket

socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socket.bind(('', 6038))

while True:
        data, address = socket.recvfrom(2000)
        print("{} received from {}".format(data,address))


print("Close")
client.close()
stock.close()