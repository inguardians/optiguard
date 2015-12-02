# c12_18_serial.py - python module for handling serial communications
# as they relate to C12.18 communications.
# 
# Copyright (c) 2011, InGuardians, Inc. <consulting@inguardians.com>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Point Of Contact:    Don C. Weber <don@inguardians.com>

# TODO: c12_18_serial.py: This module needs to be cleaned up

import os, sys, time
import serial
import struct
import crcmod
import warnings

class SERCONN:
    def __init__(self, debug = False):
        # Set up defaults
        self.debug     = debug
        self.comm_port = None
        self.baud      = 9600
        self.timeout   = 1
        self.invert    = False
        # New Settings
        self.parity    = serial.PARITY_NONE
        self.bytesize  = serial.EIGHTBITS
        self.xonxoff   = False
        self.rtscts    = False
        self.stopbits  = serial.STOPBITS_ONE
        self.dsrdtr    = False
        
    def serInit(self, port = None, baud=9600, timeout=5, invert=0):
        # FIXME: c12_18_serial.py: serInit: This should conduct a search for the optical probe. Should also handle OSX
        if port == None:
            if os.name == 'posix':
                self.comm_port = '/dev/ttyUSB0'
            elif os.name == 'nt':
                self.comm_port = 'COM4'
            elif os.name == 'mac':
                print "Apple Not Supported. Boot to Linux or Windows."
                sys.exit()
        else:
            self.comm_port = port

        # Some optical probes handle sending data differently
        # FIXME: c12_18_serial.py: serInit: do we need to set everything a second time for invert?
        if invert:
            self.invert = True

        if port == None:
            print "Could not find comm port"
            sys.exit()
        if self.debug: print "comm_port:", self.comm_port
                
        # Set up serial
        self.timeout = timeout
        self.baud = baud
            
        #self.serialport = serial.Serial(self.comm_port, self.baud, timeout=self.timeout)
        self.serialport = serial.Serial(self.comm_port, self.baud, timeout=self.timeout, parity=self.parity, bytesize=self.bytesize, xonxoff=self.xonxoff, rtscts=self.rtscts, stopbits=self.stopbits, dsrdtr=self.dsrdtr)

        if self.invert:
            self.serialport.setRTS(0)

        # Unset DTR so that send LED start in the off position
        self.serialport.setDTR(0)

#########################################
# Read Serial
#########################################
        
    def read_byte(self):
        '''Returns a single byte read in from serial'''
        return self.serialport.read(1)
    
    def read_sbytes(self, num=1):
        '''Returns a list of bytes read one at a time in from serial'''
        tmp_bytes = []
        for cnt in range(num):
            tmp_bytes.append(self.read_byte())
        return ''.join(tmp_bytes)
    
    def read_fbytes(self, num=1):
        '''Returns a selected number of bytes read in from serial'''
        return self.serialport.read(num)
    
    def read_line(self):
        '''Returns a line of bytes read in from serial'''
        return self.serialport.readline()

    def close(self):
        self.serialport.close()

#########################################

#########################################
# Write Serial
#########################################

    def write_byte(self, data=None, flush = True):
        '''Write a single byte to serial'''
        if data == None or len(data) > 1:
            return 0;
        self.serialport.write(data)
        # Might need to flush
        if flush:
            self.serialport.flush()
        return 1;
    
    def write_bytes(self, data=None, flush = True):
        '''Write a list of bytes to serial'''
        if data == None:
            return 0;
        # Should be okay to write all at the some time
        self.serialport.write(data)
        # Might need to flush
        if flush:
            self.serialport.flush()
        return 1;

#########################################
        
if __name__ == "__main__":

    try:
        data = sys.argv[1]
    except:
        print "c12_18_serial.py: No data provided"
        sys.exit()

    ser_conn = SERCONN(debug = True)
    ser_conn.serInit()
    if not ser_conn.write_bytes(data):
        print "Serial Write Failed"
        sys.exit()
    ser_conn.read_fbytes(20)
    ser_conn.close()
