#! /usr/bin/python

"""
Dispatcher

Reads messages from a defined stream
Sends messages to processor streams adding an offset field used 
by processors to release processed messages in the right order 


"""

import time
import json
import traceback
from random import randint
from confluent_kafka import Producer, Consumer, KafkaError
from mapr.ojai.storage.ConnectionFactory import ConnectionFactory


############################       Utilities        #########################

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
    

############################       Settings        #########################

PROJECT_FOLDER = "/teits"
CLUSTER_NAME = get_cluster_name()
CLUSTER_IP = get_cluster_ip()
ROOT_PATH = '/mapr/' + CLUSTER_NAME + PROJECT_FOLDER
SOURCE_STREAM = ROOT_PATH + "/video_stream"
SOURCE_TOPIC = "raw_*"
PROCESSORS_STREAM = ROOT_PATH + "/processors_stream"
PROCESSORS_TABLE = ROOT_PATH + "/processors_table"


# Create database connection
connection_str = CLUSTER_IP + ":5678?auth=basic;user=mapr;password=mapr;ssl=false"
connection = ConnectionFactory().get_connection(connection_str=connection_str)
processors_table = connection.get_or_create_store(PROCESSORS_TABLE)



#######################       MAIN FUNCTION       ##################

def main():

    # Reset processors table
    for proc in processors_table.find():
        print(proc)
        processors_table.delete(_id=proc["_id"])
        print("deleted")

    # Subscribe to source stream on given topics
    consumer_group = str(time.time())
    main_consumer = Consumer({'group.id': consumer_group,'default.topic.config': {'auto.offset.reset': 'latest'}})
    main_consumer.subscribe([SOURCE_STREAM + ":drone_1_raw",SOURCE_STREAM + ":drone_2_raw",SOURCE_STREAM + ":drone_3_raw",]) 
    producer = Producer({'streams.producer.default.stream': PROCESSORS_STREAM})

    # Initialize offset
    try:
        offset = processors_table.find_by_id("offset")["offset"]
    except:
        offset = 0
        processors_table.insert_or_replace({"_id":"offset","offset":offset}) 
    
    start_time = time.time()
    current_sec = 0
    received_messages = 0
    sent_messages = 0
    print("waiting for new data ... ")
    while True:
        try:
            msg = main_consumer.poll()
            if msg is None:
                continue
            if not msg.error():
                json_msg = json.loads(msg.value().decode('utf-8'))
                received_messages += 1
                # get the first available processor
                processed = False
                result = processors_table.find({"$where": {"$eq": {"status": "available"}},"$limit": 1})
                for doc in result:
                    # set the processor as "busy"
                    # the processor state will be reset as "available" by the processor itself 
                    # once the message has been processed 
                    doc["status"] = "busy"
                    processors_table.insert_or_replace(doc)

                    offset += 1
                    json_msg["offset"] = offset # Insert offset in the message. Used to release frames in order

                    # Push the frame to be processed in the processor topic
                    producer.produce(doc["_id"],json.dumps(json_msg))
                    sent_messages += 1

                # Print stats every second
                elapsed_time = time.time() - start_time
                if int(elapsed_time) != current_sec:
                    print("Dispatching - Received {} msg/s , sent {} msg/s".format(received_messages,sent_messages))
                    received_messages = 0
                    sent_messages = 0
                    current_sec = int(elapsed_time)



        except Exception as ex:
            print(ex)
            traceback.print_exc()


if __name__ == '__main__':
    main()
