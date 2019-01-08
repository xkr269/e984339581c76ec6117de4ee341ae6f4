import logging
import json
import os
from confluent_kafka import Consumer, KafkaError, Producer

# Retrieves current cluster name
with open('/opt/mapr/conf/mapr-clusters.conf', 'r') as f:
    first_line = f.readline()
    cluster_name = first_line.split(' ')[0]
    logging.debug('Cluster name : {}'.format(cluster_name))

POSITIONS_STREAM_PATH = '/mapr/' + cluster_name + '/video_stream'   # Positions stream path

c = Consumer({'group.id': "defgroup",'default.topic.config': {'auto.offset.reset': 'earliest'}})
c.subscribe([POSITIONS_STREAM_PATH + ":raw"])
while True:
  msg = c.poll()
  if msg is None:
    print("none")
    continue
  if not msg.error():
    json_msg = json.loads(msg.value().decode('utf-8'))
    print(json_msg['index'])
  elif msg.error().code() != KafkaError._PARTITION_EOF:
    print(msg.error())
