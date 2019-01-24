#! /usr/bin/python

"""

Settings files for TEITS demo project


"""
def get_cluster_name():
  with open('/opt/mapr/conf/mapr-clusters.conf', 'r') as f:
    first_line = f.readline()
    return first_line.split(' ')[0]

def get_cluster_ip():
  with open('/opt/mapr/conf/mapr-clusters.conf', 'r') as f:
    first_line = f.readline()
    return first_line.split(' ')[2].split(':')[0]



CLUSTER_NAME = get_cluster_name()
CLUSTER_IP = get_cluster_ip()


# Project folders
PROJECT_FOLDER = "/teits/" # Project folder from the cluster root
ROOT_PATH = '/mapr/' + CLUSTER_NAME + PROJECT_FOLDER
DATA_FOLDER = ROOT_PATH + "data/" # Folder to store the data
RECORDING_FOLDER = DATA_FOLDER + "recording/" # Folder to store the recordings



# Table and streams names
ZONES_TABLE = DATA_FOLDER + 'zones_table' # Table for storing informations about 
DRONEDATA_TABLE = DATA_FOLDER + 'dronedata_table'  # Table for storing informations about each drone
POSITIONS_STREAM = DATA_FOLDER + 'positions_stream'   # Stream for storign drone movements
PROCESSORS_TABLE = DATA_FOLDER + 'processors_table'  # Table for storing info about processors
PROCESSORS_STREAM = DATA_FOLDER + 'processors_stream'   # Stream to feed the processors
VIDEO_STREAM = DATA_FOLDER + 'video_stream' # Stream for the video frames metadata 
RECORDING_STREAM = DATA_FOLDER + 'recording_stream' # Stream for the video frames recording metadata 

# Generic Settings
ALLOWED_LAG = 2 # Allowed lag between real time events and processed events
OFFSET_RESET_MODE = 'latest' # latest for running the demo, earliest can be used for replaying existing streams
NUMBER_OF_PROCESSORS = 5 # Each processor can analyse 2 to 3 images / second
EMULATE_DRONES = True    # If emulation is enbled, drone will replay recorded stream in each zone.


