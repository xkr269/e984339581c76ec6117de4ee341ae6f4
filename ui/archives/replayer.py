# Replayer

import sys
import os
import json
import time
import glob
import threading

from random import randint
from confluent_kafka import Producer, Consumer, KafkaError
from mapr.ojai.storage.ConnectionFactory import ConnectionFactory


def get_cluster_name():
  with open('/opt/mapr/conf/mapr-clusters.conf', 'r') as f:
    first_line = f.readline()
    return first_line.split(' ')[0]

def get_cluster_ip():
  with open('/opt/mapr/conf/mapr-clusters.conf', 'r') as f:
    first_line = f.readline()
    return first_line.split(' ')[2].split(':')[0]


DRONE_ID = sys.argv[1]

CLUSTER_NAME = get_cluster_name()
CLUSTER_IP = get_cluster_ip()
PROJECT_FOLDER = "/teits"
ROOT_PATH = '/mapr/' + CLUSTER_NAME + PROJECT_FOLDER
SOURCE_STREAM = ROOT_PATH + "/video_stream"
IMAGE_FOLDER = ROOT_PATH + "/" + DRONE_ID + "/images/source/"
DRONEDATA_TABLE = ROOT_PATH + "/dronedata_table"
POSITIONS_TABLE = ROOT_PATH + "/positions_table"
POSITIONS_STREAM = ROOT_PATH + "/positions_stream"


# Create database connection
connection_str = CLUSTER_IP + ":5678?auth=basic;user=mapr;password=mapr;ssl=false"
connection = ConnectionFactory().get_connection(connection_str=connection_str)
dronedata_table = connection.get_or_create_store(DRONEDATA_TABLE)
positions_table = connection.get_or_create_store(POSITIONS_TABLE)

dronedata_table.insert_or_replace({"_id":DRONE_ID,"flight_data":{"battery":"75","fly_speed":"5"},"log_data":"unset","count":"0","connection_status":"connected"})


MESSAGES_RATE = 3.0 # per second

producer = Producer({'streams.producer.default.stream': SOURCE_STREAM})

produced_messages = 0
current_sec = 0
start_time = 0
message_id = 0



def drone_emulator(drone_id):
    consumer_group = drone_id + str(time.time())
    positions_consumer = Consumer({'group.id': consumer_group,'default.topic.config': {'auto.offset.reset': 'latest'}})
    positions_consumer.subscribe([POSITIONS_STREAM + ":" + drone_id])

    positions_table.insert_or_replace(doc={'_id': drone_id, "zone":"home_base", "status":"landed","offset":current_angle})

    while True:
        print("waiting for instructions")

        msg = positions_consumer.poll()

        if msg is None:
            continue

        if not msg.error():
            json_msg = json.loads(msg.value().decode('utf-8'))
            from_zone = positions_table.find_by_id(drone_id)["zone"]
            drop_zone = json_msg["drop_zone"]
            
            if json_msg["action"] == "takeoff":
                print("###############      Takeoff")
                positions_table.insert_or_replace(doc={'_id': drone_id, "zone":from_zone, "status":"flying"})

            if drop_zone != from_zone:
                print("###############      Moved")
                positions_table.insert_or_replace(doc={'_id': drone_id, "zone":drop_zone, "status":"flying"})
                
            if json_msg["action"] == "land":
                print("###############      Land")
                positions_table.insert_or_replace(doc={'_id': drone_id, "zone":from_zone, "status":"landed"})

        elif msg.error().code() != KafkaError._PARTITION_EOF:
            print(msg.error())


# create video thread
droneThread = threading.Thread(target=drone_emulator,args=[DRONE_ID])
droneThread.start()


# list and sort files in the directory

files = filter(os.path.isfile, glob.glob(IMAGE_FOLDER + "*"))
files.sort(key=lambda x: os.path.getmtime(x))
indexes = []

indexes.sort()

while True:
    try:
        for filename in files:
            index = int(filename.split('/')[-1].split('.')[0].split('-')[1])
            producer.produce(DRONE_ID+"_raw", json.dumps({"drone_id":DRONE_ID,
                                                          "index":index,
                                                          "image":IMAGE_FOLDER + "frame-{}.jpg".format(index)}))

            time.sleep(1/MESSAGES_RATE)
            produced_messages += 1
            message_id += 1

            # Print stats every second
            elapsed_time = time.time() - start_time
            if int(elapsed_time) != current_sec:
                print("Produced {} messages. Rate : {} msg/s".format(message_id,produced_messages))
                produced_messages = 0
                current_sec = int(elapsed_time)

    except KeyboardInterrupt:
        break   

dronedata_table.insert_or_replace({"_id":DRONE_ID,"flight_data":{"battery":"75","fly_speed":"0"},"log_data":"unset","count":"0","connection_status":"disconnected"})
