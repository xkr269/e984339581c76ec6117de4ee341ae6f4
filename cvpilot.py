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
import cv2
# try:
#     import av
# except:
#     pass
import tellopy
import json
import threading
from random import randint
from confluent_kafka import Producer, Consumer, KafkaError
from mapr.ojai.storage.ConnectionFactory import ConnectionFactory
from math import atan2, sqrt, pi, floor
from shutil import copyfile
import base64
from io import BytesIO
import logging
import base64
import numpy as np

import settings

DRONE_ID = sys.argv[1]

logging.basicConfig(filename=settings.LOG_FOLDER + "pilot_{}.log".format(DRONE_ID),
                    level=logging.INFO,
                    format='%(asctime)s :: %(levelname)s :: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


KILL_ALL = False

# Remote mode sends data through a remote MaprDB buffer instead of writing directly to the FS
REMOTE_MODE = settings.REMOTE_MODE


logging.info("Remote mode : {}".format(REMOTE_MODE))


def get_cluster_name():
  with open('/opt/mapr/conf/mapr-clusters.conf', 'r') as f:
    first_line = f.readline()
    return first_line.split(' ')[0]

def get_cluster_ip():
  with open('/opt/mapr/conf/mapr-clusters.conf', 'r') as f:
    first_line = f.readline()
    return first_line.split(' ')[2].split(':')[0]

def check_stream(stream_path):
  if not os.path.islink(stream_path):
    logging.info("stream {} is missing. Exiting.".format(stream_path))
    sys.exit()


STREAM_FPS = settings.STREAM_FPS
REPLAYER_FPS = settings.REPLAYER_FPS
PROJECT_FOLDER = settings.PROJECT_FOLDER




# Wait ratios
FORWARD_COEF = settings.FORWARD_COEF # Time taken to move 1m
ANGULAR_COEF = settings.ANGULAR_COEF # Time taken to rotate 360 deg

DRONE_MODE = settings.DRONE_MODE
NO_FLIGHT = settings.NO_FLIGHT 
DIRECTIONAL_MODE = settings.DIRECTIONAL_MODE

 
CLUSTER_NAME = get_cluster_name()
CLUSTER_IP = get_cluster_ip()

ROOT_PATH = settings.ROOT_PATH
DATA_FOLDER = settings.DATA_FOLDER
IMAGE_FOLDER = DATA_FOLDER + "images/" + DRONE_ID + "/source/"
VIDEO_STREAM = settings.VIDEO_STREAM
POSITIONS_STREAM = settings.POSITIONS_STREAM
DRONEDATA_TABLE = settings.DRONEDATA_TABLE
ZONES_TABLE = settings.ZONES_TABLE
CONTROLS_TABLE = settings.CONTROLS_TABLE
RECORDING_FOLDER = settings.RECORDING_FOLDER

BUFFER_TABLE = DATA_FOLDER + "{}_buffer".format(DRONE_ID)

current_angle = 0.0


time_tracker = {"min":1000,"max":0,"count":0,"avg":0}


SECURE_MODE = settings.SECURE_MODE
username = settings.USERNAME
password = settings.PASSWORD
PEM_FILE = settings.PEM_FILE


# Initialize databases
if SECURE_MODE:
  connection_str = "{}:5678?auth=basic;" \
                           "user={};" \
                           "password={};" \
                           "ssl=true;" \
                           "sslCA={};" \
                           "sslTargetNameOverride={}".format(CLUSTER_IP,username,password,PEM_FILE,CLUSTER_IP)
else:
  connection_str = "{}:5678?auth=basic;user={};password={};ssl=false".format(CLUSTER_IP,username,password)# Create database connection

connection = ConnectionFactory().get_connection(connection_str=connection_str)
zones_table = connection.get_or_create_store(ZONES_TABLE)

# initialize drone data
dronedata_table = connection.get_or_create_store(DRONEDATA_TABLE)
dronedata_table.insert_or_replace({"_id":DRONE_ID,
                                   "status":"ready",
                                   "last_command":"land",
                                   "flight_data":{"battery":50,"fly_speed":5.0},
                                   "log_data":"unset",
                                   "count":0,
                                   "connection_status":"disconnected",
                                   "position": {"zone":"home_base", "status":"landed","offset":0.0}})

# initialize drone controls
controls_table = connection.get_or_create_store(CONTROLS_TABLE)
controls_table.insert_or_replace({"_id":DRONE_ID,
                                   "pressed_keys":[]})


buffer_table = connection.get_or_create_store(BUFFER_TABLE)

# test if folders exist and create them if needed
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

# create sreams if needed
check_stream(VIDEO_STREAM)
check_stream(POSITIONS_STREAM)





#######################    INTERACTIVE DRONE CONTROL    ##################
# Function polls an instruction DB to get the current control keys and send the commands to the drone

controls = {
    'left': lambda drone, speed: drone.left(speed),
    'right': lambda drone, speed: drone.right(speed),
    'forward': lambda drone, speed: drone.forward(speed),
    'backward': lambda drone, speed: drone.backward(speed),
    'flip': lambda drone, speed: drone.flip_back(),
    'clockwise': lambda drone, speed: drone.clockwise(speed),
    'counter_clockwise': lambda drone, speed: drone.counter_clockwise(speed),
    'up': lambda drone, speed: drone.up(speed),
    'down': lambda drone, speed: drone.down(speed),
    'takeoff': lambda drone, speed: drone.takeoff(),
    'land': lambda drone, speed: drone.land(),
}


#######################    VIDEO PROCESSING    ##################


def get_drone_video2(drone):

    print("get video 2")

    global IMAGE_FOLDER
    global DRONE_ID
    global VIDEO_STREAM

    UDP_IP = "0.0.0.0"
    UDP_PORT = 11111
    cap = cv2.VideoCapture("udp://{}:{}".format(UDP_IP,UDP_PORT))
    index = 0

    video_producer = Producer({'streams.producer.default.stream': VIDEO_STREAM})
    
    while True:
        # Capture frame-by-frame
        ret, frame = cap.read()
        index += 1
        if ret:
            logging.info("saving {}".format(index))
            new_image = IMAGE_FOLDER + "frame-{}.jpg".format(index)
            cv2.imwrite(new_image, frame)
            video_producer.produce(DRONE_ID + "_source", json.dumps({"drone_id":DRONE_ID,
                                                                     "index":index,
                                                                     "image":new_image}))




            

#######################       MAIN FUNCTION       ##################

def main():

    logging.info("Pilot started for {}".format(DRONE_ID))

    drone_number = int(DRONE_ID.split('_')[1])
    
    drone = tellopy.Tello()
    
    drone.connect()
    drone.wait_for_connection(600)

    dronedata_table.update(_id=DRONE_ID,mutation={"$put":{'connection_status':"connected"}})


    drone.custom_command("command")
    time.sleep(2)
    drone.custom_command("streamon")

    # create video thread
    videoThread = threading.Thread(target=get_drone_video2,args=[drone])
    videoThread.start()

    start_time = time.time()
    consumer_group = DRONE_ID + str(time.time())
    positions_consumer = Consumer({'group.id': consumer_group,'default.topic.config': {'auto.offset.reset':'latest'}})
    positions_consumer.subscribe([POSITIONS_STREAM + ":" + DRONE_ID])

    while True:
        speed = 100
        try:
            prev_pk = []
            while True:
                time.sleep(0.05)
                
                if drone.state == drone.STATE_CONNECTED:
                    dronedata_table.update(_id=DRONE_ID,mutation={"$put":{'connection_status':"connected"}})
                else:
                    dronedata_table.update(_id=DRONE_ID,mutation={"$put":{'connection_status':"disconnected"}})

                pressed_keys = controls_table.find_by_id("drone_1")["pressed_keys"]
                if set(pressed_keys) != set(prev_pk):
                    keys_up = []
                    for key in prev_pk:
                        if not key in pressed_keys:
                            keys_up.append(key)
                    keys_down = []
                    for key in pressed_keys:
                        if not key in prev_pk:
                            keys_down.append(key)
                    prev_pk = pressed_keys
                    print("Pressed keys : {}".format(pressed_keys))
                    print("Down : {}".format(keys_down))
                    print("Up : {}".format(keys_up))

                    for key in keys_up:
                        controls[key](drone, 0)
                    for key in keys_down:
                        controls[key](drone,speed)

        except Exception as ex:
            logging.exception("interactive control failed")


    logging.info("QUITTING")


    KILL_ALL = True
    drone.killall = True
    logging.info("Exiting threads ... ")
    time.sleep(5)
    logging.info("threads killed.")

    sys.exit()


if __name__ == '__main__':
    main()
