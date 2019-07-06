import argparse
from IM871 import IM871
from SMI260Commands import SMI260Commands
import serial

parser = argparse.ArgumentParser(description='Sends commands to SMI260 inverter')
parser.add_argument('--port', help='port of the wireless mbus stick', required=True)
parser.add_argument('--address', help='address of the inverter', required=True)
parser.add_argument('--maxPower', type=int, help='maximum power output', required=True)
parser.add_argument('--power', help='switch inverter on or off', choices=['on', 'off'], required=True)

args = parser.parse_args()

try:
    ser = serial.Serial(args.port, 57600)
    if ser.is_open:
        ser.close()
    ser.open()
except serial.serialutil.SerialException as ex:
    print(ex)
    exit(1)

cmd = SMI260Commands()
smimsg = cmd.change_state(args.address, args.maxPower, 1 if args.power == 'on' else 0)
ser.write(smimsg)
ser.flush()
ser.close()









