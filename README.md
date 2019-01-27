The Eye In The Sky

Real time image processing from remote controlled drones


run as root !


Prerequisites :
copy all files in your projet folder on the MapR file system
run ./setup.sh

Configure settings :
- PROJECT_FOLDER
- DRONE_MODE :
    - live : use with real drones. Run the pilot.py script on the laptop connected to the drone
    - video : use without drones. Import the videos you want to stream into the data/recording folder as {{zone_name}}.mp4
    - replay : you can record video from live drones using the recording application (python recording.py)

Launch project :
python configure.py on the main cluster (maprcli should be available)

then 
python start.py for main program
in live mode, pilot.py has to run on the computer connected to the drone 