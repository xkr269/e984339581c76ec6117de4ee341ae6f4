import time
import traceback
import json
from random import randint
from confluent_kafka import Consumer, KafkaError


############################       Utilities        #########################

def get_cluster_name():
  with open('/opt/mapr/conf/mapr-clusters.conf', 'r') as f:
    first_line = f.readline()
    return first_line.split(' ')[0]

def check_stream(stream_path):
  if not os.path.islink(stream_path):
    print("stream {} is missing. Exiting.".format(stream_path))
    sys.exit()
    

############################       Settings        #########################

OFFSET_RESET_MODE = 'latest'
CLUSTER_NAME = get_cluster_name()
PROJECT_FOLDER = "/teits"
ROOT_PATH = '/mapr/' + CLUSTER_NAME + PROJECT_FOLDER
DISPLAY_STREAM = ROOT_PATH + '/output_stream'   # Output Stream path
TOPIC_NAME = "default"

# Configure consumer
consumer_group = str(time.time())
consumer = Consumer({'group.id': consumer_group, 'default.topic.config': {'auto.offset.reset': OFFSET_RESET_MODE}})
consumer.subscribe([DISPLAY_STREAM + ":" + TOPIC_NAME])

while True:
    msg = consumer.poll()
    if msg is None:
        continue
    if not msg.error():
        try:
            received_msg = json.loads(msg.value().decode("utf-8"))
            print(received_msg)

        except KeyboardInterrupt:
            break   

        except Exception as ex:
            print(ex)
            traceback.print_exc()

    elif msg.error().code() != KafkaError._PARTITION_EOF:
        print(msg.error())
        break
