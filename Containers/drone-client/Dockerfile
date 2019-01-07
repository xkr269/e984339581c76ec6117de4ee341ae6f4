FROM maprtech/pacc:6.1.0_6.0.0_ubuntu16_yarn_fuse_streams

# System
RUN sudo apt-get update -y
RUN sudo apt-get install -y vim
RUN sudo apt-get install -y locate
#RUN sudo apt-get install -y software-properties-common python-software-properties

# Python2.7 + Libs
RUN sudo apt-get install -y python2.7 python-pip
RUN sudo pip install --upgrade pip
RUN sudo apt-get install -y python-dev pkg-config
RUN sudo apt-get install -y libavformat-dev
RUN sudo apt-get install -y libavcodec-dev
RUN sudo apt-get install -y libavdevice-dev
RUN sudo apt-get install -y libavutil-dev
RUN sudo apt-get install -y libswscale-dev
RUN sudo apt-get install -y libavresample-dev
RUN sudo apt-get install -y libavfilter-dev
RUN sudo apt-get install -y libgtk2.0-dev
RUN sudo apt-get install -y libsm6 libxext6
RUN sudo pip install requests
RUN sudo apt-get install -y python-opencv
RUN sudo pip install image
RUN sudo apt-get install -y python-numpy
WORKDIR /tmp
RUN wget http://ffmpeg.org/releases/ffmpeg-3.2.tar.bz2
RUN tar -xjf ffmpeg-3.2.tar.bz2
WORKDIR ffmpeg-3.2
RUN ./configure --disable-static --enable-shared --disable-doc --disable-yasm
RUN make
RUN sudo make install
RUN sudo pip install av

# Python lib for Ryze (DJI) Tello drone
RUN sudo pip install tellopy
EXPOSE 9000/udp
EXPOSE 6038/udp

# MapR-ES setup
RUN export LD_LIBRARY_PATH=/opt/mapr/lib:/usr/lib/jvm/java-8-openjdk-amd64/jre/lib/amd64/server
RUN sudo pip install --global-option=build_ext --global-option="--library-dirs=/opt/mapr/lib" --global-option="--include-dirs=/opt/mapr/include/" mapr-streams-python

# Copy scripts
RUN sudo mkdir -p /home/mapr
RUN sudo chmod -Rf 777 /home/mapr
RUN sudo chown -Rf 2000:2000 /home/mapr
COPY stream_drone_video.py /home/mapr/
COPY video.mp4 /home/mapr/
COPY video-producer.py /home/mapr/
COPY startup.sh /home/mapr/
RUN sudo chmod +x /home/mapr/startup.sh
CMD /home/mapr/startup.sh
