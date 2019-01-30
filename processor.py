#! /usr/bin/python

"""

Face Detection Processor

Reads images from the main video stream
Detects stuff on the image , depending on the processor function
Writes processed images to the main video steam


"""

import cv2
import os
import numpy
import time
import traceback
import json
import imutils
import logging
from imutils.object_detection import non_max_suppression

from PIL import Image
from random import randint
from mapr.ojai.storage.ConnectionFactory import ConnectionFactory
from confluent_kafka import Consumer, KafkaError, Producer

import settings


############################       Settings        #########################


OFFSET_RESET_MODE = settings.OFFSET_RESET_MODE
PROCESSOR_ID = "processor_" + str(int(time.time())) + str(randint(0,10000)) # Generate processor UID

logging.basicConfig(filename=settings.LOG_FOLDER + "processor_{}.log".format(PROCESSOR_ID) ,level=logging.INFO)


CLUSTER_NAME = settings.CLUSTER_NAME
CLUSTER_IP = settings.CLUSTER_IP
DATA_FOLDER = settings.DATA_FOLDER
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

hog = cv2.HOGDescriptor()
hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

def people_detection(image):
    
    # detect people in the image
    (rects, weights) = hog.detectMultiScale(image, winStride=(4, 4),
        padding=(8, 8), scale=1.05)
 
    # # draw the original bounding boxes
    # for (x, y, w, h) in rects:
    #     cv2.rectangle(orig, (x, y), (x + w, y + h), (0, 0, 255), 2)
 
    # apply non-maxima suppression to the bounding boxes using a
    # fairly large overlap threshold to try to maintain overlapping
    # boxes that are still people
    rects = numpy.array([[x, y, x + w, y + h] for (x, y, w, h) in rects])
    pick = non_max_suppression(rects, probs=None, overlapThresh=0.65)
 
    # draw the final bounding boxes
    for (xA, yA, xB, yB) in pick:
        cv2.rectangle(image, (xA, yA), (xB, yB), (0, 255, 0), 2)

    return (image,len(pick))



def face_detection(image):

    global faceCascade

    # print("processing {}".format(message["image"]))
    while not os.path.isfile(image):
        time.sleep(0.05)
    image_array = numpy.array(Image.open(message["image"]))
    image = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = faceCascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )

    # Draw faces on the image
    for (x, y, w, h) in faces:
        cv2.rectangle(image, (x, y), (x+w, y+h), (0, 255, 0), 2)

    return (image,len(faces))




def processing_function(message):

    image_array = numpy.array(Image.open(message["image"]))
    image = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
    image = imutils.resize(image, width=min(400, image.shape[1]))
    (processed_image,count) = people_detection(image) 

    message["count"] = count


    image_folder = DATA_FOLDER + "/images/" + message["drone_id"] + "/processed/"
    if not os.path.exists(image_folder):
        os.makedirs(image_folder)
    processed_image_path = image_folder + "frame-{}.jpg".format(message["index"])
    cv2.imwrite(processed_image_path, processed_image)
    message["image"] = processed_image_path

    return message


# Sets processor as available
# print("Set {} as available".format(PROCESSOR_ID))
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
            dronedata_table.update(_id=processed_message["drone_id"],mutation={'$put': {'count': processed_message["count"]}})


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
            topic = processed_message["drone_id"] + "_processed"
            producer.produce(topic,json.dumps(processed_message))

            # Commit offset
            processors_table.insert_or_replace({"_id":"offset","offset":offset})
            
            # Set processor as available
            # print("Set {} as available".format(PROCESSOR_ID))
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