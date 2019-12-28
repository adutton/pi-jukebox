#!/bin/bash

pip3 install python-mpd2

if ! grep -Fxq "##### Automatically written by setup.sh" .profile
then
    echo "##### Automatically written by setup.sh" >>.profile
    echo "sh /home/pi/run-jukebox.sh" >>.profile
fi
