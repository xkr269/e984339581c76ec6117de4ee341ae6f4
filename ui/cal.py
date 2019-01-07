import tellopy
from time import sleep


drone = tellopy.Tello()


def forward(distance):
    drone.right(20)
    sleep(distance*2)
    print("forward 0")
    drone.forward(0)
    print("done")
    sleep(2)

drone.connect()
drone.wait_for_connection(60)

drone.takeoff()
print("takeoff")
sleep(5)

forward(2)

drone.land()
sleep(3)
drone.quit()

