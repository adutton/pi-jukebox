#!/bin/bash

# Set NUMLOCK on OR exit if not at console
if ! /usr/bin/setleds -D +num 2>&1 >/dev/null
then
    exit
fi

# Wait until the MPD port is accepting connections
while [ $(netstat -lt | grep ':6600' | wc -l) -eq 0 ]; do
    sleep 1s;
done

# Repeatedly call the jukebox until it exits cleanly
until python3 /home/pi/jukebox.py
do
    echo 'Restarting from crash'
    sleep 2s
done
