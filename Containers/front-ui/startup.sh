#!/bin/bash
#docker run --rm -it -p 6038:6038/udp -p 9000:9000/udp $MAPR_DOCKER_ARGS drone-client:latest "$@"
cd /home/mapr
export LD_LIBRARY_PATH=/opt/mapr/lib:/usr/lib/jvm/java-8-openjdk-amd64/jre/lib/amd64/server
python /home/mapr/consumer-flask.py /frenchpatrol/pilote:images /frenchpatrol/detection:images
#gunicorn --worker-class gevent --workers 1 --bind 0.0.0.0:5000 consumer-flask:app
