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
import os
import json
from confluent_kafka import Producer, Consumer, KafkaError
from mapr.ojai.storage.ConnectionFactory import ConnectionFactory
from flask import Flask, render_template, request, Response, flash, redirect, url_for

import settings

CLUSTER_IP = settings.CLUSTER_IP

ZONES_TABLE = settings.ZONES_TABLE
RECORDING_STREAM = settings.RECORDING_STREAM
RECORDING_FOLDER = settings.RECORDING_FOLDER
RECORDING_TABLE = settings.RECORDING_TABLE


# Create database connection
connection_str = CLUSTER_IP + ":5678?auth=basic;user=mapr;password=mapr;ssl=false"
connection = ConnectionFactory().get_connection(connection_str=connection_str)
zones_table = connection.get_or_create_store(ZONES_TABLE)
recording_table = connection.get_or_create_store(RECORDING_TABLE)


os.system("mkdir -p {}".format(RECORDING_FOLDER + "temp"))

def stream_video():
    consumer_group = str(time.time())
    consumer = Consumer({'group.id': consumer_group, 'default.topic.config': {'auto.offset.reset': "latest"}})
    subscriptions = [RECORDING_STREAM + ":temp"]
    for zone in zones_table.find():
        subscriptions.append(RECORDING_STREAM + ":" + zone["_id"])
    consumer.subscribe(subscriptions)
    while True:
        msg = consumer.poll()
        if msg is None:
            continue
        if not msg.error():
            json_msg = json.loads(msg.value().decode('utf-8'))
            image = json_msg['image']
            print(image)
            try:
              with open(image, "rb") as imageFile:
                f = imageFile.read()
                b = bytearray(f)
              yield (b'--frame\r\n' + b'Content-Type: image/jpg\r\n\r\n' + b + b'\r\n\r\n')
            except Exception as ex:
              print("can't open file {}".format(image))
              print(ex)

        elif msg.error().code() != KafkaError._PARTITION_EOF:
            print('  Bad message')
            print(msg.error())
            break
    print("Stopping video loop for {}".format(drone_id))


app = Flask(__name__)


@app.route('/')
def recorder():
    for zone in zones_table.find():
        print(zone)
    return render_template("recorder.html",zones=zones_table.find())

@app.route('/video_stream/')
def video_stream():
  return Response(stream_video(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/delete_recording',methods=["POST"])
def delete_recording():
    RECORD_NAME = request.form["zone_name"]
    recording_table.insert_or_replace({"_id":"recording","status":False,"zone":"temp"})
    print("Deleting {} recordings")
    try:
        os.system("rm -rf {}".format(RECORDING_FOLDER + RECORD_NAME))
        os.system("maprcli stream delete topic -path " + RECORDING_STREAM + " -topic " + RECORD_NAME)
    except: 
        traceback.print_exc()
    return "ok"

@app.route('/start_recording',methods=["POST"])
def start_recording():
    RECORD_NAME = request.form["zone_name"]
    os.system("mkdir -p {}".format(RECORDING_FOLDER + RECORD_NAME))
    recording_table.insert_or_replace({"_id":"recording","status":True,"zone":RECORD_NAME})
    return "ok"

@app.route('/stop_recording',methods=["POST"])
def stop_recording():
    recording_table.insert_or_replace({"_id":"recording","status":False,"zone":"temp"})
    return "ok"



app.run(debug=True,host='0.0.0.0',port=80)
