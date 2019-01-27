import fileinput
import os
import settings
import time
import subprocess
from mapr.ojai.storage.ConnectionFactory import ConnectionFactory

print("Starting pre-flight checks ... ")

# Create folders
if not os.path.exists(settings.DATA_FOLDER):
    os.makedirs(settings.DATA_FOLDER)

print("Data directory created")


# Create folders
if not os.path.exists(settings.RECORDING_FOLDER):
    os.makedirs(settings.RECORDING_FOLDER)

print("Recording directory created")


# Create streams

print("Creating streams ...")

def create_stream(stream_path):
  if not os.path.islink(stream_path):
    os.system('maprcli stream create -path ' + stream_path + ' -produceperm p -consumeperm p -topicperm p -copyperm p -adminperm p')

create_stream(settings.POSITIONS_STREAM)
print("Positions stream created")
create_stream(settings.PROCESSORS_STREAM)
print("Processors stream created")
create_stream(settings.VIDEO_STREAM)
print("Video stream created")
create_stream(settings.RECORDING_STREAM)
print("Recording stream created")


print("initializing drones")
DRONEDATA_TABLE = settings.DRONEDATA_TABLE
CLUSTER_IP = settings.CLUSTER_IP

# Create database connection
connection_str = CLUSTER_IP + ":5678?auth=basic;user=mapr;password=mapr;ssl=false"
connection = ConnectionFactory().get_connection(connection_str=connection_str)
dronedata_table = connection.get_or_create_store(DRONEDATA_TABLE)
for DRONE_ID in ["drone_1","drone_2","drone_3"]:
    dronedata_table.insert_or_replace({"_id":DRONE_ID,
                                       "flight_data":{"battery":50,"fly_speed":5.0},
                                       "log_data":"unset",
                                       "count":0,
                                       "connection_status":"disconnected",
                                       "position": {"zone":"home_base", "status":"landed","offset":0.0}})



with fileinput.FileInput(filename, inplace=True) as file:
    for line in file:
        print(line.replace("{{clustername}}", settings.CLUSTER_NAME), end='')

print("Configuration complete, run the aplication using start.py")
