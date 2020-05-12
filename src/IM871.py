# -*- coding: utf-8 -*-

from flags import Flags
from array import array
from enum import Enum
import os

SOF = 0xA5


# Endpoint Identifier
class EndpointID(Enum):
    DEVMGMT_ID = 0x01
    RADIOLINK_ID = 0x02
    RADIOLINKTEST_ID = 0x03
    HWTEST_ID = 0x04


class DeviceMessageIdentifier(Enum):
    DEVMGMT_MSG_PING_REQ = 0x01
    DEVMGMT_MSG_PING_RSP = 0x02
    DEVMGMT_MSG_SET_CONFIG_REQ = 0x03
    DEVMGMT_MSG_SET_CONFIG_RSP = 0x04
    DEVMGMT_MSG_GET_CONFIG_REQ = 0x05
    DEVMGMT_MSG_GET_CONFIG_RSP = 0x06
    DEVMGMT_MSG_RESET_REQ = 0x07
    DEVMGMT_MSG_RESET_RSP = 0x08
    DEVMGMT_MSG_FACTORY_RESET_REQ = 0x09
    DEVMGMT_MSG_FACTORY_RESET_RSP = 0x0A
    DEVMGMT_MSG_GET_OPMODE_REQ = 0x0B
    DEVMGMT_MSG_GET_OPMODE_RSP = 0x0C
    DEVMGMT_MSG_SET_OPMODE_REQ = 0x0D
    DEVMGMT_MSG_SET_OPMODE_RSP = 0x0E
    DEVMGMT_MSG_GET_DEVICEINFO_REQ = 0x0F
    DEVMGMT_MSG_GET_DEVICEINFO_RSP = 0x10
    DEVMGMT_MSG_GET_SYSSTATUS_REQ = 0x11
    DEVMGMT_MSG_GET_SYSSTATUS_RSP = 0x12
    DEVMGMT_MSG_GET_FWINFO_REQ = 0x13
    DEVMGMT_MSG_GET_FWINFO_RSP = 0x14
    DEVMGMT_MSG_GET_RTC_REQ = 0x19
    DEVMGMT_MSG_GET_RTC_RSP = 0x1A
    DEVMGMT_MSG_SET_RTC_REQ = 0x1B
    DEVMGMT_MSG_SET_RTC_RSP = 0x1C
    DEVMGMT_MSG_ENTER_LPM_REQ = 0x1D
    DEVMGMT_MSG_ENTER_LPM_RSP = 0x1E
    DEVMGMT_MSG_SET_AES_ENCKEY_REQ = 0x21
    DEVMGMT_MSG_SET_AES_ENCKEY_RSP = 0x22
    DEVMGMT_MSG_ENABLE_AES_ENCKEY_REQ = 0x23
    DEVMGMT_MSG_ENABLE_AES_ENCKEY_RSP = 0x24
    DEVMGMT_MSG_SET_AES_DECKEY_REQ = 0x25
    DEVMGMT_MSG_SET_AES_DECKEY_RSP = 0x26
    DEVMGMT_MSG_AES_DEC_ERROR_IND = 0x27


class RadioLinkMessageIdentifier(Enum):
    RADIOLINK_MSG_WMBUSMSG_REQ = 0x01
    RADIOLINK_MSG_WMBUSMSG_RSP = 0x02
    RADIOLINK_MSG_WMBUSMSG_IND = 0x03
    RADIOLINK_MSG_DATA_REQ = 0x04
    RADIOLINK_MSG_DATA_RSP = 0x05


class ControlFieldFlags(Flags):
    Reserved = 1
    TimeStampField = 2
    RSSIField = 4
    CRC16Field = 8


class Packet:
    def __init__(self):
        self.control_field = ControlFieldFlags.no_flags
        self.endpoint_id = EndpointID.DEVMGMT_ID
        self.message_id = None
        self.payload_length = 0
        self.payload = bytearray()
        self.timestamp = 0
        self.rssi = 0

class IM871:
    def __init__(self):
        self.debug = os.getenv('DEBUG', False)

    def build(self, packet):
        data = bytearray()
        data.append(SOF)
        data.append(int(packet.control_field) << 4 | packet.endpoint_id.value & 0x0F)
        data.append(packet.message_id.value)
        data.append(len(packet.payload) & 0xff)
        data.extend(packet.payload)

        if bool(packet.control_field & ControlFieldFlags.CRC16Field):
            crc = self.crc16(data[1:])
            data.append(crc & 0xff)
            data.append(crc >> 8 & 0xff)

        # TODO: TIMESTAMP & RSSI

        return data

    def parse(self, data):
        packets = []
        offset = 0

        while offset < len(data):
            packet = Packet()

            if data[offset] != SOF:
                print("WARINING! no Start Of Frame found!")
                continue

            packet.control_field = ControlFieldFlags(data[ offset + 1] >> 4)
            packet.endpoint_id = EndpointID(data[offset + 1] & 0x0F)
            if self.debug:
                print("Control fields: " + str(packet.control_field))
                print("Endpoint id: " + str(packet.endpoint_id))

            if packet.endpoint_id == EndpointID.DEVMGMT_ID:
                packet.message_id = DeviceMessageIdentifier(data[offset + 2])
            elif packet.endpoint_id == EndpointID.RADIOLINK_ID:
                packet.message_id = RadioLinkMessageIdentifier(data[offset + 2])

            if self.debug:
                print("Message id: " + str(packet.message_id))

            packet.payload_length = data[offset + 3]
            if self.debug:
                print("Payload length: " + str(packet.payload_length))

            if packet.payload_length != 0:
                packet.payload = bytearray(data[offset + 4: offset + 4 + packet.payload_length])
                if self.debug:
                    print("Payload: " + self.to_hex(packet.payload))

            length = packet.payload_length
        
            if bool(ControlFieldFlags.TimeStampField & packet.control_field):
                length += 4
                packet.timestamp = int.from_bytes(data[offset + length: offset + 4 + length], byteorder='little')

            if bool(ControlFieldFlags.RSSIField & packet.control_field):
                length += 1
                packet.rssi = data[offset + 4 + length]

            if bool(ControlFieldFlags.CRC16Field & packet.control_field):
                packetdata = data[offset + 1:offset + 4+length]
                crc = self.crc16(packetdata)
                crcb = data[offset + 4+length:offset + 4+length+2]
                crci = int.from_bytes(crcb, byteorder='little')
                if crc != crci:
                    print("WARNING! CRC does not match!")
                    continue
                length += 2
            packets.append(packet)
            offset += length + 4

        return packets

    def get_wmbus_message(self, packet):
        arr = [packet.payload_length]
        arr.extend(packet.payload)
        return bytearray(arr)

    def crc16(self, packetdata):
        POLY = 0x8408  # 0x8408 is deduced from the polynomial X**16 + X**12 + X**5 + X**0

        # process each byte
        crc = 0xFFFF  # init FCS to all ones
        for byte in packetdata:
            # process each bit of the current byte
            for x in range(8):
                if (byte & 1) ^ (crc & 1):
                    crc = (crc >> 1) ^ POLY
                else:
                    crc >>= 1
                byte >>= 1
        crc ^= 0xFFFF  # finally invert crc

        return crc

    def to_hex(self, v, split=' '):
        """ Return value in hex form as a string (for pretty printing purposes).
        The function provides a conversion of integers or byte arrays ('B') into
        their hexadecimal form separated by the splitter string
        """
        myformat = "%0.2X"
        if type(v) == array or type(v) == bytearray:
            return split.join(myformat % x for x in v)
        elif type(v) == str:
            temp = bytearray(v)
            return split.join(myformat % x for x in temp)
        elif type(v) == int:
            return myformat % v
        else:
            return "tohex(): unsupported type"
