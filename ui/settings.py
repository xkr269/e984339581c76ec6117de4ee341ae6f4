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
RECORDING_TABLE = DATA_FOLDER + 'recording_table' # Table to excahnge informations while recording

# Generic Settings
ALLOWED_LAG = 2 # Allowed lag between real time events and processed events
OFFSET_RESET_MODE = 'latest' # latest for running the demo, earliest can be used for replaying existing streams
DISPLAY_STREAM_NAME = "processed" # source or processed


ACTIVE_DRONES = 2 # Number of pilot launched
NUMBER_OF_PROCESSORS = 2 # Each processor can analyse 2 to 3 images / second
DRONE_MODE = "live"    # "replay" : replay recorded streams; "video" : plays video files, "live": send data from drones.
NO_FLIGHT = True  # when True, the flight commands aren't sent to the drones.


STREAM_FPS = 20.0 # FPS sent to the datastore
REPLAYER_FPS = 24.0 # FPS replayed from recording
RECORDER_FPS = 24.0 # FPR recorded from drone

DIRECTIONAL_MODE = "OPTIMIZED" # LINEAR (only x & y moves), OPTIMIZED (minimizes turns) or FORWARD (turns and forward)


# Drone wait ratios
FORWARD_COEF = 3 # Time taken to move 1m
ANGULAR_COEF = 8.0 # Time taken to rotate 360 deg
