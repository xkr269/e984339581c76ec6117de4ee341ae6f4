#! /usr/bin/python

"""
Dispatcher application for TEITS demo

What it does :
- Connects to the source video stream
- dispatches incoming images to the processing streams

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

PROJECT_FOLDER = "/teits"

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
    print("stream {} is missing. Exiting.".format(stream_path))
    sys.exit()
    
cluster_name = get_cluster_name()
cluster_ip = get_cluster_ip()
ROOT_PATH = '/mapr/' + cluster_name + PROJECT_FOLDER
VIDEO_STREAM = ROOT_PATH + "/video_stream"
PROCESSORS_TABLE = ROOT_PATH + "/processors_table"

# Create database connection
connection_str = cluster_ip + ":5678?auth=basic;user=mapr;password=mapr;ssl=false"
connection = ConnectionFactory().get_connection(connection_str=connection_str)
processors_table = connection.get_or_create_store(PROCESSORS_TABLE)




#######################       MAIN FUNCTION       ##################

def main():

    # Subscribe to source video stream on given topics

    consumer_group = str(time.time())
    main_consumer = Consumer({'group.id': consumer_group,'default.topic.config': {'auto.offset.reset': 'latest'}})
    main_consumer.subscribe([VIDEO_STREAM + ":drone_1_raw"]) # gets data for all drones
    producer = Producer({'streams.producer.default.stream': VIDEO_STREAM})

    # reset processors table
    for proc in processors_table.find():
        print(proc)
        processors_table.delete(_id=proc["_id"])
        print("deleted")


    while True:
        try:

            msg = main_consumer.poll()
            if msg is None:
                print("No new message in the stream")
                continue


            if not msg.error():

                json_msg = json.loads(msg.value().decode('utf-8'))
                # get the first available processor
                query = {"$where": {"$eq": {"status": "available"}},"$limit": 1}
                result = processors_table.find(query)
                processed = False
                for doc in result:
                    print(doc)
                    # set the processor as "busy"
                    # the processor state will be reset as "available" by the processor itself 
                    # once the message has been processed 
                    print("Using {} to process frame {} for {}".format(doc["_id"],json_msg["index"],json_msg["drone_id"]))
                    doc["status"] = "busy"
                    processors_table.insert_or_replace(doc)

                    # push the frame to be processed in the processor topic
                    producer.produce(doc["_id"],msg.value())
                    processed = True
                if not processed:
                    print("No processor available @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")




        except Exception as ex:
            print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
            print(ex)
            traceback.print_exc()


    drone.quit()


    sys.exit()


if __name__ == '__main__':
    main()
