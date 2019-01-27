import os
import settings
import time
import subprocess


print("Starting pre-flight checks ... ")

# Create folders
if not os.path.exists(settings.DATA_FOLDER):
    os.makedirs(settings.DATA_FOLDER)

print("Data directory created")


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


print("Configuration complete, run the aplication using start.py")
