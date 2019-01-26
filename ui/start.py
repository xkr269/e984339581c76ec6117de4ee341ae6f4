#! /usr/bin/python


"""

The Eye In The Sky

Real time face detection from automated drones video streams

Use the settings.yaml file to define the project path and the number of processor processes.


"""

import os
import settings
import time
import subprocess


def launch_script(script_name,arg=None):
    if arg:
        return subprocess.Popen(["python", settings.ROOT_PATH + script_name,arg])
    else:
        return subprocess.Popen(["python", settings.ROOT_PATH + script_name])

def terminate_process(process):
    process.terminate()


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


print("Checklist complete, starting processes")


processes = []


# Used in simulation mode
# for i in [1]:
#     processes.append(launch_script("e984339581c76ec6117de4ee341ae6f4/ui/pilot.py",arg="drone_"+str(i)))
#     print("Drone {} pilot started ... ".format(i))

processes.append(launch_script("e984339581c76ec6117de4ee341ae6f4/ui/teits_ui.py"))
print("User interface started ... ")

if settings.DRONE_MODE == "replay":
    for i in range(settings.ACTIVE_DRONES):
        processes.append(launch_script("e984339581c76ec6117de4ee341ae6f4/ui/pilot.py",arg="drone_"+str(i+1)))
        print("Drone {} simulator started ... ".format(i+1))
        time.sleep(1)


processes.append(launch_script("e984339581c76ec6117de4ee341ae6f4/ui/dispatcher.py"))
print("Dispatcher started ... ")


for i in range(settings.NUMBER_OF_PROCESSORS):
    processes.append(launch_script("e984339581c76ec6117de4ee341ae6f4/ui/processor.py"))
    print("Processor {} started ... ".format(i+1))


while True:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        break

print('Terminating processes...')
for process in processes:
    terminate_process(process)
    print(".")
    time.sleep(1)


print("\n Terminated")


