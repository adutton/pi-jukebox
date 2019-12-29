# Pi Jukebox
This project seeks to recreate the internals of a 1960s Seeburg Select-o-matic LS325 using a Raspberry Pi.

Ingredients:
* Seeburg Select-o-matic LS325
* Raspberry Pi 3 with 4+ GB SD card
* Numeric keypad (USB)
* External drive (USB) for song storage (option)
* Audio cable - 3.5mm to red/white RCA jacks

# Install Moode
I wanted a Raspberry Pi-friendly linux distribution that could run Python3.

I tried Pi Jukebox, but was discouraged by the older packages that were installed.
 Then I tried just running MPD on a Raspbian Lite (Buster) but that required more tweaking and tuning than I wanted to use.

I landed on the Moode distribution which happened to be Python3-based.  http://moodeaudio.org/

It is a bit weird to setup because it's intended to be totally headless.

## Configuration

### Network Config
* SSID
* Password
* Country - United States

### Library Config
* Automatically update MPD database on USB insert/remove - YES

### Audio Config
* MPD
  * Autoplay after start - ON

### System Config
#### General
* Timezone - America/Los_Angeles
* Browser Title - Jukebox
#### System Modifications
* HDMI port - ON
* File system - Expand
#### Local Display
* Local UI display - ON
#### Local Services
* SSH term server - ON

Reboot

To use the 3.5mm jack:
* Run `sudo raspi-config` and set "Audio Output" to "Force 3.5mm"

* Prevent the blank screen from popping up
Edit `/home/pi/.xinitrc` and comment out the line starting with
```
chromium-browser ...
```

Turn on HDMI by editing `sudo nano /boot/config.txt` and commenting out the `hdmi_blanking` line.

Configure startup settings to autologin to console:
https://www.opentechguides.com/how-to/article/raspberry-pi/134/raspbian-jessie-autologin.html

Run `setup.sh` to install prequisites and set up the autorunning of the `jukebox.py`.

## Music

### Add music
Put music on a USB key, you may have to rescan in MPD to pick up the new songs.  Music should be prefixed with three digits and a dash `###-Song name.mp3`.  Music can be located on the internal SD card or the 

### Add radio stations
Add local radio stations using the web interface.  Name the radio stations `###-Station name`.  You can use 3 or 4 digits for the station.

## Use
To play a song, just type the three-digit number prefixed to the song name.

To play radio stations, start with 9, then the 3-4 digit station number.  Stations will be added to the queue but will never advance.  You'll need to skip the station to move to the next.

* Skip - `/` or `s`
* Increase volume - `+`
* Decrease volume - `-`
* Delete last number you typed - `BACKSPACE`
* Clear/reset all you've typed - `ENTER` or `r`
* Re-initialize everything - `i`
* Quit - `q`

### Random play
777
### Startup song
000

# References

MPD protocol
https://www.musicpd.org/doc/html/protocol.html

Python module for running MPD (mpd2):
https://python-mpd2.readthedocs.io/

I started my research with this article:
http://www.raspberry-pi-geek.com/Archive/2013/01/Extending-the-Raspberry-Pi-to-a-miniature-music-center

How to emulate Raspberry Pi on Mac:
https://grantwinney.com/how-to-create-a-raspberry-pi-virtual-machine-vm-in-virtualbox/
Debian - Install Sudo:
https://www.privateinternetaccess.com/forum/discussion/18063/debian-8-1-0-jessie-sudo-fix-not-installed-by-default

# Using the GPIO pins
gpiozero
https://gpiozero.readthedocs.io/en/stable/api_pins.html#module-gpiozero.pins.native

Mocking GPIO:
https://github.com/grantwinney/52-Weeks-of-Pi/blob/master/GPIOmock.py

GPIO:
https://sourceforge.net/projects/raspberry-gpio-python/
