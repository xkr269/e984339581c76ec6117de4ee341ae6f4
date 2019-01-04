import tellopy
import json
import time
from confluent_kafka import Producer, Consumer, KafkaError



# zones coordinates (in meter)
zones = {}
zones["toureiffel"] = (1,1)
zones["home_base"] = (0,0)
zones["notredame"] = (1,0)
zones["arcdetriomphe"] = (0,1)
zones["sacrecoeur"] = (2,0)
zones["montparnasse"] = (0,2)
zones["geode"] = (2,1)
zones["republique"] = (1,2)

default_speed = 35 # in % of max speed
time_shift = 1 # time multiplier ratio

def move(drone,from_zone,drop_zone):
    print("moving from {} to {}".format(from_zone,drop_zone))
    # horizontal move

    if from_zone == "home_base" and drop_zone == "home_base":
        drone.quit()
        exit()

    if from_zone == "home_base":
        drone.takeoff()
        time.sleep(5)


    x_move = zones[drop_zone][0] - zones[from_zone][0]
    y_move = zones[drop_zone][1] - zones[from_zone][1]
    print("x_move = {}, y_move = {}".format(x_move,y_move))
    if x_move > 0 :
        drone.right(default_speed)
        print("sleep for {} ".format(abs(x_move)))
        time.sleep(abs(x_move) * time_shift)
        drone.right(0)
    elif x_move < 0 :
        drone.left(default_speed)
        time.sleep(abs(x_move)* time_shift)
        drone.left(0)

    time.sleep(1)

    if y_move > 0 :
        drone.forward(default_speed)
        time.sleep(abs(y_move)* time_shift)
        drone.forward(0)
    elif y_move < 0 :
        drone.backward(default_speed)
        time.sleep(abs(y_move)* time_shift)
        drone.backward(0)

    time.sleep(1)

    if drop_zone == "home_base":
        drone.land()
        time.sleep(5)




def main():
    drone = tellopy.Tello()
    try:
        # Connect to the drone
        print("Connecting to drone")
        drone.connect()
        drone.wait_for_connection(600.0)
        print("Connected")

        # Poll positions stream
        POSITIONS_STREAM_PATH = '/mapr/demo.mapr.com/positions_stream'   # Positions stream path

        c = Consumer({'group.id': "defgroup",'default.topic.config': {'auto.offset.reset': 'latest'}})
        c.subscribe([POSITIONS_STREAM_PATH + ":positions"])
        nb_moves = 0
        while nb_moves < 5 :
          msg = c.poll()
          if msg is None :
            continue
          if not msg.error():
            print("message received")
            print(msg.value())
            value = json.loads(msg.value())
            from_zone = value["from_zone"]
            drop_zone = value["drop_zone"]
            move(drone,from_zone,drop_zone)
            nb_moves += 1

          elif msg.error().code() != KafkaError._PARTITION_EOF:
            print(msg.error())


    # Catch exceptions
    except Exception as ex:
        #exc_type, exc_value, exc_traceback = sys.exc_info()
        #traceback.print_exception(exc_type, exc_value, exc_traceback)
        print(ex)

    # Clean exit w/landing + disconnect
    finally:
        print('Disconnecting...')
        drone.land()
        drone.quit()

    drone.land()
    drone.quit()

if __name__ == '__main__':
    # Launch main
    main()
