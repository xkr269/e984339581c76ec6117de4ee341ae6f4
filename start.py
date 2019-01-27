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


#### Kill previous instances
current_pid = os.getpid()
print(current_pid)
all_pids = os.popen("ps aux | grep 'start.py' | awk '{print $2}'").read().split('\n')[:-1]
for pid in all_pids:
    if int(pid) != current_pid:
        print("killing {}".format(pid))
        os.system("kill -9 {}".format(pid))



def launch_script(script_name,arg=None):
    if arg:
        return subprocess.Popen(["python", settings.ROOT_PATH + script_name,arg])
    else:
        return subprocess.Popen(["python", settings.ROOT_PATH + script_name])

def terminate_process(process):
    process.terminate()


processes = []


# Used in simulation mode
# for i in [1]:
#     processes.append(launch_script("e984339581c76ec6117de4ee341ae6f4/ui/pilot.py",arg="drone_"+str(i)))
#     print("Drone {} pilot started ... ".format(i))

processes.append(launch_script("teits_ui.py"))
print("User interface started ... ")

if settings.DRONE_MODE == "replay":
    for i in range(settings.ACTIVE_DRONES):
        processes.append(launch_script("pilot.py",arg="drone_"+str(i+1)))
        print("Drone {} simulator started ... ".format(i+1))
        time.sleep(1)


processes.append(launch_script("dispatcher.py"))
print("Dispatcher started ... ")


for i in range(settings.NUMBER_OF_PROCESSORS):
    processes.append(launch_script("processor.py"))
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


