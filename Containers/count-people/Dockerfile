FROM maprtech/pacc:6.1.0_6.0.0_ubuntu16_yarn_fuse_streams

# System
RUN sudo apt-get update -y
RUN sudo apt-get install -y vim
RUN sudo apt-get install -y locate

# Python3.5 + OpenCV 3.4.4
RUN sudo apt-get update -y; sudo apt-get install -y python3 python3-pip
RUN sudo pip3 install --upgrade pip
RUN sudo pip3 install image
RUN sudo pip3 install opencv-python
RUN sudo apt-get install -y libavformat-dev
RUN sudo apt-get install -y libavcodec-dev
RUN sudo apt-get install -y libavdevice-dev
RUN sudo apt-get install -y libavutil-dev
RUN sudo apt-get install -y libswscale-dev
RUN sudo apt-get install -y libavresample-dev
RUN sudo apt-get install -y libavfilter-dev
RUN sudo apt-get install -y libgtk2.0-dev
RUN sudo apt-get install -y libsm6 libxext6
RUN sudo pip3 install numpy
RUN sudo pip install maprdb-python-client
RUN sudo pip install Flask

# MapR-ES setup
RUN export LD_LIBRARY_PATH=/opt/mapr/lib:/usr/lib/jvm/java-8-openjdk-amd64/jre/lib/amd64/server
RUN sudo pip install --global-option=build_ext --global-option="--library-dirs=/opt/mapr/lib" --global-option="--include-dirs=/opt/mapr/include/" mapr-streams-python

# Copy scripts
<<<<<<< HEAD
# CMD /mapr/demo.mapr.com/teits/e984339581c76ec6117de4ee341ae6f4/Containers/count-people/startup.sh
=======
RUN sudo mkdir -p /home/mapr
RUN sudo chmod -Rf 777 /home/mapr
RUN sudo chown -Rf 2000:2000 /home/mapr
# COPY startup.sh /home/mapr/
# RUN sudo chmod +x /home/mapr/startup.sh
# CMD /home/mapr/startup.sh
>>>>>>> 3738b3225d6c2ee78bfd9b2804d29035d770e95f
