#! /usr/bin/python

import logging
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



# Retrieves current cluster name
with open('/opt/mapr/conf/mapr-clusters.conf', 'r') as f:
    first_line = f.readline()
    cluster_name = first_line.split(' ')[0]
    logging.debug('Cluster name : {}'.format(cluster_name))

POSITIONS_STREAM = '/mapr/' + cluster_name + '/positions_stream'   # Positions stream path
POSITIONS_TABLE = '/mapr/' + cluster_name + '/positions_table'  # Path for the table that stores positions information
ZONES_TABLE = '/mapr/' + cluster_name + '/zones_table'   # Zones table path

UPLOAD_FOLDER = 'static'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

sleep_time = 0
  
# Create database connection
connection_str = "localhost:5678?auth=basic;user=mapr;password=mapr;ssl=false"
connection = ConnectionFactory().get_connection(connection_str=connection_str)
positions_table = connection.get_or_create_store(POSITIONS_TABLE)
zones_table = connection.get_or_create_store(ZONES_TABLE)

if args.reset:
  # Reset positions stream
  os.system('maprcli stream delete -path ' + POSITIONS_STREAM)
  print("positions stream deleted")

  # Init drone position
  print("drone position reset")
  positions_table.insert_or_replace(doc={'_id': 'drone_1', "zone":"home_base"})


# Configure positions stream
if not os.path.islink(POSITIONS_STREAM):
    logging.debug("creating stream {}".format(POSITIONS_STREAM))
    os.system('maprcli stream create -path ' + POSITIONS_STREAM + ' -produceperm p -consumeperm p -topicperm p -copyperm p -adminperm p')
    logging.debug("stream created")


logging.debug("creating producer for {}".format(POSITIONS_STREAM))
p = Producer({'streams.producer.default.stream': POSITIONS_STREAM})


def stream_video(consumer):
    running = True
    frameId = 0
    print('Start of loop')
    while running:
        print('  Polling message')
        msg = consumer.poll() #timeout=1)
        print('  Message obtained')
        if msg is None:
            print('  Message is None')
            continue
        if not msg.error():
            print('  Message is valid, receiving frame ' + str(frameId))
            yield (b'--frame\r\n' + b'Content-Type: image/png\r\n\r\n' + msg.value() + b'\r\n\r\n')
            time.sleep(sleep_time)
            frameId += 1
        elif msg.error().code() != KafkaError._PARTITION_EOF:
            print('  Bad message')
            print(msg.error())
            running = False
        # if frameId > 100:
        #     running = False


def create_stream(drone_id):
  stream_path = '/mapr/' + cluster_name + "/" + drone_id
  if not os.path.islink(stream_path):
    logging.debug("creating stream {}".format(stream_path))
    os.system('maprcli stream create -path ' + stream_path + ' -produceperm p -consumeperm p -topicperm p -copyperm p -adminperm p')
    logging.debug("stream created")

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TEMPLATES_AUTO_RELOAD'] = True


@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r

######  Web pages  #####

@app.route('/')
def home():
  return render_template("teits_ui.html",zones=zones_table.find())

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

  # zones = []
  # for zone in zones_table.find():
  #   zones.append(zone)


  return render_template("edit_ui.html",zones=zones_table.find())

@app.route('/save_zone',methods=['POST'])
def save_zone():
  name = request.form['zone_name']
  width = request.form['zone_width']
  height = request.form['zone_height']
  top = request.form['zone_top']
  left = request.form['zone_left']
  zone_doc = {'_id': name, "height":height,"width":width,"top":top,"left":left}
  zones_table.insert_or_replace(doc=zone_doc)
  return "{} updated".format(name)

@app.route('/delete_zone',methods=['POST'])
def delete_zone():
  name = request.form['zone_name']
  zones_table.delete(_id=name)
  return "{} Deleted".format(name)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/update_drone_position',methods=["POST"])
def update_drone_position():
  drone_id = request.form["drone_id"]
  drop_zone = request.form["drop_zone"]
  try:
    from_zone = positions_table.find_by_id(drone_id)["zone"]
  except:
    from_zone = "unpositionned"
  positions_table.insert_or_replace(doc={'_id': drone_id, "zone":drop_zone})
  message = {"drone_id":drone_id,"from_zone":from_zone,"drop_zone":drop_zone}
  p.produce("positions", json.dumps(message))
  return "{} moved from zone {} to zone {}".format(drone_id,from_zone,drop_zone)

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


@app.route('/video_stream/<drone_id>/<topic>')
def video_stream(drone_id,topic):
  create_stream(drone_id)
  stream = "/" + drone_id + ":" + topic
  consumer_group = randint(3000, 3999)
  consumer = Consumer({'group.id': consumer_group, 'default.topic.config': {'auto.offset.reset': 'latest'}})
  consumer.subscribe([stream])
  return Response(stream_video(consumer), mimetype='multipart/x-mixed-replace; boundary=frame')






app.run(debug=True,host='0.0.0.0',port=80)


