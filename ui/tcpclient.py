# coding: utf-8

import socket

hote = "10.0.0.13"
port = 6038

socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket.connect((hote, port))
print("Connection on {}".format(port))

socket.send(u"Hey my name is Olivier!")

print("Close")
socket.close()