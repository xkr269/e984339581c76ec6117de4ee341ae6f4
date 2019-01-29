#! /usr/bin/python

import math
import io
import os
import json
import time
import argparse
import traceback
from random import randint
from shutil import copyfile
from copy import deepcopy


from flask import Flask, render_template, request, Response, flash, redirect, url_for
from mapr.ojai.storage.ConnectionFactory import ConnectionFactory
from confluent_kafka import Producer, Consumer, KafkaError

import settings


#### Kill previous instances
current_pid = os.getpid()
print(current_pid)
all_pids = os.popen("ps aux | grep 'teits_ui.py' | awk '{print $2}'").read().split('\n')[:-1]
for pid in all_pids:
    if int(pid) != current_pid:
        print("killing {}".format(pid))
        os.system("kill -9 {}".format(pid))



parser = argparse.ArgumentParser()
parser.add_argument('-d', '--reset', dest='reset', default=False, help='Reset stream and drone positions')
args = parser.parse_args()

CLUSTER_NAME = settings.CLUSTER_NAME
CLUSTER_IP = settings.CLUSTER_IP

PROJECT_FOLDER = settings.PROJECT_FOLDER
ROOT_PATH = CLUSTER_NAME + settings.PROJECT_FOLDER
RECORDING_FOLDER = settings.RECORDING_FOLDER
VIDEO_STREAM = settings.VIDEO_STREAM
POSITIONS_STREAM = settings.POSITIONS_STREAM
OFFSET_RESET_MODE = settings.OFFSET_RESET_MODE
DRONEDATA_TABLE = settings.DRONEDATA_TABLE
ZONES_TABLE = settings.ZONES_TABLE
RECORDING_STREAM = settings.RECORDING_STREAM


DISPLAY_STREAM_NAME = settings.DISPLAY_STREAM_NAME # "source" for original images, "processed" for processed image


# Create database connection
connection_str = CLUSTER_IP + ":5678?auth=basic;user=mapr;password=mapr;ssl=false"
connection = ConnectionFactory().get_connection(connection_str=connection_str)
zones_table = connection.get_or_create_store(ZONES_TABLE)
dronedata_table = connection.get_or_create_store(DRONEDATA_TABLE)

# Positions stream. Each drone has its own topic
positions_producer = Producer({'streams.producer.default.stream': POSITIONS_STREAM})
recording_producer = Producer({'streams.producer.default.stream': RECORDING_STREAM})

def stream_video(drone_id):
    global VIDEO_STREAM
    global OFFSET_RESET_MODE
    global DISPLAY_STREAM_NAME

    print('Start of loop for {}:{}'.format(VIDEO_STREAM,drone_id))
    consumer_group = str(time.time())
    consumer = Consumer({'group.id': consumer_group, 'default.topic.config': {'auto.offset.reset': OFFSET_RESET_MODE}})
    consumer.subscribe([VIDEO_STREAM + ":" + drone_id + "_" + DISPLAY_STREAM_NAME ])
    current_stream = DISPLAY_STREAM_NAME
    while True:
        if DISPLAY_STREAM_NAME != current_stream:
          consumer.subscribe([VIDEO_STREAM + ":" + drone_id + "_" + DISPLAY_STREAM_NAME ])
          current_stream = DISPLAY_STREAM_NAME
          print("stream changed #############################")
        msg = consumer.poll(timeout=1)
        if msg is None:
            continue
        if not msg.error():
            json_msg = json.loads(msg.value().decode('utf-8'))
            image = json_msg['image']
            print("playing {}".format(image))
            try:
              while not os.path.isfile(image):
                    time.sleep(0.05)
              with open(image, "rb") as imageFile:
                f = imageFile.read()
                b = bytearray(f)
              yield (b'--frame\r\n' + b'Content-Type: image/jpg\r\n\r\n' + b + b'\r\n\r\n')
            except Exception as ex:
              print("can't open file {}".format(image))
              print(ex)

        elif msg.error().code() != KafkaError._PARTITION_EOF:
            print('  Bad message')
            print(msg.error())
            break
    print("Stopping video loop for {}".format(drone_id))


app = Flask(__name__)



###################################
#####         MAIN UI         #####
###################################

# Main UI
@app.route('/')
def home():
  zones = zones_table.find()
  display = DISPLAY_STREAM_NAME
  drones = []
  for i in range(settings.ACTIVE_DRONES):
    drones.append("drone_{}".format(i+1))
  return render_template("teits_ui.html",active_drones=settings.ACTIVE_DRONES,zones=zones,display=display,drones=drones)



# Gets move instructions from the web UI and push the new instruction to the posisions stream 
# Each move instruction has a from zone, a destination (drop) zone and an action to be performed after the move.
@app.route('/set_drone_position',methods=["POST"])
def set_drone_position():
  drone_id = request.form["drone_id"]

  drop_zone = request.form["drop_zone"]
  
  try:
    action = request.form["action"]
  except:
    action = "wait"

  try:
    current_position = dronedata_table.find_by_id(drone_id)["position"]
    print("current position = {}".format(current_position))
    from_zone = current_position["zone"]
    current_status = current_position["status"]
  except:
    traceback.print_exc()
    from_zone = "home_base"
    current_status = "landed"


  if from_zone != drop_zone and current_status == "landed":
    # If move is required but drone is not flying, then takeoff before moving
    action = "takeoff"
    message = {"drone_id":drone_id,"drop_zone":from_zone,"action":action}
    positions_producer.produce(drone_id, json.dumps(message))
    print("New instruction : {}".format(message))


  message = {"drone_id":drone_id,"drop_zone":drop_zone,"action":action}
  positions_producer.produce(drone_id, json.dumps(message))
  print("New instruction : {}".format(message))
  return "{} moved from zone {} to zone {} then {}".format(drone_id,from_zone,drop_zone,action)



# Returns current drone position ### unused
@app.route('/get_position',methods=["POST"])
def get_position():
  drone_id = request.form["drone_id"]
  try:
    position = dronedata_table.find_by_id(drone_id)["position"]["zone"]
  except:
    position = "unpositionned"
  return position



# Get next waypoint when patroling
@app.route('/get_next_waypoint',methods=["POST"])
def get_next_waypoint():
  # Get all available zones excluding home base
  waypoints = []
  for zone in zones_table.find():
    if zone["_id"] != "home_base":
      waypoints.append(zone["_id"])

  # Get current drone position
  drone_id = request.form["drone_id"]
  current_position = dronedata_table.find_by_id(drone_id)["position"]["zone"]

  # If drone is starting from home base, we assign him to a zone based on its ID.
  if current_position == "home_base":
    drone_number = int(drone_id.split("_")[1])
    current_index = drone_number % len(waypoints)
  else:
    current_index = waypoints.index(current_position)

  # Returns the next waypoint
  if current_index == len(waypoints)-1:
    new_index = 0
  else :
    new_index = current_index + 1
  return waypoints[new_index]


# Streams images from the video stream
@app.route('/video_stream/<drone_id>')
def video_stream(drone_id):
  return Response(stream_video(drone_id), mimetype='multipart/x-mixed-replace; boundary=frame')



# Returns drone current battery value 
@app.route('/get_battery_pct',methods=["POST"])
def get_battery_pct():
  drone_id = request.form["drone_id"]
  try:
    battery = dronedata_table.find_by_id(drone_id)["flight_data"]["battery"]
  except:
    battery = "-"
  return str(battery)


# Returns drone current speed
@app.route('/get_speed',methods=["POST"])
def get_speed():
  drone_id = request.form["drone_id"]
  if drone_id == "drone_1":
    try:
      speed = float(dronedata_table.find_by_id(drone_id)["flight_data"]["fly_speed"])
    except Exception as ex:
      traceback.print_exc()
      speed = 0.0
    return str(round(speed,2))
  return "0"



# Return drone current count
@app.route('/get_count',methods=["POST"])
def get_count():
  drone_id = request.form["drone_id"]
  if drone_id == "global":
    try:
        count = 0
        for dronedata in dronedata_table.find():
            count += int(dronedata["count"])
        return str(count)
    except Exception:
      traceback.print_exc()
      count = 0
      return "-"
  else:
    try:
      dronedata = dronedata_table.find_by_id(drone_id)
      count = dronedata["count"]
    except Exception as ex:
      print(ex)
      traceback.print_exc()
      count = 0
    return str(count)
  return "-"



# Changes DISPLAY stream
@app.route('/set_video_stream',methods=["POST"])
def set_video_stream():
  global DISPLAY_STREAM_NAME
  DISPLAY_STREAM_NAME = request.form["stream"]
  return "Display stream changed to {}".format(DISPLAY_STREAM_NAME)


# Returns drone current connection status
@app.route('/get_connection_status',methods=["POST"])
def get_connection_status():
  drone_id = request.form["drone_id"]
  return dronedata_table.find_by_id(drone_id)["connection_status"]


# Force landing
@app.route('/land',methods=["POST"])
def land():
    drone_id = request.form["drone_id"]
    drone = dronedata_table.find_by_id(drone_id)
    current_zone = drone["position"]["zone"]
    message = {"drone_id":drone_id,"drop_zone":current_zone,"action":"land"}
    positions_producer.produce(drone_id, json.dumps(message))
    return "Landing order sent for {}".format(drone_id)


# Resets drone position to home_base:landed in the database and the positions stream
@app.route('/reset_position',methods=["POST"])
def reset_position():
    drone_id = request.form["drone_id"]
    dronedata_table.update(_id=drone_id,mutation={"$put": {'position.zone': "home_base"}})
    message = {"drone_id":drone_id,"drop_zone":"home_base","action":"land"}
    positions_producer.produce(drone_id, json.dumps(message))
    return "Landing order sent for {}".format(drone_id)




###################################
#####          EDITOR         #####
###################################


# Editor UI
@app.route('/edit',methods=['GET', 'POST'])
def edit():
  if request.method == 'POST':
    # check if the post request has the file part
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], "background"))
  # for zone in zones_table.find():
  #   print(zone)

  return render_template("edit_ui.html",zones=zones_table.find())


# Save zone
@app.route('/save_zone',methods=['POST'])
def save_zone():
  name = request.form['zone_name']
  height = request.form['zone_height']
  width = request.form['zone_width']
  top = request.form['zone_top']
  left = request.form['zone_left']
  x = request.form['zone_x']
  y = request.form['zone_y']
  zone_doc = {'_id': name, "height":height,"width":width,"top":top,"left":left,"x":x,"y":y}
  print("Zone saved")
  print(zone_doc)
  zones_table.insert_or_replace(doc=zone_doc)
  return "{} updated".format(name)



# Retrieves current zone coordinates
@app.route('/get_zone_coordinates',methods=['POST'])
def get_zone_coordinates():
  zone_id = request.form['zone_id']
  zone_doc = zones_table.find_by_id(_id=zone_id)

  return json.dumps({"x":zone_doc["x"],"y":zone_doc["y"]})


# Delete zone
@app.route('/delete_zone',methods=['POST'])
def delete_zone():
  name = request.form['zone_name']
  try:
    zones_table.delete(_id=name)
  except:
    traceback.print_exc()
    return "Can't delete {}".format(name)
  return "{} Deleted".format(name)


# Update zone position
@app.route('/set_zone_position',methods=["POST"])
def set_zone_position():
  zone_id = request.form["zone_id"]
  top = request.form["top"]
  left = request.form["left"]
  zone_doc = zones_table.find_by_id(zone_id)
  zone_doc["top"] = top
  zone_doc["left"] = left
  zones_table.insert_or_replace(doc=zone_doc)
  return json.dumps(zone_doc)





app.run(debug=True,host='0.0.0.0',port=80)