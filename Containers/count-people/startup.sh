#!/bin/bash
cd /mapr/demo.mapr.com/teits/e984339581c76ec6117de4ee341ae6f4/Containers/count-people
export LD_LIBRARY_PATH=/opt/mapr/lib:/usr/lib/jvm/java-8-openjdk-amd64/jre/lib/amd64/server
python3 /mapr/demo.mapr.com/teits/e984339581c76ec6117de4ee341ae6f4/Containers/count-people/facedetect-img.py
