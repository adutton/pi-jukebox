#!/usr/bin/python3

import logging
import random
import re
import sys
import termios
from socket import gaierror
from mpd import MPDClient

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

# Found via https://www.radio.net/genre/70s
# 91990 90s Hits HitsRadio http://playerservices.streamtheworld.com/api/livestream-redirect/977_90.mp3
# 91980 80s Planet http://80s.streamthenet.com:8888/stream/1/
# 91970 America's Greatest 70s Hits http://hydra.cdnstream.com/1823_128
# 91960 60s http://60s.streamthenet.com:8888/stream/1/

SONG_PATTERN = re.compile(r'(?:SDCARD|USB).*/(\d{3})-.*\..+')
RADIO_PATTERN = re.compile(r'RADIO/(\d{3,4})-.*.pls')
RANDOM_PLAY = "777"
STARTUP_SONG = "623"
RADIO_PREFIX = "9"
VOLUME_LIMIT = 35
CONNECT_TIMEOUT_SECONDS = 5

class Jukebox():
    def __init__(self, server="localhost", port=6600):
        self.server = server
        self.port = port

        self.songs = []
        self.stations = []
        self.is_random_play = False
        self.is_radio_play = False
        self.key_queue = []

        self.mpd = None

    def get_status(self):
        status = None

        if self.mpd is not None:
            try:
                status = self.mpd.status()
            except:
                self.mpd.disconnect()
                self.mpd = None

        if self.mpd is not None:
            return status

        self.mpd = MPDClient()
        self.mpd.timeout = CONNECT_TIMEOUT_SECONDS
        try:
            self.mpd.connect(host=self.server, port=self.port)
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

        logging.info("Connected to MPD version %s", self.mpd.mpd_version)
        return status

    def initialize_connection(self):
        logging.debug("Checking to see if connection to %s:%i can be established", self.server, self.port)
        status = self.get_status()

        if not status:
            return False

        volume = int(status['volume'])

        logging.debug("Volume is set to %i", volume)
        logging.debug("%s songs in queue", status['playlistlength'])

        # Set jukebox required settings
        self.mpd.consume(1)
        self.mpd.single(0)
        self.mpd.random(0)
        self.mpd.repeat(0)
        if volume > VOLUME_LIMIT:
            self.mpd.setvol(VOLUME_LIMIT)
        if status['state'] != 'play':
            self.mpd.play()

        self.songs = {SONG_PATTERN.match(song)[1]: song for song in self.mpd.list('file') if SONG_PATTERN.match(song)}
        logging.info("Found %i jukebox songs", len(self.songs))

        rootls = self.mpd.lsinfo()
        if "RADIO" in [entry.get("directory") for entry in rootls]:
            self.stations = {RADIO_PATTERN.match(radio["playlist"])[1]: radio["playlist"] for radio in self.mpd.lsinfo("RADIO") if RADIO_PATTERN.match(radio["playlist"])}
        else:
            self.stations = []
        logging.info("Found %i radio stations", len(self.stations))

        # TODO: In the future we might be able to detect these states
        self.is_random_play = False
        self.is_radio_play = False

        # Enqueue startup song, if it exists
        if status["playlistlength"] == "0":
            self.enqueue_song(STARTUP_SONG)

        return True

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
            logging.debug("Ignoring keyboard %i", ord(key))

    def reset_key_queue(self):
        logging.debug("Reset key queue")
        self.key_queue = []

    def remove_key_from_queue(self):
        logging.debug("Removing key from queue")
        self.key_queue = self.key_queue[:-1]

    def add_key_to_queue(self, key):
        logging.debug("Add key to queue %s", key)
        self.key_queue.append(key)
        song = ''.join(self.key_queue)

        # Radio stations start with a prefix
        if song[0] == RADIO_PREFIX:
            if len(song) > 3:
                logging.debug("Trying to find station %s", song[1:])
                if self.enqueue_station(song[1:]) or len(song) >= 5:
                    self.reset_key_queue()
        elif len(song) == 3:
            self.reset_key_queue()
            if self.is_radio_play:
                self.end_radio_play()

            if song == RANDOM_PLAY:
                if self.is_random_play:
                    self.end_random_play()
                else:
                    self.start_random_play()
                return

            if self.is_random_play:
                self.end_random_play()

            logging.debug("Trying to find song %s", song)
            self.enqueue_song(song)

    def enqueue_song(self, number):
        logging.debug("Finding song %s to enqueue", number)

        if number in self.songs:
            logging.debug("Found song %s", self.songs[number])

            # Make sure this song isn't already on queue
            status = self.get_status()

            if int(status["playlistlength"]) > 0:
                queue = [record["file"] for record in self.mpd.playlistinfo()]
                if self.songs[number] in queue:
                    logging.info("Did not queue song because it's already in queue")
                    return False

            logging.debug("Enqueuing %s", self.songs[number])
            self.mpd.findadd("file", self.songs[number])
            if status["state"] != "play":
                self.mpd.play()
            return True
        else:
            logging.debug("Could not locate the song")
            return False

    def enqueue_station(self, number):
        logging.debug("Finding station %s to enqueue", number)

        if number in self.stations:
            logging.debug("Found station %s", self.stations[number])

            status = self.get_status()
            self.mpd.clear()

            logging.debug("Enqueuing %s", self.stations[number])
            self.mpd.load(self.stations[number])
            if status["state"] != "play":
                self.mpd.play()

            self.is_radio_play = True

            return True

        logging.debug("Could not locate the station")
        return False

    def end_radio_play(self):
        self.is_radio_play = False
        self.get_status()
        self.mpd.clear()

    def start_random_play(self):
        if not self.is_random_play:
            logging.info("Starting random play")
            self.is_random_play = True

            self.get_status()

            # Add all songs except those in queue
            queue = [record["file"] for record in self.mpd.playlistinfo()]
            songs_to_add = [song for song in self.songs.values() if song not in queue]

            # Shuffle the songs
            random.shuffle(songs_to_add)

            for song in songs_to_add:
                logging.debug("Enqueuing %s", song)
                self.mpd.findadd("file", song)

            self.mpd.play()

    def end_random_play(self):
        if self.is_random_play:
            logging.info("Ending random play")
            self.is_random_play = False

            status = self.get_status()
            if status["state"] == "play":
                # Delete all songs except the first
                self.mpd.delete((1,))
            else:
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
        volume = int(status['volume'])

        if volume < VOLUME_LIMIT:
            volume += 1
            logging.info("Increasing volume to %i", volume)
            self.mpd.setvol(volume)
        else:
            self.mpd.setvol(VOLUME_LIMIT)

    def decrease_volume(self):
        # Pull current volume from system
        status = self.get_status()
        volume = int(status['volume'])

        if volume > 0:
            volume -= 1
            logging.info("Decreasing volume to %i", volume)
            self.mpd.setvol(volume)
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

    # Read server from command line as first argument
    server = "localhost"
    if len(argv) > 0:
        server = argv[0]
    j = Jukebox(server=server)

    if not j.initialize_connection():
        logging.critical("Could not establish connection to MPD")
        return

    key = get_char_keyboard()
    while key != "q":
        j.handle_keyboard(key)
        key = get_char_keyboard()

    logging.debug("Stopping jukebox")
    j.close_connection()
    sys.exit(0)


if __name__ == "__main__":
    main(sys.argv[1:])
