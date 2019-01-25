#! /usr/bin/python

"""
Recorder application for TEITS demo

What it does :
- Connects to the drone
- Gets the video
- Stores each frame in a folder
- Stores frame indexes in a stream (recording_stream) in a topic named with the zone id entered in the UI

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
from flask import Flask, render_template, request, Response, flash, redirect, url_for


import settings

CLUSTER_IP = settings.CLUSTER_IP

RECORDER_FPS = settings.RECORDER_FPS

RECORDING_STREAM = settings.RECORDING_STREAM
RECORDING_FOLDER = settings.RECORDING_FOLDER
RECORDING_TABLE = settings.RECORDING_TABLE

CURRENT_ZONE = "render_template"
RECORD_VIDEO = False

# Create and init database
connection_str = CLUSTER_IP + ":5678?auth=basic;user=mapr;password=mapr;ssl=false"
connection = ConnectionFactory().get_connection(connection_str=connection_str)
recording_table = connection.get_or_create_store(RECORDING_TABLE)
recording_table.insert_or_replace({"_id":"recording","status":False,"zone":"temp"})


#######################    VIDEO PROCESSING    ##################

# Function for transfering the video frames to FS and Stream
def get_drone_video(drone):
    video_producer = Producer({'streams.producer.default.stream': RECORDING_STREAM})
    current_sec = 0
    last_frame_time = 0
    container = av.open(drone.get_video_stream())
    try:
        start_time = time.time()
        total_frames = 0
        received_frames = 0
        sent_frames = 0
        frame_skip = 400

        while drone.state != drone.STATE_QUIT:
            print("Drone is connected - decoding container")
            for frame in container.decode(video=0):
                received_frames += 1
                total_frames += 1
                if total_frames < frame_skip:
                    continue

                recording_info = recording_table.find_by_id("recording")
                RECORD_VIDEO = recording_info["status"]
                CURRENT_ZONE = recording_info["zone"]

                if drone.state != drone.STATE_CONNECTED:
                    print("Drone disconnected - QUITTING VIDEO THREAD ")
                    break
                current_time = time.time()
                if current_time > (last_frame_time + float(1/RECORDER_FPS)):
                    image = RECORDING_FOLDER + CURRENT_ZONE + "/frame-{}.jpg".format(frame.index) 
                    frame.to_image().save(image)
                    print(RECORD_VIDEO)
                    if RECORD_VIDEO :
                        topic = CURRENT_ZONE
                    else:
                        topic = "temp"
                    print(topic)
                    video_producer.produce(topic, json.dumps({"index":frame.index,
                                                              "image":image}))

                    print("saved {} to {}".format(image,topic))
                    
                    sent_frames += 1
                    last_frame_time = time.time()


                # Print stats every second
                elapsed_time = time.time() - start_time
                if int(elapsed_time) != current_sec:
                    print("Elapsed : {} s, received {} fps , sent {} fps".format(int(elapsed_time),received_frames,sent_frames))
                    received_frames = 0
                    sent_frames = 0
                    current_sec = int(elapsed_time)

    # Catch exceptions
    except Exception:
        traceback.print_exc()


#######################       MAIN FUNCTION       ##################


drone = tellopy.Tello() 
drone.connect()
drone.wait_for_connection(600)

videoThread = threading.Thread(target=get_drone_video,args=[drone])
videoThread.start()


while True:
    try:
        if drone.state == drone.STATE_QUIT:
            drone.sock.close()
            while videoThread.isAlive() or drone.video_thread_running:
                print("wait for threads to stop")
                time.sleep(1)
            print("reconnecting ...")
            drone = tellopy.Tello()
            drone.connect()
            drone.wait_for_connection(600)
            print("connected - starting video thread")
            # recreate video thread
            videoThread = threading.Thread(target=get_drone_video,args=[drone])
            videoThread.start()
        time.sleep(1)

    except KeyboardInterrupt:
        break   



drone.quit()
print("Disconnecting ...")
time.sleep(2)
print("Terminated.")