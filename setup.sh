yum install -y bzip2


wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
bash ./miniconda.sh -b -p /opt/miniconda
export PATH="/opt/miniconda/bin:$PATH"


yum install -y gcc-c++
yum install -y python-pip

pip install maprdb-python-client
pip install --global-option=build_ext --global-option="--library-dirs=/opt/mapr/lib" --global-option="--include-dirs=/opt/mapr/include/" mapr-streams-python

pip install numpy
pip install Flask
pip install imutils
pip install opencv-python
pip install Pillow

conda install av -c conda-forge -y

