

import time
import traceback
import json
from random import randint
from mapr.ojai.storage.ConnectionFactory import ConnectionFactory
from confluent_kafka import Consumer, KafkaError, Producer


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

OFFSET_RESET_MODE = 'latest'
PROCESSOR_ID = "processor_" + str(int(time.time())) + str(randint(0,10000))

CLUSTER_NAME = get_cluster_name()
CLUSTER_IP = get_cluster_ip()
PROJECT_FOLDER = "/teits"
ROOT_PATH = '/mapr/' + CLUSTER_NAME + PROJECT_FOLDER
PROCESSORS_TABLE = ROOT_PATH + '/test_table'  # Path for the table that stores processor info
PROCESSORS_STREAM = ROOT_PATH + '/processors_stream'   # Output Stream path
OUTPUT_STREAM = ROOT_PATH + '/output_stream'   # Output Stream path
OUTPUT_TOPIC = "default"
ALLOWED_LAG = 1 # second


# Build Ojai MapRDB access
connection_str = CLUSTER_IP + ":5678?auth=basic;user=mapr;password=mapr;ssl=false"
connection = ConnectionFactory().get_connection(connection_str=connection_str)
processors_table = connection.get_or_create_store(PROCESSORS_TABLE)


# Configure consumer
consumer_group = str(time.time())
consumer = Consumer({'group.id': consumer_group, 'default.topic.config': {'auto.offset.reset': OFFSET_RESET_MODE}})
consumer.subscribe([PROCESSORS_STREAM + ":" + PROCESSOR_ID])

# Configure producer
producer = Producer({'streams.producer.default.stream': OUTPUT_STREAM})


def processing_function(message):
    print("Processing")
    time.sleep(0.1)
    message["processed"]=True
    return message


# Sets processor as available
print("Set {} as available".format(PROCESSOR_ID))
processors_table.insert_or_replace({"_id":PROCESSOR_ID,"status":"available"})


while True:
    msg = consumer.poll()
    if msg is None:
        continue
    if not msg.error():
        try:
            received_msg = json.loads(msg.value().decode("utf-8"))
            offset = received_msg["offset"]
            
            if offset < processors_table.find_by_id("offset")["offset"]:
                # If the message offset is lower than the latest committed offset
                # message is discarded
                continue

            # Processing the message
            processed_message = processing_function(received_msg)

            # Write processed message to the output stream
            check_time = time.time()
            display_wait = True
            last_committed_offset = processors_table.find_by_id("offset")["offset"]
            while last_committed_offset != (offset - 1) and time.time() < (check_time + ALLOWED_LAG):
                if display_wait:
                    print('Waiting for previous frame to complete - Current offest : {}, Last committed offset : {}'.format(offset,last_committed_offset))
                    display_wait = False
                last_committed_offset = processors_table.find_by_id("offset")["offset"]

            print("Message {} - offset {} processed".format(received_msg["_id"],offset))
            if not display_wait:
                print("Wait time : {}".format(time.time() - check_time))
            producer.produce(OUTPUT_TOPIC,json.dumps(processed_message))

            # Commit offset
            processors_table.insert_or_replace({"_id":"offset","offset":offset})
            
            # Set processor as available
            print("Set {} as available".format(PROCESSOR_ID))
            processors_table.insert_or_replace({"_id":PROCESSOR_ID,"status":"available"})

        except KeyboardInterrupt:
            break   

        except Exception as ex:
            print(ex)
            traceback.print_exc()
            break

    elif msg.error().code() != KafkaError._PARTITION_EOF:
        print(msg.error())
        break

# Unregisters the processor from the processors table 
processors_table.delete({"_id":PROCESSOR_ID})
