# SMI260
SMI260 solar converter to MQTT gateway

This projects connects the Letrika SMI 260 plug-in solar inverter to an MQTT brocker by using the IMST IM871 USB stick.
It provides status informations and gives you the ability to turn the inverter on and off or set the maximum power output. 

The topics are:

 base topic   | topic   | description
------------- | ------------- | ------------
SMI/<last 4 digits of inverter serial>/  | DCVoltage       | output of the solar panel
SMI/<last 4 digits of inverter serial>/  | Energy          | total of emitted energy
SMI/<last 4 digits of inverter serial>/  | Frequency       | frequency of the AC output
SMI/<last 4 digits of inverter serial>/  | MaxPower        | limit of the AC output
SMI/<last 4 digits of inverter serial>/  | MaxPower/Set    | sets limit of AC output
SMI/<last 4 digits of inverter serial>/  | Power           | current power output
SMI/<last 4 digits of inverter serial>/  | PowerOn         | power state
SMI/<last 4 digits of inverter serial>/  | PowerOn/Set     | turn inverter on and off
SMI/<last 4 digits of inverter serial>/  | TemperatureDCAC | temperature of the DC/AC converter
SMI/<last 4 digits of inverter serial>/  | TemperatureDCDC | temperature of the DC/DC converter

## Setup

To setup install all dependencies: `pip3 install -r requirements.txt` 

and then run it with  `python3.7 ./SMI260MQTTGateway.py`

## Settings
You can configure the gateway ether by editing SMI260MQTTGateway.py with your settings (settings are in the lower part of the file) or you can set environment variables:

variable | description | default value 
---------|------------ | --------------
SUNSTICKPORT     | path to the USB stick        | /dev/ttyUSB0
MQTTSERVER       | IP of the MQTT brocker       | 127.0.0.1
MQTTSERVERPORT   | port of the MQTT brocker     | 1883
MQTTSERVERUSER   | user for MQTT authentication | -
MQTTSERVERPASS   | password for MQTT authentication | -
MQTTSERVERTOPIC  | MQTT topic the data is published to | SMI
POLL             | duration to poll in seconds | 120
SMI_LIST         | comma spearated list of last 4 digits of the inverter | 1234,2345
DEBUG            | set debug output            | False

## Docker

This repo contains a Dockerfile to dockerise the gateway. 

Build the container with `docker build -t smi260mqttgateway .`

and run it with at least the following command  `docker run --device=<path to your USB stick> -e SMI_LIST="<list of inverters> smi260mqttgateway`

Examples for a full stack can be found here [amd64](https://github.com/geeks-r-us/SMI260/blob/master/amd64.docker-compose.yml) [armv7](https://github.com/geeks-r-us/SMI260/blob/master/armv7.docker-compose.yml)
                                         
This is my first attempt to use python asyncio so excuse the bad code. Suggestions on how to improve that code are welcome.
Little write up on this project can be found on https://geeks-r-us.de/2019/07/01/solarkarftwerk-im-smarthome-einbinden/ and
https://geeks-r-us.de/2020/04/08/smi260-standalone-logger/

Thx to Cyrill Brunschwiler for the work on the [scambus repository](https://github.com/CBrunsch/scambus) and the wmbus parser which is used in this project to parse the messeages.

If you like this work consider of keeping me up at night and [buy me a coffee](https://ko-fi.com/geeks_r_us) 
