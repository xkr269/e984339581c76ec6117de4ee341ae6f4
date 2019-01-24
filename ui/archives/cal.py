import tellopy
from time import sleep
from math import atan2, pi, sqrt
import threading

drone = tellopy.Tello()
tello_address = ('192.168.10.1', 8889)

speed = 10
sleep_coef_fwd = 1.5
sleep_delay = 1
sleep_coef_turn = 10

def send_to_drone(msg):
    msg = msg.encode(encoding="utf-8") 
    sent = drone.sock.sendto(msg, tello_address)


def forward(distance):
    distance = int(distance * 100)
    msg = "forward " + str(distance)
    print(msg)
    send_to_drone(msg)
    print("start sleep")
    sleep(sleep_delay + distance * sleep_coef_fwd / 100)
    print("stop sleep")

def turn(angle): # en degrés
    angle = int(angle)
    if angle > 0:
        msg = "ccw " + str(angle)
        print(msg)
        send_to_drone(msg)
    else :
        msg = "cw " + str(abs(angle))
        print(msg)
        send_to_drone(msg)
    print("start sleep")
    sleep(sleep_delay + abs(angle) * sleep_coef_turn / 360)
    print("stop sleep")

drone.connect()
drone.wait_for_connection(60)

drone.takeoff()
print("takeoff")
print("start sleep")
sleep(5)
print("stop sleep")

print("send command")
send_to_drone("command")
print("start sleep")
sleep(sleep_delay + 1)
print("stop sleep")


# Waypoints (coordinates in meters)
nico = (0,1.5)
raph = (1.5,1.5)
benj = (0,-2)
audrey = (1.5,-2)
home_base = (0,0)

waypoints = [nico,raph,home_base]

current_position = home_base
current_angle = 0

def move_to(position):
    global current_position
    global current_angle

    # calcul du déplacement
    x = position[0] - current_position[0]
    y = position[1] - current_position[1]

    # calcul angle de rotation vs axe x
    a = atan2(y,x)*180/pi

    # angle de rotation corrigé
    b = a - current_angle

    # rotation
    turn(b)

    # update angle
    current_angle = a

    # distance à parcourir
    d = sqrt(x*x + y*y)

    # déplacement
    forward(d)

    # update position
    current_position = position


for position in waypoints:
    print("Moving to {}".format(position))
    move_to(position)

drone.land()
sleep(3)
drone.quit()
drone.sock.shutdown()
drone.sock.close()

