#! /usr/bin/python

"""
Pilot application for TEITS demo

What it does :
- Connects to the drone
- Gets the video
- Stores each frame in a folder
- Stores frame indexes in a stream (video_stream) in a topic named with drone id
- reads movements instructions from a stream

What has to be defined :
- the drone ID
- FPS for the transmitted video
- the project folder on the cluster

"""

import traceback
import time
from time import sleep
import os
import sys
import av
import tellopy
import json
import threading
from random import randint
from confluent_kafka import Producer, Consumer, KafkaError
from mapr.ojai.storage.ConnectionFactory import ConnectionFactory
from math import atan2, sqrt, pi, floor


DRONE_ID = sys.argv[1]
FPS = 5.0
PROJECT_FOLDER = "/teits"
DIRECTIONAL_MODE = "FORWARD" # LINEAR (only x & y moves), OPTIMIZED (minimizes turns) or FORWARD (turns and forward)
FORWARD_COEF = 3 # Time taken to move 1m
ANGULAR_COEF = 8.0 # Time taken to rotate 360 deg
MAX_FLIGHT_TIME = 300 # seconds


def get_cluster_name():
  with open('/opt/mapr/conf/mapr-clusters.conf', 'r') as f:
    first_line = f.readline()
    return first_line.split(' ')[0]

def check_stream(stream_path):
  if not os.path.islink(stream_path):
    print("stream {} is missing. Exiting.".format(stream_path))
    sys.exit()
    
cluster_name = get_cluster_name()

ROOT_PATH = '/mapr/' + cluster_name + PROJECT_FOLDER

IMAGE_FOLDER = ROOT_PATH + "/" + DRONE_ID + "/images/source/"
VIDEO_STREAM = ROOT_PATH + "/video_stream"
POSITIONS_STREAM = ROOT_PATH + "/positions_stream"
FLIGHT_DATA_STREAM = ROOT_PATH + "/flight_data_stream"
DRONEDATA_TABLE = ROOT_PATH + "/dronedata_table"
ZONES_TABLE = ROOT_PATH + "/zones_table"
POSITIONS_TABLE = ROOT_PATH + "/positions_table"

current_angle = 0

# Create database connection
connection_str = "10.0.0.11:5678?auth=basic;user=mapr;password=mapr;ssl=false"
connection = ConnectionFactory().get_connection(connection_str=connection_str)
zones_table = connection.get_or_create_store(ZONES_TABLE)
positions_table = connection.get_or_create_store(POSITIONS_TABLE)
dronedata_table = connection.get_or_create_store(DRONEDATA_TABLE)
dronedata_table.insert_or_replace({"_id":DRONE_ID,"flight_data":"unset","log_data":"unset","count":0})

# test if folders exist and create them if needed
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

# create sreams if needed
check_stream(VIDEO_STREAM)
check_stream(POSITIONS_STREAM)
check_stream(FLIGHT_DATA_STREAM)



#######################    VIDEO PROCESSING    ##################

# Function for transfering the video frames to FS and Stream
def get_drone_video(drone):
    global FPS
    global DRONE_ID
    global VIDEO_STREAM
    global IMAGE_FOLDER
    print("producing into {}".format(VIDEO_STREAM))
    video_producer = Producer({'streams.producer.default.stream': VIDEO_STREAM})
    current_sec = 0
    last_frame_time = 0
    container = av.open(drone.get_video_stream())
    try:
        start_time = time.time()
        received_frames = 0
        sent_frames = 0
        while True:
            print("video loop")
            for frame in container.decode(video=0):
                received_frames += 1
                current_time = time.time()
                if current_time > (last_frame_time + float(1/FPS)):
                    print(frame)
                    frame.to_image().save(IMAGE_FOLDER + "frame-{}.jpg".format(frame.index))
                    video_producer.produce(DRONE_ID+"_raw", json.dumps({"index":frame.index,"image":IMAGE_FOLDER + "frame-{}.jpg".format(frame.index)}))
                    sent_frames += 1
                    last_frame_time = time.time()

                # Print stats every second
                elapsed_time = time.time() - start_time
                if int(elapsed_time) != current_sec:
                    print("Elapsed : {} s, received {} fps , sent {} fps".format(elapsed_time,received_frames,sent_frames))
                    received_frames = 0
                    sent_frames = 0
                    current_sec = int(elapsed_time)

    # Catch exceptions
    except Exception as ex:
        print(ex)


#######################    MOVE PROCESSING    ##################

def move_to_zone(drone,start_zone,drop_zone):
    global current_angle
    print("###############      moving from {} to {}".format(start_zone,drop_zone))
    # get start_zone coordinates
    current_position_document = zones_table.find_by_id(start_zone)
    current_position = (float(current_position_document["x"]),float(current_position_document["y"]))
    # get drop_zone coordinates
    new_position_document = zones_table.find_by_id(drop_zone)
    new_position = (float(new_position_document["x"]),float(new_position_document["y"]))

    # calcul du deplacement
    y = new_position[1] - current_position[1] # Back and Front
    x = new_position[0] - current_position[0] # Left and Right

    if DIRECTIONAL_MODE == "LINEAR" :
        if y > 0:
            drone.forward(y)
        elif y < 0:
            drone.backward(-y)
        if y != 0:
            print("Sleep {}".format(abs(FORWARD_COEF*y)))
            time.sleep(max(1,abs(FORWARD_COEF*y)))

        if x > 0:
            drone.right(x)
        elif x < 0:
            drone.left(-x)
        if x != 0:
            print("Sleep {}".format(abs(FORWARD_COEF*x)))
            time.sleep(max(1,abs(FORWARD_COEF*x)))
    else:
        # calcul angle de rotation vs axe Y   
        target_angle = (atan2(x,y)*180/pi + 180) % 360 - 180

        print("drone orientation : {}".format(current_angle))
        print("target angle : {}".format(target_angle))

        angle =  (target_angle - current_angle + 180) % 360 - 180 
        print("direction vs drone : {}".format(angle))

        if DIRECTIONAL_MODE == "OPTIMIZED":
            # calcul du cadran
            cadran = int(floor(angle/45))
            print("cadran = {}".format(cadran))

            # calcul offset et deplacement
            if cadran in [-1,0]:
                offset = angle
                move = drone.forward
            elif cadran in [1,2]:
                offset = angle - 90
                move = drone.right
            elif cadran in [-4,3]:
                offset = (angle + 90) % 180 - 90
                move = drone.backward
            elif cadran in [-2,-3]:
                offset = angle + 90
                move = drone.left

            print("offset : {}".format(offset))
            print("move : {}".format(move))

        elif DIRECTIONAL_MODE == "FORWARD":
            move = drone.forward
            offset = angle 
            print("forward mode, offset : {}".format(offset))

        # distance a parcourir
        distance = sqrt(x*x + y*y)

        print("distance : {}".format(distance))

        if abs(offset) > 0:
            print("###############      turning {} degrees".format(angle))
            drone.turn(offset)
            print("sleep {}".format(max(1,float(abs(offset) * ANGULAR_COEF / 360))))
            time.sleep(max(1,float(abs(offset) * ANGULAR_COEF / 360)))

        # deplacement        
        if distance > 0 :
            move(distance)
            print("sleep {}".format(max(1,distance * FORWARD_COEF)))
            time.sleep(max(1,distance * FORWARD_COEF))

        current_angle += offset

    positions_table.insert_or_replace(doc={'_id': DRONE_ID, "zone":drop_zone, "status":"flying", "offset":current_angle})


def set_homebase():
    # current_zone = positions_table.find_by_id(DRONE_ID)["zone"]
    positions_table.insert_or_replace(doc={'_id': DRONE_ID, "zone":"home_base", "status":"landed"})



#######################    FLIGHT DATA  PROCESSING    ##################

def handler(event, sender, data, **args):
    drone = sender
    # if event is drone.EVENT_LOG_DATA:
    #     log_data_doc = {"mvo":{"vel_x":data.mvo.vel_x,
    #                            "vel_y":data.mvo.vel_y,
    #                            "vel_z":data.mvo.vel_z,
    #                            "pos_x":data.mvo.pos_x,
    #                            "pos_y":data.mvo.pos_y,
    #                            "pos_z":data.mvo.pos_z},
    #                     "imu":{"acc_x":data.imu.acc_x,
    #                            "acc_y":data.imu.acc_y,
    #                            "acc_z":data.imu.acc_z,
    #                            "gyro_x":data.imu.gyro_x,
    #                            "gyro_y":data.imu.gyro_y,
    #                            "gyro_z":data.imu.gyro_z}}
    #     mutation = {'$put': {'log_data': log_data_doc}}
    #     dronedata_table.update(_id=DRONE_ID,mutation=mutation)
    #     # print(dronedata_table.find_by_id(DRONE_ID)["log_data"]);


    if event is drone.EVENT_FLIGHT_DATA:
        fly_speed = sqrt(data.north_speed*data.north_speed + data.east_speed*data.east_speed);
        flight_data_doc = {"battery":str(data.battery_percentage),
                           "fly_speed":str(data.fly_speed),
                           "wifi_strength":str(data.wifi_strength)}
        mutation = {'$put': {'flight_data': flight_data_doc}}
        dronedata_table.update(_id=DRONE_ID,mutation=mutation)



#######################       MAIN FUNCTION       ##################

def main():

    drone = tellopy.Tello()
    set_homebase() # reset drone position in the positions table

    # subscribe to flight data
    drone.subscribe(drone.EVENT_FLIGHT_DATA, handler)
    # drone.subscribe(drone.EVENT_LOG_DATA, handler)

    drone.connect()
    drone.wait_for_connection(60)
    # drone.set_loglevel("LOG_DEBUG")


    # create video thread
    videoThread = threading.Thread(target=get_drone_video,args=[drone])
    videoThread.start()


    start_time = time.time()
    consumer_group = randint(1000, 100000)
    positions_consumer = Consumer({'group.id': consumer_group,'default.topic.config': {'auto.offset.reset': 'latest'}})
    positions_consumer.subscribe([POSITIONS_STREAM + ":" + DRONE_ID])

    while True:
        try:
            print("waiting for instructions")
            msg = positions_consumer.poll()
            if msg is None:
                print("none")
                continue
            if not msg.error():
                json_msg = json.loads(msg.value().decode('utf-8'))
                print(json_msg)
                from_zone = positions_table.find_by_id(DRONE_ID)["zone"]
                drop_zone = json_msg["drop_zone"]
                
                if json_msg["action"] == "takeoff":
                    print("###############      Takeoff")
                    drone.takeoff()
                    time.sleep(5)
                    positions_table.insert_or_replace(doc={'_id': DRONE_ID, "zone":from_zone, "status":"flying"})

                if drop_zone != from_zone:
                    move_to_zone(drone,from_zone,drop_zone)
                    print("###############      Moved")
                    
                if json_msg["action"] == "land":
                    print("###############      Land")
                    drone.land()
                    positions_table.insert_or_replace(doc={'_id': DRONE_ID, "zone":from_zone, "status":"landed"})
                    time.sleep(5)

            elif msg.error().code() != KafkaError._PARTITION_EOF:
                print(msg.error())

            if time.time() > start_time + MAX_FLIGHT_TIME:
                print("Time expired - Landing")
                drone.land()
                time.sleep(5)
                break
        except Exception as ex:
            print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
            print(ex)
            traceback.print_exc()


    drone.quit()


    sys.exit()


if __name__ == '__main__':
    main()
