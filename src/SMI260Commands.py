from IM871 import IM871, ControlFieldFlags, EndpointID, RadioLinkMessageIdentifier


class SMI260Commands:
    def __init__(self):
        self.stick = IM871()

    def change_state(self, address, max_power_output, on):
        self.stick.control_field = ControlFieldFlags.CRC16Field
        self.stick.endpoint_id = EndpointID.RADIOLINK_ID
        self.stick.message_id = RadioLinkMessageIdentifier.RADIOLINK_MSG_WMBUSMSG_REQ

        bytepower = bytearray(max_power_output.to_bytes(2, 'little'))
        byteon = bytearray(on.to_bytes(1, 'little'))
        message = self.set_address(address, bytearray.fromhex(
            '44 B4 B0 00 00 00 00 01 02 51 0C 79 00 00 00 00 12 2B 8C 00 02 7C 07 69 68 70 5F 73 6F 63 E8 03 01 FD 66 01'))

        message[18] = bytepower[0]
        message[19] = bytepower[1]
        message[35] = byteon[0]

        self.stick.payload = message
        return self.stick.build()

    def query_state(self, address):
        self.stick.control_field = ControlFieldFlags.CRC16Field
        self.stick.endpoint_id = EndpointID.RADIOLINK_ID
        self.stick.message_id = RadioLinkMessageIdentifier.RADIOLINK_MSG_WMBUSMSG_REQ
        self.stick.payload = self.set_address(address,
                                              bytearray.fromhex('5B B4 B0 00 00 00 00 01 02 51 0C 79 00 00 00 00'))
        return self.stick.build()

    def query_settings(self, address):
        self.stick.control_field = ControlFieldFlags.CRC16Field
        self.stick.endpoint_id = EndpointID.RADIOLINK_ID
        self.stick.message_id = RadioLinkMessageIdentifier.RADIOLINK_MSG_WMBUSMSG_REQ
        self.stick.payload = self.set_address(address,
                                              bytearray.fromhex('5B B4 B0 00 00 00 00 01 02 51 0C 79 00 00 00 00 00 FF A7'))
        return self.stick.build()

    def byte_from_address(self, address):
        padded = '{:06d}'.format(int(address))
        rotated = padded[4:6] + " " + padded[2:4] + " " + padded[0:2]
        return bytearray.fromhex(rotated)

    def set_address(self, address, message):
        byte_address = self.byte_from_address(address)
        message[3] = byte_address[0]
        message[4] = byte_address[1]
        message[5] = byte_address[2]
        return message
