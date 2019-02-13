#! /usr/bin/python

"""
Pilot application for TEITS demo

What it does :
- Connects to the drone
- Gets the video
- Stores each frame in a folder
- Stores frame indexes in a stream (video_stream) in a topic named with drone id
- reads movements instructions from a stream

What has to be defined :
- the drone ID
- FPS for the transmitted video
- the project folder on the cluster

"""

import traceback
import time
from time import sleep
import os
import sys
try:
    import av
except:
    pass
import tellopy
import json
import threading
from random import randint
from confluent_kafka import Producer, Consumer, KafkaError
from mapr.ojai.storage.ConnectionFactory import ConnectionFactory
from math import atan2, sqrt, pi, floor
from shutil import copyfile
import base64
from io import BytesIO
import logging
import base64
import numpy as np

import settings

DRONE_ID = sys.argv[1]

logging.basicConfig(filename=settings.LOG_FOLDER + "pilot_{}.log".format(DRONE_ID) ,level=logging.INFO)


KILL_ALL = False

# Remote mode sends data through a remote MaprDB buffer instead of writing directly to the FS
REMOTE_MODE = False
if len(sys.argv)>2:
    if sys.argv[2] == "remote":
        REMOTE_MODE = True

logging.info("Remote mode : {}".format(REMOTE_MODE))


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
    logging.info("stream {} is missing. Exiting.".format(stream_path))
    sys.exit()


STREAM_FPS = settings.STREAM_FPS
REPLAYER_FPS = settings.REPLAYER_FPS
RECORDER_FPS = settings.RECORDER_FPS
PROJECT_FOLDER = settings.PROJECT_FOLDER




# Wait ratios
FORWARD_COEF = settings.FORWARD_COEF # Time taken to move 1m
ANGULAR_COEF = settings.ANGULAR_COEF # Time taken to rotate 360 deg

DRONE_MODE = settings.DRONE_MODE
NO_FLIGHT = settings.NO_FLIGHT 
DIRECTIONAL_MODE = settings.DIRECTIONAL_MODE

 
CLUSTER_NAME = get_cluster_name()
CLUSTER_IP = get_cluster_ip()

ROOT_PATH = settings.ROOT_PATH
DATA_FOLDER = settings.DATA_FOLDER
IMAGE_FOLDER = DATA_FOLDER + "images/" + DRONE_ID + "/source/"
VIDEO_STREAM = settings.VIDEO_STREAM
POSITIONS_STREAM = settings.POSITIONS_STREAM
DRONEDATA_TABLE = settings.DRONEDATA_TABLE
ZONES_TABLE = settings.ZONES_TABLE
RECORDING_STREAM = settings.RECORDING_STREAM
RECORDING_FOLDER = settings.RECORDING_FOLDER

BUFFER_TABLE = DATA_FOLDER + "{}_buffer".format(DRONE_ID)

current_angle = 0.0


time_tracker = {"min":1000,"max":0,"count":0,"avg":0}


# Create database connection
connection_str = CLUSTER_IP + ":5678?auth=basic;user=mapr;password=mapr;ssl=false"
connection = ConnectionFactory().get_connection(connection_str=connection_str)
zones_table = connection.get_or_create_store(ZONES_TABLE)
dronedata_table = connection.get_or_create_store(DRONEDATA_TABLE)
dronedata_table.insert_or_replace({"_id":DRONE_ID,
                                   "status":"ready",
                                   "last_command":"land",
                                   "flight_data":{"battery":50,"fly_speed":5.0},
                                   "log_data":"unset",
                                   "count":0,
                                   "connection_status":"disconnected",
                                   "position": {"zone":"home_base", "status":"landed","offset":0.0}})

buffer_table = connection.get_or_create_store(BUFFER_TABLE)

# test if folders exist and create them if needed
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

# create sreams if needed
check_stream(VIDEO_STREAM)
check_stream(POSITIONS_STREAM)


#######################    VIDEO PROCESSING    ##################

# Function for transfering the video frames to FS and Stream
def get_drone_video(drone):

    logging.info("Getting video from drone")

    global STREAM_FPS
    global DRONE_ID
    global VIDEO_STREAM
    global IMAGE_FOLDER
    global REMOTE_MODE
    global KILL_ALL

    logging.info("producing video stream into {}".format(VIDEO_STREAM))

    video_producer = Producer({'streams.producer.default.stream': VIDEO_STREAM})

    current_sec = 0
    last_frame_time = 0
    container = av.open(drone.get_video_stream())
    try:
        start_time = time.time()
        received_frames = 0
        sent_frames = 0
        while drone.state != drone.STATE_QUIT and not KILL_ALL:
            logging.info("Drone is connected - decoding container")
            try:
                for frame in container.decode(video=0):
                    if KILL_ALL:
                        break
                    # if drone.state != drone.STATE_CONNECTED:
                    #     logging.info("Drone disconnected - QUITTING VIDEO THREAD")
                    #     break
                    received_frames += 1
                    current_time = time.time()
                    if current_time > (last_frame_time + float(1/STREAM_FPS)):
                        start_time = time.time()
                        index = frame.index
                        new_image = IMAGE_FOLDER + "frame-{}.jpg".format(index)
                        try:
                            if REMOTE_MODE:


                                memfile = BytesIO()
                                frame.to_image().save(memfile,format="JPEG",width=480,height=270) # getvalue
                                image_bytes = base64.b64encode(memfile)
                                json_dict = {"_id":"{}".format(index),
                                            "image_name":new_image,
                                            "image_bytes":image_bytes}
                                buffer_table.insert_or_replace(json_dict)
                            else:
                                frame.to_image().save(new_image)
                                video_producer.produce(DRONE_ID + "_source", json.dumps({"drone_id":DRONE_ID,
                                                                                         "index":index,
                                                                                         "image":new_image}))
                        except Exception as ex:
                            logging.info(ex)
                            traceback.print_exc()

                        sent_frames += 1
                        last_frame_time = time.time()
                        duration = last_frame_time - start_time
                        time_tracker["min"] = min(time_tracker["min"],duration)
                        time_tracker["max"] = max(time_tracker["max"],duration)
                        time_tracker["count"] += 1
                        time_tracker["avg"] = (time_tracker["avg"] * (time_tracker["count"] - 1) + duration) / time_tracker["count"]


                    # Print stats every second
                    elapsed_time = time.time() - start_time
                    if int(elapsed_time) != current_sec:
                        logging.info("Elapsed : {} s, received {} fps , sent {} fps".format(int(elapsed_time),received_frames,sent_frames))
                        logging.info("Time tracker : {} ".format(time_tracker))
                        received_frames = 0
                        sent_frames = 0
                        current_sec = int(elapsed_time)
            except:
                logging.exception("fails")

    # Catch exceptions
    except Exception:
        traceback.print_exc()


# def stream_recording():
#     global STREAM_FPS
#     global REPLAYER_FPS
#     global DRONE_ID
#     global VIDEO_STREAM
#     global IMAGE_FOLDER
#     global RECORDING_STREAM
#     global RECORDING_FOLDER
#     global KILL_ALL

#     logging.info("Producing video from records into {}".format(VIDEO_STREAM))
#     video_producer = Producer({'streams.producer.default.stream': VIDEO_STREAM})
#     consumer_group = str(time.time())
#     video_consumer = Consumer({'group.id': consumer_group,'default.topic.config': {'auto.offset.reset': 'earliest'}})
    
#     current_sec = 0
#     last_frame_time = 0

#     stream_zone = dronedata_table.find_by_id(DRONE_ID)["position"]["zone"]
#     video_consumer.subscribe([RECORDING_STREAM + ":" + stream_zone])


#     try:
#         start_time = time.time()
#         received_frames = 0
#         sent_frames = 0
#         logging.info("{} subscribed to {} video stream".format(DRONE_ID,stream_zone))
#         while not KILL_ALL:
#             current_zone = dronedata_table.find_by_id(DRONE_ID)["position"]["zone"]
#             # logging.info("current_zone = {}".format(current_zone))
#             if current_zone != stream_zone:
#                 stream_zone = current_zone
#                 consumer_group = str(time.time())
#                 video_consumer = Consumer({'group.id': consumer_group,'default.topic.config': {'auto.offset.reset': 'earliest'}})
#                 video_consumer.subscribe([RECORDING_STREAM + ":" + stream_zone])
#                 logging.info("subscribed to {} video stream".format(stream_zone))

#             msg = video_consumer.poll(timeout=1)


#             if msg is None :
#                 # logging.info("timeout")
#                 consumer_group = str(time.time())
#                 video_consumer = Consumer({'group.id': consumer_group,'default.topic.config': {'auto.offset.reset': 'earliest'}})
#                 video_consumer.subscribe([RECORDING_STREAM + ":" + stream_zone])
#                 continue

#             if not msg.error():
#                 json_msg = json.loads(msg.value().decode('utf-8'))
#                 # logging.info("emulator for {} . producing {}".format(DRONE_ID,json_msg["image"]))
#                 received_frames += 1
#                 current_time = time.time()

#                 if current_time > (last_frame_time + float(1/STREAM_FPS)):
#                     frame_index = json_msg["index"]
#                     source_image = json_msg["image"]
#                     new_image = IMAGE_FOLDER + "frame-{}.jpg".format(frame_index)
#                     copyfile(source_image,new_image)
#                     video_producer.produce(DRONE_ID+"_source", json.dumps({"drone_id":DRONE_ID,
#                                                                         "index":frame_index,
#                                                                         "image":new_image}))
#                     sent_frames += 1
#                     last_frame_time = time.time()

#             elif msg.error().code() == KafkaError._PARTITION_EOF:
#                 logging.info("end of partition")
#                 consumer_group = str(time.time())
#                 video_consumer = Consumer({'group.id': consumer_group,'default.topic.config': {'auto.offset.reset': 'earliest'}})
#                 video_consumer.subscribe([RECORDING_STREAM + ":" + stream_zone])
#                 logging.info("subscribed to {} video stream".format(stream_zone))
#                 continue

#             # Print stats every second
#             elapsed_time = time.time() - start_time
#             if int(elapsed_time) != current_sec:
#                 logging.info("Elapsed : {} s, received {} fps , sent {} fps".format(int(elapsed_time),received_frames,sent_frames))
#                 received_frames = 0
#                 sent_frames = 0
#                 time_tracker["min"] = 100
#                 time_tracker["max"] = 0
#                 current_sec = int(elapsed_time)

#             time.sleep(1/REPLAYER_FPS)

#     # Catch exceptions
#     except Exception:
#         traceback.print_exc()



def play_video_from_file(): # file name has to be "zone_name.mp4"
    global DRONE_ID
    global VIDEO_STREAM
    global IMAGE_FOLDER
    global KILL_ALL
    global STREAM_FPS

    # logging.info("producing into {}".format(VIDEO_STREAM))
    if not REMOTE_MODE :
        video_producer = Producer({'streams.producer.default.stream': VIDEO_STREAM})
    current_sec = 0
    last_frame_time = 0

    try:
        start_time = time.time()
        received_frames = 0
        sent_frames = 0
        while not KILL_ALL:
            try:
                stream_zone = dronedata_table.find_by_id(DRONE_ID)["position"]["zone"]
                zone_video = RECORDING_FOLDER + stream_zone + ".mp4"
                logging.info("playing {} ".format(zone_video))
                container = av.open(zone_video)
                
                for frame in container.decode(video=0):
                    if KILL_ALL:
                        break
                    received_frames += 1
                    current_time = time.time()
                    if current_time > (last_frame_time + float(1/STREAM_FPS)):
                        begin_process = time.time()
                        index = frame.index
                        new_image = IMAGE_FOLDER + "frame-{}.jpg".format(index)
                        try:
                            if REMOTE_MODE:
                                frame_format = frame.format.name
                                ndarray = frame.to_ndarray(width=640,height=360)
                                data_type = ndarray.dtype.name
                                shape = ndarray.shape
                                enc_bytes = ndarray.tobytes()
                                enc_str = base64.b64encode(enc_bytes)
                                buffer_table.insert_or_replace({"_id":"{}".format(index),
                                                                "image_name":new_image,
                                                                "image_bytes":enc_str,
                                                                "shape_0":shape[0],
                                                                "shape_1":shape[1],
                                                                "data_type":data_type,
                                                                "format":frame_format})

                            else:
                                logging.info("producing {}".format(new_image))
                                video_producer.produce(DRONE_ID+"_source", json.dumps({"drone_id":DRONE_ID,
                                                                                    "index":index,
                                                                                    "image":new_image}))
                                frame.to_image().save(new_image)
                        except Exception as ex:
                            logging.info(ex)
                            traceback.print_exc()
                        sent_frames += 1
                        last_frame_time = time.time()
                        end_process = time.time()
                        duration = end_process - begin_process
                        time_tracker["min"] = min(time_tracker["min"],duration)
                        time_tracker["max"] = max(time_tracker["max"],duration)
                        time_tracker["count"] += 1
                        time_tracker["avg"] = (time_tracker["avg"] * (time_tracker["count"] - 1) + duration) / time_tracker["count"]


                        current_zone = dronedata_table.find_by_id(DRONE_ID)["position"]["zone"]
                        if current_zone != stream_zone:
                            stream_zone = current_zone
                            zone_video = RECORDING_FOLDER + stream_zone + ".mp4"
                            container = av.open(zone_video)
                            logging.info("playing {} ".format(zone_video))
                            break

                    # Print stats every second
                    elapsed_time = time.time() - start_time
                    if int(elapsed_time) != current_sec:
                        logging.info("Elapsed : {} s, received {} fps , sent {} fps".format(int(elapsed_time),received_frames,sent_frames))
                        logging.info("Time tracker : {} ".format(time_tracker))
                        time_tracker["min"] = 100
                        time_tracker["max"] = 0
                        received_frames = 0
                        sent_frames = 0
                        current_sec = int(elapsed_time)

                    # time.sleep(1/REPLAYER_FPS)

            except KeyboardInterrupt:
                break

            except Exception:
                traceback.print_exc()
                continue

    # Catch exceptions
    except Exception:
        traceback.print_exc()



#######################    MOVE PROCESSING    ##################

def move_to_zone(drone,start_zone,drop_zone):


    global current_angle

    try:

        logging.info("...   moving from {} to {}".format(start_zone,drop_zone))
        # get start_zone coordinates
        current_position_document = zones_table.find_by_id(start_zone)
        current_position = (float(current_position_document["x"]),float(current_position_document["y"]))
        # get drop_zone coordinates
        new_position_document = zones_table.find_by_id(drop_zone)
        new_position = (float(new_position_document["x"]),float(new_position_document["y"]))

        # calcul du deplacement
        y = new_position[1] - current_position[1] # Back and Front
        x = new_position[0] - current_position[0] # Left and Right

        # distance a parcourir
        distance = sqrt(x*x + y*y)
        offset = 0

        if DIRECTIONAL_MODE == "DIRECT" :
            command = "go {} {} 0 100".format(y*100,x*100)
            mutation = {"$put":{"last_command":command}}
            drone.custom_command(command)
            time.sleep(max(1,distance * FORWARD_COEF))

        if DIRECTIONAL_MODE == "LINEAR" :
            if y > 0:
                drone.forward(y)
            elif y < 0:
                drone.backward(-y)
            if y != 0:
                logging.info("Sleep {}".format(abs(FORWARD_COEF*y)))
                time.sleep(max(1,abs(FORWARD_COEF*y)))

            if x > 0:
                drone.right(x)
            elif x < 0:
                drone.left(-x)
            if x != 0:
                logging.info("Sleep {}".format(abs(FORWARD_COEF*x)))
                time.sleep(max(1,abs(FORWARD_COEF*x)))
        else:
            # calcul angle de rotation vs axe Y   
            target_angle = (atan2(x,y)*180/pi + 180) % 360 - 180

            logging.info("drone orientation : {}".format(current_angle))
            logging.info("target angle : {}".format(target_angle))

            angle =  (target_angle - current_angle + 180) % 360 - 180 
            logging.info("direction vs drone : {}".format(angle))

            if DIRECTIONAL_MODE == "OPTIMIZED":
                # calcul du cadran
                cadran = int(floor(angle/45))
                logging.info("cadran = {}".format(cadran))

                # calcul offset et deplacement
                if cadran in [-1,0]:
                    offset = angle
                    move = drone.forward
                elif cadran in [1,2]:
                    offset = angle - 90
                    move = drone.right
                elif cadran in [-4,3]:
                    offset = (angle + 90) % 180 - 90
                    move = drone.backward
                elif cadran in [-2,-3]:
                    offset = angle + 90
                    move = drone.left

                logging.info("offset : {}".format(offset))
                logging.info("move : {}".format(move))

            elif DIRECTIONAL_MODE == "FORWARD":
                move = drone.forward
                offset = angle 
                logging.info("forward mode, offset : {}".format(offset))

            

            logging.info("distance : {}".format(distance))

            if abs(offset) > 0:
                logging.info("###############      turning {} degrees".format(angle))
                drone.turn(offset)
                logging.info("sleep {}".format(max(1,float(abs(offset) * ANGULAR_COEF / 360))))
                time.sleep(max(1,float(abs(offset) * ANGULAR_COEF / 360)))

            # deplacement        
            if distance > 0 :
                move(distance)
                logging.info("sleep {}".format(max(1,distance * FORWARD_COEF)))
                time.sleep(max(1,distance * FORWARD_COEF))

            current_angle += offset
    except:
        traceback.print_exc()
        logging.exception("fails")

        drone.land()
        time.sleep(1)
        sys.exit()


def set_homebase():
    dronedata_table.update(_id=DRONE_ID,mutation={"$put": {"position": {"zone":"home_base", "status":"landed","offset":current_angle}}})
    logging.info("Drone position reset to homebase")



#######################    FLIGHT DATA  PROCESSING    ##################

def handler(event, sender, data, **args):
    drone = sender
    if event is drone.EVENT_LOG_DATA:
        log_data_doc = {"mvo":{"vel_x":data.mvo.vel_x,
                               "vel_y":data.mvo.vel_y,
                               "vel_z":data.mvo.vel_z,
                               "pos_x":data.mvo.pos_x,
                               "pos_y":data.mvo.pos_y,
                               "pos_z":data.mvo.pos_z},
                        "imu":{"acc_x":data.imu.acc_x,
                               "acc_y":data.imu.acc_y,
                               "acc_z":data.imu.acc_z,
                               "gyro_x":data.imu.gyro_x,
                               "gyro_y":data.imu.gyro_y,
                               "gyro_z":data.imu.gyro_z}}
        mutation = {"$put": {'log_data': log_data_doc}}
        dronedata_table.update(_id=DRONE_ID,mutation=mutation)


    if event is drone.EVENT_FLIGHT_DATA:
        fly_speed = sqrt(data.north_speed*data.north_speed + data.east_speed*data.east_speed);
        flight_data_doc = {"battery":str(data.battery_percentage),
                           "fly_speed":str(data.fly_speed),
                           "wifi_strength":str(data.wifi_strength)}
        mutation = {"$put": {'flight_data': flight_data_doc}}
        try:
            dronedata_table.update(_id=DRONE_ID,mutation=mutation)
        except Exception as ex:
            logging.exception("fails")

            if "EXPIRED" in str(ex):
                logging.info("EXPIRED")



#######################       MAIN FUNCTION       ##################

def main():

    logging.info("Pilot started for {}".format(DRONE_ID))

    global current_angle
    global KILL_ALL

    fly_drone = DRONE_MODE=="live" and not NO_FLIGHT

    set_homebase() # reset drone position in the positions table

    drone_number = int(DRONE_ID.split('_')[1])
    
    if settings.DRONE_MODE  == "live":
        drone = tellopy.Tello()
    else:
        drone = tellopy.Tello(port=9000+drone_number) #,simulate=True) 

    if DRONE_MODE == "live":
        drone.subscribe(drone.EVENT_FLIGHT_DATA, handler)
        drone.connect()
        drone.wait_for_connection(600)

    dronedata_table.update(_id=DRONE_ID,mutation={"$put":{'connection_status':"connected"}})

    # create video thread
    if DRONE_MODE == "replay":
        videoThread = threading.Thread(target=stream_recording)
    elif DRONE_MODE == "video":
        videoThread = threading.Thread(target=play_video_from_file)
    elif DRONE_MODE == "live":
        videoThread = threading.Thread(target=get_drone_video,args=[drone])

    videoThread.start()


    start_time = time.time()
    consumer_group = DRONE_ID + str(time.time())
    positions_consumer = Consumer({'group.id': consumer_group,'default.topic.config': {'auto.offset.reset':'latest'}})
    positions_consumer.subscribe([POSITIONS_STREAM + ":" + DRONE_ID])

    while True:
        try:
            # logging.info("waiting for instructions - drone state = {}".format(dronedata_table.find_by_id(DRONE_ID)["connection_status"]))
            msg = positions_consumer.poll(timeout=1)
            if msg is None:
                # Check that Drone is still connected
                # if not, restarts.
                if DRONE_MODE != "live":
                    if drone.state != drone.STATE_CONNECTED:
                        dronedata_table.update(_id=DRONE_ID,mutation={"$put":{'connection_status':"disconnected"}})

                    if drone.state == drone.STATE_QUIT:
                        drone.sock.close()
                        while videoThread.isAlive() or drone.video_thread_running:
                            logging.info("wait for threads to stop")
                            time.sleep(1)
                        logging.info("reconnecting ...")
                        drone = tellopy.Tello()
                        drone.connect()
                        drone.wait_for_connection(600)
                        dronedata_table.update(_id=DRONE_ID,mutation={"$put":{'connection_status':"connected"}})
                        logging.info("connected - starting video thread")
                        # recreate video thread
                        videoThread = threading.Thread(target=get_drone_video,args=[drone])
                        videoThread.start()
                continue

            # Proceses moving instructions
            if not msg.error():

                json_msg = json.loads(msg.value().decode('utf-8'))

                if "action" in json_msg:
                    action = json_msg["action"]
                    if action == "takeoff":
                        logging.info("....................................................  Takeoff")
                        mutation = {"$put":{"status":"busy"}}
                        dronedata_table.update(_id=DRONE_ID,mutation=mutation)
                        mutation = {"$put":{"last_command":"takeoff"}}
                        dronedata_table.update(_id=DRONE_ID,mutation=mutation)
                        drone.takeoff()
                        mutation = {"$put":{"position.status":"flying"}}
                        dronedata_table.update(_id=DRONE_ID,mutation=mutation)
                        mutation = {"$put":{"status":"waiting"}}
                        dronedata_table.update(_id=DRONE_ID,mutation=mutation)

                    if action == "land":
                        logging.info("....................................................  Land")
                        mutation = {"$put":{"status":"busy"}}
                        dronedata_table.update(_id=DRONE_ID,mutation=mutation)
                        mutation = {"$put":{"last_command":"land"}}
                        dronedata_table.update(_id=DRONE_ID,mutation=mutation)
                        drone.land()
                        mutation = {"$put":{"position.status":"landed"}}
                        dronedata_table.update(_id=DRONE_ID,mutation=mutation)
                        mutation = {"$put":{"status":"waiting"}}
                        dronedata_table.update(_id=DRONE_ID,mutation=mutation)  


                else:
                    from_zone = dronedata_table.find_by_id(DRONE_ID)["position"]["zone"]
                    drop_zone = json_msg["drop_zone"]
                    if drop_zone != from_zone:
                        if fly_drone:
                            mutation = {"$put":{"status":"busy"}}
                            move_to_zone(drone,from_zone,drop_zone)
                            while not drone.ready:
                                time.sleep(0.1)
                            mutation = {"$put":{"position.zone":drop_zone}}
                            dronedata_table.update(_id=DRONE_ID,mutation=mutation) 

                

            elif msg.error().code() != KafkaError._PARTITION_EOF:
                logging.info(msg.error())

        except KeyboardInterrupt:
            drone.land()
            break   

        except:
            logging.exception("land failed")
            drone.land()
            break
        time.sleep(1)

    logging.info("QUITTING")


    if not DRONE_MODE:
        drone.quit()

    KILL_ALL = True
    drone.killall = True
    logging.info("Exiting threads ... ")
    time.sleep(5)
    logging.info("threads killed.")

    sys.exit()


if __name__ == '__main__':
    main()
