#! /usr/bin/python

"""

Settings files for TEITS demo project


"""


ACTIVE_DRONES = 3 # Number of pilot processes launched
NUMBER_OF_PROCESSORS = 2 # Each processor can analyse 2 to 3 images / second
DRONE_MODE = "live"    # "replay" : replay recorded streams; "video" : plays video files, "live": send data from drones.
NO_FLIGHT = True  # when True, the flight commands aren't sent to the drones.
REMOTE_MODE = True # When True, drones pilots are supposed to be far from the main cluster. 
                   # Images are then sent using a direct connection to a DB buffer in the main cluster

# Video settings
STREAM_FPS = 5.0 # FPS sent by the pilot to the datastore
REPLAYER_FPS = 24.0 # FPS replayed from recording
RECORDER_FPS = 24.0 # FPR recorded from drone



# Utilities

def get_cluster_name():
  with open('/opt/mapr/conf/mapr-clusters.conf', 'r') as f:
    first_line = f.readline()
    return first_line.split(' ')[0]

def get_cluster_ip():
  with open('/opt/mapr/conf/mapr-clusters.conf', 'r') as f:
    first_line = f.readline()
    return first_line.split(' ')[2].split(':')[0]


# Cluster information
CLUSTER_NAME = get_cluster_name()
CLUSTER_IP = get_cluster_ip()


# Project folders
PROJECT_FOLDER = "/teits/" # Project folder from the cluster root
ROOT_PATH = '/mapr/' + CLUSTER_NAME + PROJECT_FOLDER
DATA_FOLDER = ROOT_PATH + "data/" # Folder to store the data
RECORDING_FOLDER = DATA_FOLDER + "recording/" # Folder to store the recordings


# Table names
ZONES_TABLE = DATA_FOLDER + 'zones_table' # Table for storing informations about 
DRONEDATA_TABLE = DATA_FOLDER + 'dronedata_table'  # Table for storing informations about each drone
PROCESSORS_TABLE = DATA_FOLDER + 'processors_table'  # Table for storing info about processors
RECORDING_TABLE = DATA_FOLDER + 'recording_table' # Table to excahnge informations while recording


# Stream names
POSITIONS_STREAM = DATA_FOLDER + 'positions_stream'   # Stream for storign drone movements
PROCESSORS_STREAM = DATA_FOLDER + 'processors_stream'   # Stream to feed the processors
VIDEO_STREAM = DATA_FOLDER + 'video_stream' # Stream for the video frames metadata 
RECORDING_STREAM = DATA_FOLDER + 'recording_stream' # Stream for the video frames recording metadata 


# Generic Settings
ALLOWED_LAG = 2 # Allowed lag between real time events and processed events
OFFSET_RESET_MODE = 'latest' # latest for running the demo, earliest can be used for replaying existing streams
DISPLAY_STREAM_NAME = "processed" # source or processed- whichstream is displayed in the UI



# Drone settings
DIRECTIONAL_MODE = "OPTIMIZED" # LINEAR (only x & y moves), OPTIMIZED (minimizes turns) or FORWARD (turns and forward)
FORWARD_COEF = 3 # Time taken to move 1m - used to wait between move instructions
ANGULAR_COEF = 8.0 # Time taken to rotate 360 deg - used to wait between move instructions
