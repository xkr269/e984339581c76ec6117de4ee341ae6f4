#! /usr/bin/python

"""

Face Detection Processor

Reads images from the main video stream
Detects faces on the image
Writes processed images to the main video steam


"""

import cv2
import os
import numpy
import time
import traceback
import json

from PIL import Image
from random import randint
from mapr.ojai.storage.ConnectionFactory import ConnectionFactory
from confluent_kafka import Consumer, KafkaError, Producer

import settings


############################       Settings        #########################

OFFSET_RESET_MODE = settings.OFFSET_RESET_MODE
PROCESSOR_ID = "processor_" + str(int(time.time())) + str(randint(0,10000)) # Generate processor UID

CLUSTER_NAME = settings.CLUSTER_NAME
CLUSTER_IP = settings.CLUSTER_IP
PROJECT_FOLDER = "/teits"
ROOT_PATH = '/mapr/' + CLUSTER_NAME + PROJECT_FOLDER
DRONEDATA_TABLE = settings.DRONEDATA_TABLE # Path for the table that stores drone data
PROCESSORS_TABLE = settings.PROCESSORS_TABLE # Path for the table that stores processor info
PROCESSORS_STREAM = settings.PROCESSORS_STREAM # Output Stream path
OUTPUT_STREAM = settings.VIDEO_STREAM
ALLOWED_LAG = settings.ALLOWED_LAG


# Build Ojai MapRDB access
connection_str = CLUSTER_IP + ":5678?auth=basic;user=mapr;password=mapr;ssl=false"
connection = ConnectionFactory().get_connection(connection_str=connection_str)
processors_table = connection.get_or_create_store(PROCESSORS_TABLE)
dronedata_table = connection.get_or_create_store(DRONEDATA_TABLE)



# Configure consumer
consumer_group = str(time.time())
consumer = Consumer({'group.id': consumer_group, 'default.topic.config': {'auto.offset.reset': OFFSET_RESET_MODE}})
consumer.subscribe([PROCESSORS_STREAM + ":" + PROCESSOR_ID])

# Configure producer
producer = Producer({'streams.producer.default.stream': OUTPUT_STREAM})


# Face detection params
cascPath = "haarcascade_frontalface_default.xml"
faceCascade = cv2.CascadeClassifier(cascPath)

def processing_function(message):
    global faceCascade

    # print("processing {}".format(message["image"]))
    image_array = numpy.array(Image.open(message["image"]))
    image = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = faceCascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )

    message["faces"] = len(faces)

    # Draw faces on the image
    for (x, y, w, h) in faces:
        cv2.rectangle(image, (x, y), (x+w, y+h), (0, 255, 0), 2)

    # Write new image to file system
    image_folder = ROOT_PATH + "/" + message["drone_id"] + "/images/faces/"
    if not os.path.exists(image_folder):
        os.makedirs(image_folder)
    new_image_path = image_folder + "frame-{}.jpg".format(message["index"])
    cv2.imwrite(new_image_path, image)
    message["image"] = new_image_path
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

            # Update drone document with faces count 
            dronedata_table.update(_id=processed_message["drone_id"],mutation={'$put': {'count': processed_message["faces"]}})


            # Write processed message to the output stream
            check_time = time.time()
            display_wait = True
            last_committed_offset = processors_table.find_by_id("offset")["offset"]
            while last_committed_offset != (offset - 1) and time.time() < (check_time + ALLOWED_LAG):
                if display_wait:
                    print('Waiting for previous frame to complete - Current offest : {}, Last committed offset : {}'.format(offset,last_committed_offset))
                    display_wait = False
                last_committed_offset = processors_table.find_by_id("offset")["offset"]

            print("Message {} - offset {} processed".format(received_msg["index"],offset))
            if not display_wait:
                print("Wait time : {}".format(time.time() - check_time))
            topic = processed_message["drone_id"] + "_faces"
            producer.produce(topic,json.dumps(processed_message))

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