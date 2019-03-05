The Eye In The Sky

Real time image processing from remote controlled drones

<hr>
----------------------------------------------------------------------
1/ Overview

This demo shows how MapR simplifies processing of real time events at scale.
It displays analytics about the number of people counted in real time from video streams.

Drones are controlled via WiFi.


2/ Architecture

The architecture can be split in 3 main functions :
- ingestion of the video streams
- processing of the video frames
- user interface

Each part uses differents python scripts than can be run on multiple nodes.

2-1/ Ingestion : pilot.py
The pilot script has two roles :
- receiving the video stream from the drone and push the frames into the processing pipeline ("source" stream)
- reading the flight instructions from a stream ("positions" stream) and send them to the drones

It can be run in two modes :
- "live" mode : video streams are coming from drones
- "video" mode : video streams are played from recorded files

The pilot script is usually run on the cluster in "video" mode, and on one (or multiple) edge node in "live" mode.


2-2/ Processing : dispatcher.py and processor.py
The dispatcher takes each frame from the "source" stream and send them to the first available processor.
Once the processor has finished, it pushes the processed images in a "processed" stream.


2-3/ User interface : teits_ui.py
This script manages the web interface:
- sends the images to the UI
- get instructions to move the drones and pushes them to the "positions" stream


All the application settings are defined in the "settingss.py" file.


3/ Recommended infrastructure

In "live" mode, this demo is typically run on a laptop using VMs
In "video" mode, it can be run anywhere.

This application has been developped on CentOS 7

Drones used are the Ryze Tello.

3-1/ Central cluster
Single VM is usually enough.
10GB RAM recommended.
50GB storage.
One NIC connected to the host network

3-2/ Edge nodes
1GB RAM
10GB disk
Two NICs : one connected to the cluster, one bridged to a WiFi interface to connect the drone.

-----------------------------------------------------------------------------



run as root !


Prerequisites :

- go to your mapr FS root
- git clone https://github.com/xkr269/e984339581c76ec6117de4ee341ae6f4.git
- mv e984339581c76ec6117de4ee341ae6f4 teits
- cd teits
- ./setup.sh
- edit init.sh to update the cluster name
- source init.sh

Configure settings :
- DRONE_MODE :
    - live : use with real drones. Run the pilot.py script on the laptop connected to the drone
    - video : use without drones. Import the videos you want to stream into the data/recording folder as {{zone_name}}.mp4
    - replay : you can record video from live drones using the recording application (python recording.py)

Launch project :
python configure.py on the main cluster (maprcli should be available)

python start.py for main program

Access the zone editor : {{cluster_ip}}/edit
create and position the zones for the drones
At least a home_base zone should exist.
Typical position is x=0 y=0.


In live mode, pilot.py has to run on the computer connected to the drone 