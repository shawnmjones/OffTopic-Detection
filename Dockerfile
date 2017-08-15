FROM python:3.6.2-stretch
# FYI: Stretch is Debian...
MAINTAINER Shawn M. Jones <jones.shawn.m@gmail.com>

RUN apt-get update -y 

# install Java for Java stuff
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y default-jdk
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y git

# clean apt cache
RUN DEBIAN_FRONTEND=noninteractive apt-get clean

# create application space
RUN mkdir -p /app

# install Python requirements
COPY requirements.txt /app
WORKDIR /app
RUN pip install -r /app/requirements.txt --no-cache-dir
RUN git clone https://github.com/ptwobrussell/python-boilerpipe.git
WORKDIR /app/python-boilerpipe
RUN wget https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/boilerpipe/boilerpipe-1.2.0-bin.tar.gz
RUN python setup.py install

# copy over application stuff
COPY . /app

# set up environment
WORKDIR "/app/off_topic"
RUN python -m nltk.downloader punkt
