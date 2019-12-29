#!/bin/bash

pip3 install python-mpd2

if ! grep -Fxq "##### Automatically written by setup.sh" .profile
then
    echo "##### Automatically written by setup.sh" >>.profile
    echo "sh /home/pi/run-jukebox.sh" >>.profile
fi

if [ ! -d moode-radio-utils ];
then
    git clone https://github.com/TheOldPresbyope/moode-radio-utils.git

    echo "Y" | sudo python3 ./moode-radio-utils/loadmyradios.py
fi