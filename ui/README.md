# demobdp2018

MapR global data fabric demo

-------------------------------------------------------
Overview

This demo shows MapR ability to easily replicate data across the global namespace


-------------------------------------------------------
Prerequisites

You need to install this demo on a MapR cluster with file system, DB and streams, as well as a valid Enterpris license (can be a demo one).
The demo has to be run on a cluster node.
You need to be able to access the node on port 80.


-------------------------------------------------------
Installation process

- Clone the repository at the root of the MapR filesystem of your cluster
- Launch the setup script as root : (sudo) ./setup.sh
- Launch the init script as root : (sudo) python3 init.py
- Launch the demo as root : (sudo) ./start.sh


-------------------------------------------------------
Usage
start.sh : starts the demo
stop.sh : stops all the processes
init.py : (always run with python3) resets the environment

