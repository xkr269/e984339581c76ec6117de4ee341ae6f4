# generateur

import json
import time
from random import randint
from confluent_kafka import Producer, Consumer, KafkaError


def get_cluster_name():
  with open('/opt/mapr/conf/mapr-clusters.conf', 'r') as f:
    first_line = f.readline()
    return first_line.split(' ')[0]

    
CLUSTER_NAME = get_cluster_name()
PROJECT_FOLDER = "/teits"
ROOT_PATH = '/mapr/' + CLUSTER_NAME + PROJECT_FOLDER
SOURCE_STREAM = ROOT_PATH + "/source_stream"

MESSAGES_RATE = 30.0 # per second

producer = Producer({'streams.producer.default.stream': SOURCE_STREAM})

produced_messages = 0
current_sec = 0
start_time = 0
message_id = 0


while True:
    message_id += 1 
    doc = {"_id":message_id,"drone_id":"drone_1","value":randint(0,10000)}
    producer.produce("drone_1",json.dumps(doc))
    time.sleep(1/MESSAGES_RATE)
    produced_messages += 1

    # Print stats every second
    elapsed_time = time.time() - start_time
    if int(elapsed_time) != current_sec:
        print("Produced {} messages. Rate : {} msg/s".format(message_id,produced_messages))
        produced_messages = 0
        current_sec = int(elapsed_time)

