
# PulseCheck - A HR analysis device

### Purpose
This device was developed as part of the Metropolia UAS hardware 1 & 2 courses. Purpose was to learn basic development and ideas of embedded devices with MicroPython

---
### Good to know
Remember to pull the dependant pico-lib submodule with the command `git submodule update --init`

The device can be connected to a WI-FI and a MQTT broker by editing the config in settings.txt. Original device was a Raspberry Pi Pico using a custom protoboard with hardware peripherals made by Metropolia

---
### Features

#### - Measure HR
Draws a live signal graph and measures the average BPM from the last 10 beats until the user presses to exit.

#### - HRV Analysis
Takes a 30 second measurement for local analysis, returns values such as RMSSD and SDNN

#### - Kubios Analysis
This feature only works with a Kubios API. Its the same as HRV but analysis is done via Kubios Cloud for much greater analysis with more values

#### - History
User can view up to 7 previous locally saved measurements on the device.
