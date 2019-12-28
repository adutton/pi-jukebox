#!/usr/bin/python3

import fcntl
import logging
import os
import re
import sys
import termios
from mpd import MPDClient
from socket import gaierror

SONG_PATTERN = re.compile(r'USB.+/(\d{1,4}).*\.mp3')

class Jukebox():
    def __init__(self, server="localhost", port=6600):
        self.server = server
        self.port = port
        self.songs = []
        self.reset_key_queue()
        self.mpd = None
        self.volume = 0
        self.is_running = True

    def reconnect(self):
        status = None

        if self.mpd != None:
            try:
                status = self.mpd.status()
            except:
                self.mpd.disconnect()
                self.mpd = None

        if self.mpd != None:
            return status

        self.mpd = MPDClient()
        TIMEOUT_SECONDS = 1
        try:
            self.mpd.connect(host=self.server, port=self.port, timeout=TIMEOUT_SECONDS)
            status = self.mpd.status()
        except gaierror:
            logging.error("Could not connect to server, does the server name exist?")
            return None
        except ConnectionRefusedError:
            logging.error("Connection refused, is the port open?")
            return None
        except Exception as ex:
            logging.exception(ex)
            return None

        logging.info("Connected to MPD version {}".format(self.mpd.mpd_version))
        return status

    def initialize_connection(self):
        logging.debug("Checking to see if connection to {}:{} can be established".format(self.server, self.port))
        status = self.reconnect()

        if not status:
            return False

        self.volume = int(status['volume'])

        logging.debug("Volume is set to {}".format(self.volume))
        logging.debug("{} songs in queue".format(status['playlistlength']))

        # Set jukebox required settings
        self.mpd.consume(1)
        self.mpd.single(0)
        self.mpd.random(0)
        self.mpd.repeat(0)
        if status['state'] != 'play':
            self.mpd.play()

        self.songs = {SONG_PATTERN.match(song)[1]: song for song in self.mpd.list('file') if SONG_PATTERN.match(song)}
        logging.info("Found {} jukebox songs".format(len(self.songs)))

        return True

    def exit(self):
        self.close_connection()
        self.is_running = False

    def close_connection(self):
        if self.mpd:
            self.mpd.close()
            self.mpd.disconnect()
            self.mpd = None

    def handle_keyboard(self, key):
        if key in "0123456789":
            self.add_key_to_queue(key)
        elif key == "+":
            self.increase_volume()
        elif key == "-":
            self.decrease_volume()
        elif key == "s" or key == "/":
            self.skip_song()
        elif key == "r" or key == "\n":
            self.reset_key_queue()
        elif key == "i" or key == "*":
            self.close_connection()
            self.initialize_connection()
        else:
            logging.debug("Ignoring keyboard {}".format(key))

    def reset_key_queue(self):
        logging.debug("Reset key queue")
        self.queue = []

    def add_key_to_queue(self, key):
        logging.debug("Add key to queue {}".format(key))
        self.queue.append(key)

        if len(self.queue) >= 3:
            song = ''.join(self.queue)
            self.reset_key_queue()
            self.enqueue_song(song)

    def enqueue_song(self, number):
        logging.debug("Finding song {} to enqueue".format(number))

        if number in self.songs:
            logging.debug("Found song {}".format(self.songs[number]))

            # Make sure this song isn't already on queue
            status = self.reconnect()

            if int(status["playlistlength"]) > 0:
                queue = [record["file"] for record in self.mpd.playlistinfo()]
                if self.songs[number] in queue:
                    logging.info("Did not queue song because it's already in queue")
                    return

            logging.debug("Enqueuing {}".format(self.songs[number]))
            self.mpd.findadd("file", self.songs[number])
            if status["state"] != "play":
                self.mpd.play()
        else:
            logging.debug("Could not locate the song")

    def play(self):
        status = self.reconnect()
        if status['state'] != 'play':
            self.mpd.play()

    def skip_song(self):
        status = self.reconnect()
        if status['state'] == 'play':
            self.mpd.next()

    def increase_volume(self):
        # Pull current volume from system
        status = self.reconnect()
        self.volume = int(status['volume'])

        if self.volume < 100:
            self.volume += 1
            logging.info("Increasing volume to {}".format(self.volume))
            self.mpd.setvol(self.volume)
        else:
            self.mpd.setvol(100)

    def decrease_volume(self):
        # Pull current volume from system
        status = self.reconnect()
        self.volume = int(status['volume'])

        if self.volume > 0:
            self.volume -= 1
            logging.info("Decreasing volume to {}".format(self.volume))
            self.mpd.setvol(self.volume)
        else:
            self.mpd.setvol(0)

def get_char_keyboard():
    fd = sys.stdin.fileno()

    oldterm = termios.tcgetattr(fd)
    newattr = termios.tcgetattr(fd)
    newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
    termios.tcsetattr(fd, termios.TCSANOW, newattr)

    c = None
    try:
        c = sys.stdin.read(1)
    except IOError:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)

    return c

def main(argv):
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', "%H:%M:%S")
    handler.setFormatter(formatter)
    root.addHandler(handler)

    logging.debug("Starting jukebox")

    # Read server from command line
    # TODO: Read from configuration file?
    server = "localhost"
    if len(argv) > 0:
        server = argv[0]
    j = Jukebox(server=server)

    if not j.initialize_connection():
        logging.critical("Could not establish connection to MPD")
        return

    key = get_char_keyboard()
    while (key != "q"):
        for c in key:
            j.handle_keyboard(c)
        key = get_char_keyboard()

    logging.debug("Stopping jukebox")
    j.close_connection()
    sys.exit(0)

if __name__ == "__main__":
    main(sys.argv[1:])
