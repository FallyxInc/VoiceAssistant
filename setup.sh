#!/bin/bash

#Run chmod +x setup.sh
# ./setup.sh


# Update and upgrade the system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python pip
sudo apt-get install -y python3-pip

# Install ffmpeg
sudo apt-get install -y ffmpeg

# Install paplay
sudo apt-get install -y pulseaudio

# Install the required Python packages
pip3 install -r requirements.txt
