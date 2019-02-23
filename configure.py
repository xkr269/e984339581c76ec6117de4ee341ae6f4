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


if not os.path.exists(settings.RECORDING_FOLDER):
    os.makedirs(settings.RECORDING_FOLDER)

print("Recording directory created")

if not os.path.exists(settings.LOG_FOLDER):
    os.makedirs(settings.LOG_FOLDER)

print("Log directory created")
# Create streams

print("Creating streams ...")

def create_stream(stream_path):
  if not os.path.islink(stream_path):
    os.system('maprcli stream create -path ' + stream_path + ' -produceperm p -consumeperm p -topicperm p -copyperm p -adminperm p')


os.system("rm -rf " + settings.POSITIONS_STREAM)
create_stream(settings.POSITIONS_STREAM)
print("Positions stream created")
os.system("rm -rf " + settings.PROCESSORS_STREAM)
create_stream(settings.PROCESSORS_STREAM)
print("Processors stream created")
os.system("rm -rf " + settings.VIDEO_STREAM)
create_stream(settings.VIDEO_STREAM)
print("Video stream created")
create_stream(settings.RECORDING_STREAM)
print("Recording stream created")


print("initializing drones")
os.system("rm -rf " + settings.DRONEDATA_TABLE)
DRONEDATA_TABLE = settings.DRONEDATA_TABLE
ZONES_TABLE = settings.ZONES_TABLE
CLUSTER_IP = settings.CLUSTER_IP
CLUSTER_NAME = settings.CLUSTER_NAME
SECURE_MODE = settings.SECURE_MODE
username = settings.USERNAME
password = settings.PASSWORD
PEM_FILE = settings.PEM_FILE

# Initialize databases
if SECURE_MODE:
  connection_str = "{}:5678?auth=basic;" \
                           "user={};"
                           "password={};"
                           "ssl=true;" \
                           "sslCA={};" \
                           "sslTargetNameOverride={}".format(CLUSTER_IP,username,password,PEM_FILE,CLUSTER_IP)
else:
  connection_str = "{}:5678?auth=basic;user={};password={};ssl=false".format(CLUSTER_IP,username,password)


connection = ConnectionFactory().get_connection(connection_str=connection_str)
dronedata_table = connection.get_or_create_store(DRONEDATA_TABLE)
for DRONE_ID in ["drone_1","drone_2","drone_3"]:
    dronedata_table.insert_or_replace({"_id":DRONE_ID,
                                       "flight_data":{"battery":50,"fly_speed":5.0},
                                       "log_data":"unset",
                                       "count":0,
                                       "connection_status":"disconnected",
                                       "position": {"zone":"home_base", "status":"landed","offset":0.0}})


zones_table = connection.get_or_create_store(ZONES_TABLE)
try:
  # Create home_base if doesn't exist
  zones_table.insert({"_id":"home_base","height":"10","left":"45","top":"45","width":"10","x":"0","y":"0"})
except:
  pass

print("updating init file")
os.system("sed -i 's/demo\.mapr\.com/{}/g' init.sh".format(CLUSTER_NAME))
os.system("sed -i 's/demo\.mapr\.com/{}/g' clean.sh".format(CLUSTER_NAME))

print("Configuration complete, initialize environment variables with source init.sh then run the aplication using start.py")
