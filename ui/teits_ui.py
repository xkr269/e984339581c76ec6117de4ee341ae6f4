#! /usr/bin/python

import logging
import math
import io
import os
import json
import time
import argparse
import traceback
from random import randint
from werkzeug.utils import secure_filename

from flask import Flask, render_template, request, Response, flash, redirect, url_for
from mapr.ojai.storage.ConnectionFactory import ConnectionFactory
from confluent_kafka import Producer, Consumer, KafkaError



logging.basicConfig(filename='logs/ui.log',level=logging.DEBUG)



parser = argparse.ArgumentParser()
parser.add_argument('-d', '--reset', dest='reset', default=False, help='Reset stream and drone positions')
args = parser.parse_args()


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

PROJECT_FOLDER = "/teits"
ROOT_PATH = '/mapr/' + CLUSTER_NAME + PROJECT_FOLDER

ZONES_TABLE =  ROOT_PATH + '/zones_table'   # Zones table path
POSITIONS_TABLE = ROOT_PATH + '/positions_table'  # Path for the table that stores positions information
DRONEDATA_TABLE = ROOT_PATH + '/dronedata_table'  # Path for the table that stores drone data
SETTINGS_TABLE = ROOT_PATH + '/settings_table' # Path for the application settings

VIDEO_STREAM = ROOT_PATH + '/video_stream'   # Video stream path
POSITIONS_STREAM = ROOT_PATH + '/positions_stream'   # Positions stream path
OFFSET_RESET_MODE = 'latest' # earliest or latest
VIDEO_SLEEP_TIME = 0.0 # in second, used as speed control for re playing existing video
DISPLAY_STREAM_NAME = "raw" # "raw" for original images, "faces" for face detection


# Create database connection
connection_str = CLUSTER_IP + ":5678?auth=basic;user=mapr;password=mapr;ssl=false"
connection = ConnectionFactory().get_connection(connection_str=connection_str)
positions_table = connection.get_or_create_store(POSITIONS_TABLE)
zones_table = connection.get_or_create_store(ZONES_TABLE)
dronedata_table = connection.get_or_create_store(DRONEDATA_TABLE)


UPLOAD_FOLDER = 'static'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

  
if args.reset:
  # Reset positions stream
  os.system('maprcli stream delete -path ' + POSITIONS_STREAM)
  print("positions stream deleted")

  # Reset video stream
  os.system('maprcli stream delete -path ' + VIDEO_STREAM)
  print("video stream deleted")

  # Init drone position
  print("Positions table deleted")
  os.system('maprcli table delete -path ' + POSITIONS_TABLE)
  



# Configure positions stream
if not os.path.islink(POSITIONS_STREAM):
    logging.debug("creating stream {}".format(POSITIONS_STREAM))
    os.system('maprcli stream create -path ' + POSITIONS_STREAM + ' -produceperm p -consumeperm p -topicperm p -copyperm p -adminperm p')
    logging.debug("stream created")


# Positions stream. Each drone has its own topic
logging.debug("creating producer for {}".format(POSITIONS_STREAM))
positions_producer = Producer({'streams.producer.default.stream': POSITIONS_STREAM})


# Configure video stream
if not os.path.islink(VIDEO_STREAM):
    logging.debug("creating stream {}".format(VIDEO_STREAM))
    os.system('maprcli stream create -path ' + VIDEO_STREAM + ' -produceperm p -consumeperm p -topicperm p -copyperm p -adminperm p')
    logging.debug("stream created")


def create_stream(stream_path):
  if not os.path.islink(stream_path):
    os.system('maprcli stream create -path ' + stream_path + ' -produceperm p -consumeperm p -topicperm p -copyperm p -adminperm p')


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
        # print(DISPLAY_STREAM_NAME)
        if DISPLAY_STREAM_NAME != current_stream:
          consumer.subscribe([VIDEO_STREAM + ":" + drone_id + "_" + DISPLAY_STREAM_NAME ])
          current_stream = DISPLAY_STREAM_NAME
          print("stream changed")
        msg = consumer.poll(timeout=1)
        if msg is None:
            continue
        if not msg.error():
            json_msg = json.loads(msg.value().decode('utf-8'))
            image = json_msg['image']
            try:
              with open(image, "rb") as imageFile:
                f = imageFile.read()
                b = bytearray(f)
              yield (b'--frame\r\n' + b'Content-Type: image/jpg\r\n\r\n' + b + b'\r\n\r\n')
            except Exception as ex:
              print("can't open file {}".format(image))
              print(ex)
  
            if VIDEO_SLEEP_TIME :
              time.sleep(VIDEO_SLEEP_TIME)

        elif msg.error().code() != KafkaError._PARTITION_EOF:
            print('  Bad message')
            print(msg.error())
            break
    print("Stopping video loop for {}".format(drone_id))


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


###################################
#####         MAIN UI         #####
###################################

@app.route('/')
def home():
  return render_template("teits_ui.html",zones=zones_table.find())



@app.route('/set_drone_position',methods=["POST"])
def set_drone_position():
  drone_id = request.form["drone_id"]
  drop_zone = request.form["drop_zone"]
  try:
    action = request.form["action"]
  except:
    action = "wait"

  try:
    current_position = positions_table.find_by_id(drone_id)
    from_zone = current_position["zone"]
    current_status = current_position["status"]
  except:
    from_zone = "home_base"
    current_status = "landed"

  if from_zone != drop_zone and current_status == "landed":
    action = "takeoff"
  message = {"drone_id":drone_id,"drop_zone":drop_zone,"action":action}
  print(message)
  positions_producer.produce(drone_id, json.dumps(message))
  return "{} moved from zone {} to zone {} then {}".format(drone_id,from_zone,drop_zone,action)



@app.route('/get_position',methods=["POST"])
def get_position():
  drone_id = request.form["drone_id"]
  try:
    position = positions_table.find_by_id(drone_id)["zone"]
  except:
    position = "unpositionned"
  return position


@app.route('/get_next_waypoint',methods=["POST"])
def get_next_waypoint():
  waypoints = []
  for zone in zones_table.find():
    if zone["_id"] != "home_base":
      waypoints.append(zone["_id"])

  drone_id = request.form["drone_id"]
  current_position = positions_table.find_by_id(drone_id)["zone"]
  print("current : {}".format(current_position))
  
  if current_position == "home_base":
    drone_number = int(drone_id.split("_")[1])
    return waypoints[(drone_number + 1) % len(waypoints)]
  current_index = waypoints.index(current_position)
  if current_index == len(waypoints)-1:
    new_index = 0
  else :
    new_index = current_index + 1
  return waypoints[new_index]

@app.route('/video_stream/<drone_id>')
def video_stream(drone_id):
  return Response(stream_video(drone_id), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/get_battery_pct',methods=["POST"])
def get_battery_pct():
  drone_id = request.form["drone_id"]
  try:
    battery = dronedata_table.find_by_id(drone_id)["flight_data"]["battery"]
  except:
    battery = "-"
  return battery


@app.route('/get_log_data',methods=["POST"])
def get_log_data():
  drone_id = request.form["drone_id"]
  try:
    log_data = dronedata_table.find_by_id(drone_id)["log_data"]
  except:
    log_data = "no log data"
  return json.dumps(log_data)


@app.route('/get_speed',methods=["POST"])
def get_speed():
  drone_id = request.form["drone_id"]
  if drone_id == "drone_1":
    try:
      # log_data = dronedata_table.find_by_id(drone_id)["log_data"]
      # print(log_data)
      # if log_data == "unset":
      #   vel_x = 0
      #   vel_y = 0
      # else:
      #   vel_x = float(log_data["mvo"]["vel_x"])
      #   vel_y = float(log_data["mvo"]["vel_y"])
      # speed = math.sqrt(vel_x * vel_x + vel_y*vel_y)
      speed = float(dronedata_table.find_by_id(drone_id)["flight_data"]["fly_speed"])
    except Exception as ex:
      traceback.print_exc()
      speed = 0.0
    # print(speed)
    return str(round(speed,2))
  return "0"


@app.route('/get_count',methods=["POST"])
def get_count():
  drone_id = request.form["drone_id"]
  if drone_id == "global":
    try:
        count = 0
        for dronedata in dronedata_table.find():
            print("did : {} - dronedata : {}".format(drone_id,dronedata))
            count += int(dronedata["count"])
        return str(count)
    except Exception:
      traceback.print_exc()
      count = 0
      return "-"
  else:
    try:
      dronedata = dronedata_table.find_by_id(drone_id)
      print("did : {} - dronedata : {}".format(drone_id,dronedata))
      count = dronedata["count"]
    except Exception as ex:
      print(ex)
      traceback.print_exc()
      count = 0
    return str(count)
  return "-"



@app.route('/set_video_stream',methods=["POST"])
def set_video_stream():
  global DISPLAY_STREAM_NAME
  DISPLAY_STREAM_NAME = request.form["stream"]
  return "Ok"


@app.route('/get_connection_status',methods=["POST"])
def get_connection_status():
  drone_id = request.form["drone_id"]
  return dronedata_table.find_by_id(drone_id)["connection_status"]





###################################
#####          EDITOR         #####
###################################


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

  return render_template("edit_ui.html",zones=zones_table.find())

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

@app.route('/get_zone_coordinates',methods=['POST'])
def get_zone_coordinates():
  zone_id = request.form['zone_id']
  zone_doc = zones_table.find_by_id(_id=zone_id)

  return json.dumps({"x":zone_doc["x"],"y":zone_doc["y"]})


@app.route('/delete_zone',methods=['POST'])
def delete_zone():
  name = request.form['zone_name']
  zones_table.delete(_id=name)
  return "{} Deleted".format(name)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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