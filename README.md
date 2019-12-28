# Pi Jukebox
Recreating a Seeburg Select-o-matic LS325 internals using a Raspberry Pi.

Ingredients:
Seeburg Select-o-matic LS325
Raspberry Pi 3 with 4+ GB SD card
Audio cable - 3.5mm to red/white RCA jacks

# Install Moode
http://moodeaudio.org/

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

Configure startup settings to auto-boot to console
https://www.opentechguides.com/how-to/article/raspberry-pi/134/raspbian-jessie-autologin.html

Run `setup.sh` to install prequisites (via curl?)

Get `jukebox.py` into place

Run `python3 jukebox.py`

# References

Primary article for how to create Jukebox:
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

Python module for running MPD (mpd2):
https://python-mpd2.readthedocs.io/
