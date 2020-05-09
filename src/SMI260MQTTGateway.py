import os
import asyncio
import copy
import datetime
import serial_asyncio
import paho.mqtt.client as mqtt
from IM871 import IM871, EndpointID, RadioLinkMessageIdentifier
from SMI260Commands import SMI260Commands
from wmbus import WMBusFrame


from functools import partial

debug = False

smi_list = []
mqtt_common_topic = "SMI"
mqtt_client = mqtt.Client(client_id="SMI260MQTTGateway", clean_session=True, userdata=None, protocol=mqtt.MQTTv311)


def build_mqtt_topic(device, topic):
    return mqtt_common_topic + "/" + device + "/" + topic


def parse_mqtt_message(message):
    splits = message.topic.split('/')
    address = splits[1]
    command = splits[2]
    value = message.payload
    return address, command, value


def on_connect(client, userdata, flags, rc):

    if rc == 0:
        print("Successfully connected to MQTT")
        userdata.mqtt_connected = True

        for device in smi_list:
            userdata.device_list[device] = {"Energy": None, "Power": None, "MaxPower": None, "PowerOn": None}
            client.subscribe(build_mqtt_topic(device, "MaxPower/Set"))
            client.subscribe(build_mqtt_topic(device, "PowerOn/Set"))
    else:
        raise Exception("not connected")


def on_message(client, userdata, msg):
    print(msg.topic + " " + str(msg.payload))
    address, command, value = parse_mqtt_message(msg)
    int_val = int(value)
    changed = False
    device = userdata.device_list[address]
    if command == "PowerOn":
        if 0 <= int_val <= 1:
            device[command] = int_val
            changed = True

    elif command == "MaxPower":
        if 0 <= int_val <= 310:
            device[command] = int_val
            changed = True

    if changed and device["MaxPower"] is not None and device["PowerOn"] is not None:
        cmd = SMI260Commands()
        smimsg = cmd.change_state(address, device["MaxPower"], device["PowerOn"])
        userdata.transport.write(smimsg)


def update_topic(data, state):
    frame = WMBusFrame()
    frame.parse(data, {})
    byte_address = frame.address[0:3]

    address = SMI260Commands.address_from_byte(byte_address)
    print("Manufacturer: " + str(frame.manufacturer.hex()))
    print("Address: " + address)
    if debug:
        frame.log(2)
    if address in smi_list:
        device = state.device_list[address]
        if len(data) == 33:
            record = frame.records[0]
            val = record.get_energy_in_wh()
            mqtt_client.publish(build_mqtt_topic(address, "Energy"), str(val))
            device["Energy"] = val
            print("Energy: " + val)

            record = frame.records[1]
            val = record.get_power_in_w()
            maxval = device["MaxPower"]
            if maxval and val < (maxval + 5):  # sanitize values, empiric number due to swinging around max point + 5
                mqtt_client.publish(build_mqtt_topic(address, "Power"), str(val))
                device["Power"] = val
                print("MaxPower : " + val)

        elif len(data) == 93:
            record = frame.records[0]
            val = record.get_power_in_w()
            mqtt_client.publish(build_mqtt_topic(address, "MaxPower"), str(val))
            device["MaxPower"] = val
            print("MaxPower : " + val)

            record = frame.records[6]
            locval = copy.deepcopy(record.value)
            locval.reverse()
            # power on
            power_val = int(locval[9])  # maybe a side effect ?
            mqtt_client.publish(build_mqtt_topic(address, "PowerOn"), str(power_val))
            device["PowerOn"] = power_val
            print("PowerOn : " + str(val))

            # dc sec
            dc_val = int.from_bytes(locval[9:11], 'big') / 10
            mqtt_client.publish(build_mqtt_topic(address, "DCVoltage"), str(dc_val))
            print("DCVoltage : " + str(dc_val))

            # temp dc/ac
            temp_dcac_val = int.from_bytes(locval[24:26], 'big') / 10
            mqtt_client.publish(build_mqtt_topic(address, "TemperatureDCAC"), str(temp_dcac_val))
            print("TemperatureDCAC : " + str(temp_dcac_val))

            # temp dc/dc
            temp_dcdc_val = int.from_bytes(locval[36:38], 'big') / 10
            mqtt_client.publish(build_mqtt_topic(address, "TemperatureDCDC"), str(temp_dcdc_val))
            print("TemperatureDCDC : " + str(temp_dcdc_val))

            # freq
            freq_val = int.from_bytes(locval[49:51], 'big') / 100
            mqtt_client.publish(build_mqtt_topic(address, "Frequency"), str(freq_val))
            print("Frequency : " + str(freq_val))

class Communication(asyncio.Protocol):
    def __init__(self, state):
        super().__init__()
        self.transport = None
        self.smi = SMI260Commands()
        self.state = state

    async def query(self):
        while True:
            for device in smi_list:
                print("Query SMI " + str(device) + ":")
                message = self.smi.query_state(device)
                self.transport.write(message)
                mqtt_client.loop(0.1)
                await asyncio.sleep(0.15)
                message = self.smi.query_settings(device)
                self.transport.write(message)
                mqtt_client.loop(0.1)
                await asyncio.sleep(5)

            await asyncio.sleep(self.state.poll_every)

    def connection_made(self, transport):
        self.transport = transport
        self.state.transport = transport
        print('port opened', transport)

        # query stick
        self.transport.write(bytearray().fromhex('A5 81 0F 00 34 13'))
        asyncio.ensure_future(self.query())

    def data_received(self, data):
        print('['+ str(datetime.datetime.now()) + '] data received', repr(data))
        stick = IM871()
        stick.parse(data)
        if stick.endpoint_id == EndpointID.RADIOLINK_ID and (
                stick.message_id == RadioLinkMessageIdentifier.RADIOLINK_MSG_WMBUSMSG_IND or
                stick.message_id == RadioLinkMessageIdentifier.RADIOLINK_MSG_WMBUSMSG_REQ):
            try:
                update_topic(stick.get_wmbus_message(), self.state)

            except Exception as ex:
                print("Exception : ")
                print(ex)
                pass

        print("--------------------------------------------")

    def connection_lost(self, exc):
        print('port closed')
        self.transport.loop.stop()

    def pause_writing(self):
        print('pause writing')
        print(self.transport.get_write_buffer_size())

    def resume_writing(self):
        print(self.transport.get_write_buffer_size())
        print('resume writing')


async def main():
    global smi_list, debug

    serial_port = os.getenv('SUNSTICKPORT', '/dev/ttyUSB0')
    mqtt_server = os.getenv('MQTTSERVER', '127.0.0.1')
    mqtt_port = os.getenv('MQTTSERVERPORT', 1883)
    poll_every = int(os.getenv('POLL', 120))
    smi_list = os.getenv('SMI_LIST', '11491').split(',')
    debug = os.getenv('DEBUG', False)

    async_state = type('', (), {})()
    async_state.mqtt_connected = False
    async_state.device_list = {}
    async_state.transport = None
    async_state.poll_every = poll_every

    print('Connecting to MQTT Server')
    mqtt_client.user_data_set(async_state)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(mqtt_server, mqtt_port, 60)
    print('Connecting...')
    transport = None
    future = None
    while True:
        mqtt_client.loop(0.1)
        if async_state.mqtt_connected and transport is None:
            protocol = partial(Communication, async_state)
            loop = asyncio.get_event_loop()
            transport = serial_asyncio.create_serial_connection(loop, protocol, serial_port, baudrate=57600)

            future = asyncio.ensure_future(transport)
        
        if future is not None and future.done() :
            if future.exception() is not None  and future.exception() is not asyncio.exceptions.InvalidStateError:
                print(future.exception())
                loop.stop()
                quit(-1)
        
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
