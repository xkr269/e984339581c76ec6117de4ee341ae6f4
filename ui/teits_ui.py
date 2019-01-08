#! /usr/bin/python

import logging
import io
import os
import json
import time
import argparse
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

cluster_name = get_cluster_name()

PROJECT_FOLDER = "/teits"
ROOT_PATH = '/mapr/' + cluster_name + PROJECT_FOLDER

ZONES_TABLE =  ROOT_PATH + '/zones_table'   # Zones table path
SCENE_TABLE = ROOT_PATH + '/scene_table'   # Scene table path

POSITIONS_TABLE = ROOT_PATH + '/positions_table'  # Path for the table that stores positions information

VIDEO_STREAM = ROOT_PATH + '/video_stream'   # Video stream path
POSITIONS_STREAM = ROOT_PATH + '/positions_stream'   # Positions stream path
OFFSET_RESET_MODE = 'latest'


# Create database connection
connection_str = "localhost:5678?auth=basic;user=mapr;password=mapr;ssl=false"
connection = ConnectionFactory().get_connection(connection_str=connection_str)
positions_table = connection.get_or_create_store(POSITIONS_TABLE)
zones_table = connection.get_or_create_store(ZONES_TABLE)
scene_table = connection.get_or_create_store(SCENE_TABLE)


UPLOAD_FOLDER = 'static'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

video_sleep_time = 0
  
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
    running = True
    print('Start of loop for {}:{}'.format(VIDEO_STREAM,drone_id))
    consumer_group = randint(3000, 3999)
    consumer = Consumer({'group.id': consumer_group, 'default.topic.config': {'auto.offset.reset': OFFSET_RESET_MODE}})
    consumer.subscribe([VIDEO_STREAM+":"+drone_id])
    while running:
        msg = consumer.poll() #timeout=1)
        if msg is None:
            print('  Message is None')
            continue
        if not msg.error():
            print(msg.value().decode('utf-8'))
            json_msg = json.loads(msg.value().decode('utf-8'))
            frameId = json_msg['index']
            print('Message is valid, sending frame ' + str(frameId))
            try:
              image_name = ROOT_PATH + "/" + drone_id + "/images/source/frame-{}.jpg".format(frameId)
              with open(image_name, "rb") as imageFile:
                f = imageFile.read()
                b = bytearray(f)
              # time.sleep(1/20)
              yield (b'--frame\r\n' + b'Content-Type: image/jpg\r\n\r\n' + b + b'\r\n\r\n')
            except Exception as ex:
              print("can't open file {}".format(frameId))
              print(ex)
  
            if video_sleep_time:
              print("wait")
              time.sleep(video_sleep_time)
            frameId += 1
        elif msg.error().code() != KafkaError._PARTITION_EOF:
            print('  Bad message')
            print(msg.error())
            running = False
        # if frameId > 100:
        #     running = False





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

  if action == "takeoff":
    status = "flying"
  elif action == "land":
    status = "landed"
  else:
    status = current_status

  positions_table.insert_or_replace(doc={'_id': drone_id, "zone":drop_zone, "status":status})
  message = {"drone_id":drone_id,"from_zone":from_zone,"drop_zone":drop_zone,"action":action}
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




###################################
#####       SCENE EDITOR      #####
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

  try:
    scene_width = scene_table.find_by_id("scene")["width"]
  except:
    scene_width = 1
  return render_template("edit_ui.html",zones=zones_table.find(),scene_width=scene_width)

@app.route('/save_zone',methods=['POST'])
def save_zone():
  name = request.form['zone_name']
  width = request.form['zone_width']
  height = request.form['zone_height']
  top = request.form['zone_top']
  left = request.form['zone_left']
  x = request.form['zone_x']
  y = request.form['zone_y']
  zone_doc = {'_id': name, "height":height,"width":width,"top":top,"left":left,"x":x,"y":y}
  zones_table.insert_or_replace(doc=zone_doc)
  return "{} updated".format(name)

@app.route('/delete_zone',methods=['POST'])
def delete_zone():
  name = request.form['zone_name']
  zones_table.delete(_id=name)
  return "{} Deleted".format(name)

@app.route('/set_scene_width',methods=['POST'])
def set_scene_width():
  width = request.form['scene_width']
  scene_doc = {"_id":"scene","width":width}
  scene_table.insert_or_replace(doc=scene_doc)
  return "Width set"


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/update_zone_position',methods=["POST"])
def update_zone_position():
  zone_id = request.form["zone_id"]
  top = request.form["top"]
  left = request.form["left"]
  zone_doc = zones_table.find_by_id(zone_id)
  zone_doc["top"] = top
  zone_doc["left"] = left
  zones_table.insert_or_replace(doc=zone_doc)
  return json.dumps(zone_doc)




app.run(debug=True,host='0.0.0.0',port=80)


