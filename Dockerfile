FROM python:3.6.2-stretch
# FYI: Stretch is Debian...
MAINTAINER Shawn M. Jones <jones.shawn.m@gmail.com>

RUN apt-get update -y 

# install Java for Java stuff
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y default-jdk

# clean apt cache
RUN DEBIAN_FRONTEND=noninteractive apt-get clean

# create application space
RUN mkdir -p /app

# copy over application
COPY requirements.txt /app

# install Python requirements
RUN pip install -r /app/requirements.txt --no-cache-dir

# copy over application stuff
COPY . /app

# set up environment
WORKDIR "/app/off_topic"
#RUN python setup.py
RUN python -m nltk.downloader punkt
