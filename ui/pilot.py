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


import time
from time import sleep
import os
import sys
import av
import tellopy
import json
import threading
from confluent_kafka import Producer, Consumer, KafkaError


DRONE_ID = "drone_1"
FPS = 20.0
PROJECT_FOLDER = "/teits"


def get_cluster_name():
  with open('/opt/mapr/conf/mapr-clusters.conf', 'r') as f:
    first_line = f.readline()
    return first_line.split(' ')[0]

def test_stream(stream_path):
  if not os.path.islink(stream_path):
    print("stream {} is missing. Exiting.".format(stream_path))
    sys.exit()
    
cluster_name = get_cluster_name()

ROOT_PATH = '/mapr/' + cluster_name + PROJECT_FOLDER

IMAGE_FOLDER = ROOT_PATH + "/" + DRONE_ID + "/images/source/"
VIDEO_STREAM = ROOT_PATH + "/video_stream"
POSITIONS_STREAM = ROOT_PATH + "/positions_stream"


# test if folders exist and create them if needed
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

# test if streams exist and create them if needed
test_stream(VIDEO_STREAM)
test_stream(POSITIONS_STREAM)


file = None
write_header = True
tello_address = ('192.168.10.1', 8889)

def handler(event, sender, data, **args):
    drone = sender
    if event is drone.EVENT_LOG_DATA:
        print(data)


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
            for frame in container.decode(video=0):
                received_frames += 1
                current_time = time.time()
                if current_time > (last_frame_time + float(1/FPS)):
                    frame.to_image().save(IMAGE_FOLDER + "frame-{}.jpg".format(frame.index))
                    video_producer.produce(DRONE_ID, json.dumps({"index":frame.index}))
                    sent_frames += 1
                    last_frame_time = time.time()

                # Print stats every second
                elapsed_time = time.time() - start_time
                if int(elapsed_time) != current_sec:
                    # print("Elapsed : {} s, received {} fps , sent {} fps".format(elapsed_time,received_frames,sent_frames))
                    # sys.stdout.write("Elapsed : {} s, received {} fps , sent {} fps                 \r".format(elapsed_time,received_frames,sent_frames))
                    # sys.stdout.flush()
                    received_frames = 0
                    sent_frames = 0
                    current_sec = int(elapsed_time)

    # Catch exceptions
    except Exception as ex:
        print(ex)


def move_to(drone,position):
    global current_position
    global current_angle
    # calcul du deplacement
    x = position[0] - current_position[0]
    y = position[1] - current_position[1]
    # calcul angle de rotation vs axe x
    a = atan2(y,x)*180/pi
    # angle de rotation corrige
    b = a - current_angle
    # rotation
    turn(drone,b)
    # update angle
    current_angle = a
    # distance a parcourir
    d = sqrt(x*x + y*y)
    # deplacement
    forward(drone,d)
    # update position
    current_position = position



def main():

    drone = tellopy.Tello()
    
    drone.connect()
    drone.wait_for_connection(60)

    # create video thread
    videoThread = threading.Thread(target=get_drone_video,args=[drone])
    videoThread.start()


    start_time = time.time()
    flight_time = 180 # seconds

    positions_consumer = Consumer({'group.id': "default",'default.topic.config': {'auto.offset.reset': 'latest'}})
    positions_consumer.subscribe([POSITIONS_STREAM + ":" + DRONE_ID])

    while True:
        print("polling")
        msg = positions_consumer.poll()
        if msg is None:
            print("none")
            continue
        if not msg.error():
            json_msg = json.loads(msg.value().decode('utf-8'))
            print(json_msg)
            if json_msg["action"] == "takeoff":
                drone.takeoff()
            if json_msg["action"] == "land":
                drone.land()
        elif msg.error().code() != KafkaError._PARTITION_EOF:
            print(msg.error())

        if time.time() > start_time + flight_time:
            print("Time expired")
            break


    drone.quit()


    sys.exit()


if __name__ == '__main__':
    main()
