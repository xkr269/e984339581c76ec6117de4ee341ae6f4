The Eye In The Sky

Real time image processing from remote controlled drones


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