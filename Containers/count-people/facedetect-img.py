import cv2,sys,io,time
from io import StringIO
import numpy
from random import randint
from PIL import Image
from mapr.ojai.storage.ConnectionFactory import ConnectionFactory
from confluent_kafka import Consumer, KafkaError, Producer
import traceback
import json
import os

print(1)
def get_cluster_name():
  with open('/opt/mapr/conf/mapr-clusters.conf', 'r') as f:
    first_line = f.readline()
    return first_line.split(' ')[0]

def get_cluster_ip():
  with open('/opt/mapr/conf/mapr-clusters.conf', 'r') as f:
    first_line = f.readline()
    return first_line.split(' ')[2].split(':')[0]


print(2)

############################       Settings        #########################

OFFSET_RESET_MODE = 'latest'
PROCESSOR_ID = "processor_" + str(int(time.time())) + str(randint(0,10000))

cluster_name = get_cluster_name()
cluster_ip = get_cluster_ip()
PROJECT_FOLDER = "/teits"
ROOT_PATH = '/mapr/' + cluster_name + PROJECT_FOLDER
DRONEDATA_TABLE = ROOT_PATH + '/dronedata_table'  # Path for the table that stores drone data
PROCESSORS_TABLE = ROOT_PATH + '/processors_table'  # Path for the table that stores processor info
VIDEO_STREAM = ROOT_PATH + '/video_stream'   # Video stream path

print(3)
# Face detection params
cascPath = "haarcascade_frontalface_default.xml"
faceCascade = cv2.CascadeClassifier(cascPath)

# Build Ojai MapRDB access
connection_str = cluster_ip + ":5678?auth=basic;user=mapr;password=mapr;ssl=false"
connection = ConnectionFactory().get_connection(connection_str=connection_str)
dronedata_table = connection.get_or_create_store(DRONEDATA_TABLE)
processors_table = connection.get_or_create_store(PROCESSORS_TABLE)
print(4)

# Configure consumer
consumer_group = str(time.time())
consumer = Consumer({'group.id': consumer_group, 'default.topic.config': {'auto.offset.reset': OFFSET_RESET_MODE}})
consumer.subscribe([VIDEO_STREAM + ":" + PROCESSOR_ID])

print(5)
# Configure producer
producer = Producer({'streams.producer.default.stream': VIDEO_STREAM})

print(6)

current_offset = processors_table.find_by_id("offset")["offset"]

print("Set {} as available".format(PROCESSOR_ID))
processors_table.insert_or_replace({"_id":PROCESSOR_ID,"status":"available"})


while True:
    # Set processor as "available"
    msg = consumer.poll()
    if msg is None:
        print("polled at {}".format(time.time()))
        continue
    if not msg.error():
        try:
            print("detecting")
            json_msg = json.loads(msg.value().decode("utf-8"))
            image_path = json_msg["image"]
            frame_index = json_msg["index"]
            drone_id = json_msg["drone_id"]
            frame_offset = json_msg["offset"]
            if frame_offset < current_offset:
                continue
            image_array = numpy.array(Image.open(image_path))
            image = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = faceCascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )

            # Update drone document with faces count 
            dronedata_table.update(_id=json_msg["drone_id"],mutation={'$put': {'count': len(faces)}})

            # Draw faces on the image
            for (x, y, w, h) in faces:
                cv2.rectangle(image, (x, y), (x+w, y+h), (0, 255, 0), 2)

            # Write new image to file system
            image_folder = ROOT_PATH + "/" + drone_id + "/images/faces/"
            if not os.path.exists(image_folder):
                os.makedirs(image_folder)
            new_image_path = image_folder + "frame-{}.jpg".format(frame_index)
            cv2.imwrite(new_image_path, image)

            # Write image to video stream
            write_topic = drone_id + "_faces"

            check_time = time.time()
            display_wait_previous_frame = True
            current_offset = processors_table.find_by_id("offset")["offset"]
            while current_offset != (frame_offset - 1) and time.time() < (check_time+1): # allow 1 second of lag
                if display_wait_previous_frame :
                    print('Waiting for previous frame to complete - Current frame : {}, Last committed frame = {}'.format(frame_offset,current_offset))
                    display_wait_previous_frame = False
                current_offset = processors_table.find_by_id("offset")["offset"]

            print("frame {} for {} - offset {} processed".format(frame_index,drone_id,frame_offset))
            producer.produce(write_topic,json.dumps({"index":frame_index,"image":new_image_path}))
            processors_table.insert_or_replace({"_id":"offset","offset":frame_offset})
            print("Set {} as available".format(PROCESSOR_ID))
            processors_table.insert_or_replace({"_id":PROCESSOR_ID,"status":"available"})


        except Exception as ex:
            print(ex)
            traceback.print_exc()

    elif msg.error().code() != KafkaError._PARTITION_EOF:
        print(msg.error())
        break

# Unregisters the processor from the processors table 
processors_table.delete({"_id":PROCESSOR_ID})
