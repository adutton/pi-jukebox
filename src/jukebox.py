#!/usr/bin/python3

import fcntl
import logging
import os
import re
import sys
import termios
from mpd import MPDClient
from socket import gaierror

# RADIO STATIONS
# Found via https://radiostationusa.fm/states/washington
# 9710 710 ESPN KIRO http://playerservices.streamtheworld.com/api/livestream-redirect/KIROAMAAC.aac
# 9790 790 KGMI http://18683.live.streamtheworld.com/KGMIAMAAC.aac
# 91000 1000 KOMO http://live.wostreaming.net/direct/sinclair-komoamaac-ibc2
# 91170 1170 KPUG http://18683.live.streamtheworld.com/KPUGAMAAC.aac

# 9929 92.9 KISM http://playerservices.streamtheworld.com/api/livestream-redirect/KISMFMAAC.aac
# 9965 96.5 JACK http://c14icyelb.prod.playlists.ihrhls.com/7788_icy
# 91043 104.3 KAFE http://playerservices.streamtheworld.com/api/livestream-redirect/KAFEFMAAC.aac
# 91053 105.3 SPIRIT http://crista-kcms.streamguys1.com/kcmsmp3
# 91065 106.5 PRAISE https://crista-kwpz.streamguys1.com/kwpzmp3

SONG_PATTERN = re.compile(r'USB.+/(\d{3})-.*\.mp3')
RADIO_PATTERN = re.compile(r'RADIO/(\d{3,4})-.*.pls')
RANDOM_PLAY = "777"
RADIO_PREFIX = "9"
VOLUME_LIMIT = 35

class Jukebox():
    def __init__(self, server="localhost", port=6600):
        self.server = server
        self.port = port
        self.songs = []
        self.stations = []
        self.is_random_play = False
        self.reset_key_queue()
        self.mpd = None
        self.volume = 0
        self.is_running = True

    def get_status(self):
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
        status = self.get_status()

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
        if self.volume > VOLUME_LIMIT:
            self.mpd.setvol(VOLUME_LIMIT)
        if status['state'] != 'play':
            self.mpd.play()

        self.songs = {SONG_PATTERN.match(song)[1]: song for song in self.mpd.list('file') if SONG_PATTERN.match(song)}
        logging.info("Found {} jukebox songs".format(len(self.songs)))

        rootls = self.mpd.lsinfo()
        if "RADIO" in [entry.get("directory") for entry in rootls]:
            self.stations = {RADIO_PATTERN.match(radio["playlist"])[1]: radio["playlist"] for radio in self.mpd.lsinfo("RADIO") if RADIO_PATTERN.match(radio["playlist"])}
        else:
            self.stations = []
        logging.info("Found {} radio stations".format(len(self.stations)))

        # Enqueue startup song, if it exists
        if status["playlistlength"] == "0":
            self.enqueue_song("000")

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
        elif ord(key) == 127: # Backspace
            self.remove_key_from_queue()
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
            logging.debug("Ignoring keyboard {}".format(str(ord(key))))

    def reset_key_queue(self):
        logging.debug("Reset key queue")
        self.queue = []

    def remove_key_from_queue(self):
        logging.debug("Removing key from queue")
        self.queue = self.queue[:-1]

    def add_key_to_queue(self, key):
        logging.debug("Add key to queue {}".format(key))
        self.queue.append(key)
        song = ''.join(self.queue)

        # Radio stations start with a prefix
        if song[0] == RADIO_PREFIX:
            if len(song) > 3:
                logging.debug("Trying to find station {}".format(song[1:]))
                if self.enqueue_station(song[1:]) or len(song) >= 5:
                    self.reset_key_queue()
        elif len(song) == 3:
            self.reset_key_queue()
            if self.is_random_play:
                self.end_random_play()

            if (song == RANDOM_PLAY):
                if not self.is_random_play:
                    self.start_random_play()
                return
            logging.debug("Trying to find song {}".format(song))
            self.enqueue_song(song)

    def enqueue_song(self, number):
        logging.debug("Finding song {} to enqueue".format(number))

        if number in self.songs:
            logging.debug("Found song {}".format(self.songs[number]))

            # Make sure this song isn't already on queue
            status = self.get_status()

            if int(status["playlistlength"]) > 0:
                queue = [record["file"] for record in self.mpd.playlistinfo()]
                if self.songs[number] in queue:
                    logging.info("Did not queue song because it's already in queue")
                    return False

            logging.debug("Enqueuing {}".format(self.songs[number]))
            self.mpd.findadd("file", self.songs[number])
            if status["state"] != "play":
                self.mpd.play()
            return True
        else:
            logging.debug("Could not locate the song")
            return False

    def enqueue_station(self, number):
        logging.debug("Finding station {} to enqueue".format(number))

        if number in self.stations:
            logging.debug("Found station {}".format(self.stations[number]))

            # Make sure this station isn't on the queue
            status = self.get_status()

            if int(status["playlistlength"]) > 0:
                queue = [record["file"] for record in self.mpd.playlistinfo()]
                station_url = self.mpd.listplaylistinfo(self.stations[number])[0]["file"]

                if station_url in queue:
                    logging.info("Did not queue station because it's already in queue")
                    return False

            logging.debug("Enqueuing {}".format(self.stations[number]))
            self.mpd.load(self.stations[number])
            if status["state"] != "play":
                self.mpd.play()

            return True
        else:
            logging.debug("Could not locate the station")
            return False

    def start_random_play(self):
        if not self.is_random_play:
            logging.info("Starting random play")
            self.is_random_play = True

            status = self.get_status()

            # Delete everything off the list except the current song
            self.mpd.clear()

            for song in self.songs:
                logging.debug("Enqueuing {}".format(song))
                self.mpd.findadd("file", self.songs[song])

            self.mpd.shuffle()

            self.mpd.play()

    def end_random_play(self):
        if self.is_random_play:
            logging.info("Ending random play")
            self.is_random_play = False

            self.get_status()
            self.mpd.clear()

    def play(self):
        status = self.get_status()
        if status['state'] != 'play':
            self.mpd.play()

    def skip_song(self):
        status = self.get_status()
        if status['state'] == 'play':
            self.mpd.next()

    def increase_volume(self):
        # Pull current volume from system
        status = self.get_status()
        self.volume = int(status['volume'])

        if self.volume < VOLUME_LIMIT:
            self.volume += 1
            logging.info("Increasing volume to {}".format(self.volume))
            self.mpd.setvol(self.volume)
        else:
            self.mpd.setvol(VOLUME_LIMIT)

    def decrease_volume(self):
        # Pull current volume from system
        status = self.get_status()
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
