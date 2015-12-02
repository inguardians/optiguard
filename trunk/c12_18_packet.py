# c12_18_packet.py - python module for sending and receiving C12.18
# data.
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

# TODO: c12_18_packet.py: This module needs to be cleaned up

import os, sys, time
import struct
import crcmod
import byte_tools as bt

######################################
# VARIABLES - These values will not change
######################################
# Bits of Bytes
bit0 = 1<<1
bit1 = 1<<2
bit2 = 1<<3
bit3 = 1<<4
bit4 = 1<<5
bit5 = 1<<6
bit6 = 1<<7
bit7 = 1<<8

MAXDATA = 8183     # Maximum number of data bytes for a packet
HEADLEN = 6        # Size of packet header
CRCLEN  = 2        # Size of packet footer, crc value

STD_TABLE_BASE = 0
MFG_TABLE_BASE = 2040
STD_PROC_BASE  = 0
MFG_PROC_BASE  = 2048
STD_PROC_SIZE  = 33
MFG_PROC_SIZE  = 150

#PROC_SEQ = 0       # Procedure sequence number - global as it gets incremented

# Delay values
start_delay = 100
#start_delay = 1
cmd_pause   = .15
no_pause    = 0
sec_pause   = 1
logon_pause = 5

# Outcomes
SUCCESS = True
FAIL    = False
######################################

def delay(self,delay = 0):
    '''Delay function'''
    time.sleep(delay)

# Function to reverse bit order to 
# convert from LSB to MSB or visa versa
def rev(byte):
    numbits = 8
    return sum(1<<(numbits-1-i) for i in range(numbits) if byte>>i&1)

###############################
# Known C12.18-2006 Requests and Responses
# <packet> ::= <stp><identity><ctrl><seq-nbr><length><data><crc>'''
# All messages can have two forms.  Single packet messages will have a ctrl
# byte of \x00 or \x20. This value is toggled if an ACK is not received and the packet
# needs to be resent.  Messages can start with either value.
###############################
STP        = '\xee'
ACK        = '\x06'  #Required to send to ACK that a request or response was received
NAK        = '\x15'
IDENT      = '\x00'
SPACE      = '\x20'
ack_bytes  = (ACK,NAK)
single_ctrl= ('\x00','\x20')
resp_bytes = ('ok','err','sns','isc','onp','iar','bsy','dnr','dlk','rno','isss')
resp_names = ('Okay','Error','Service Not Supported','Insufficient Security Clearance','Operation Not Possible','Inappropriate Action Request','Device Busy','Data Not Ready','Data Locked','Renegotiate Request','Invalid Service Sequence State')

# 20-byte Passwords for testing
space_passwd = '\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20'
zero_passwd  = '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
ff_passwd    = '\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
ones_passwd    = '\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
twos_passwd    = '\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
threes_passwd    = '\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
test_passwds = [space_passwd,zero_passwd,ff_passwd,ones_passwd,twos_passwd,threes_passwd]
###############################

class C1218_packet:
    def __init__(self, p_stp = STP, p_ident = IDENT, p_ctrl = '\x00' , p_seqnbr = '\x00', p_len = 1, p_data = '', p_crc = ''):
        '''
        C12.18 packet class.  Used to build C12.18 request and response packets.  Init function sets some default values.
        <packet> ::= <stp><identity><ctrl><seq-nbr><length><data><crc>
        '''
        # Packet Data
        self.p_ack      = False         # Ack packet, has it been sent or received
        self.p_stp      = p_stp         # Start of packet character '\xee'
        self.p_ident    = p_ident       # Device identification, default '\x00'
        self.p_ctrl     = p_ctrl        # Control Field, multi-packet info
        self.p_seqnbr   = p_seqnbr      # Sequence number, default '\x00', p_ctrl will change too
        self.p_len      = struct.pack('>H',p_len) # Length default '\x0001'
        self.p_data     = p_data        # Data, variable in length
        self.p_crc      = p_crc         # crcmod x-25 value for packet

        # Packet Communication Control
        self.seq            = 0 # Sequence number to track control byte.
        self.proc_seq       = 0
        self.nego_on        = False

        # Control Debugging information
        self.debug          = False

#########################################
# Write and setting functions
#########################################

    def get_crc(self):
        '''Return current value of p_crc'''
        return self.p_crc

    def size_limit(self):
        '''Check data length to determine if too big to send.  Max == 8183 bytes'''
        if len(self.data) > MAXDATA:
            return 0
        return 1

    def crc(self,data=None):
        '''Compute C12.18 CRC value which uses the x-25 settings in crcmod.
            Stores the results in Little Endian order. Returns success (1) or failure (0)'''
        if self.p_data == '' and data == None:
            return 0
        # This has to be initialized everytime.  For some reason
        # it keeps track of old values and will use that as the
        # starting value.  You could start with crcval.new(arg='\x00')
        # but I don't trust it.
        crcval = crcmod.predefined.Crc('x-25')
        if data == None:
            data = [self.p_stp, self.p_ident, self.p_ctrl, self.p_seqnbr, self.p_len, self.p_data, self.p_crc]
        crcval.update(''.join(data))
        self.p_crc = struct.pack('H',crcval.crcValue)
        return 1

    def test_crc(self,data=None,crc=None):
        '''Compute C12.18 CRC value which uses the x-25 settings in crcmod.
            Stores the results in Little Endian order. Returns success (1) or failure (0)'''
        if data == None or crc == None:
            return 0
        # This has to be initialized everytime.  For some reason
        # it keeps track of old values and will use that as the
        # starting value.  You could start with crcval.new(arg='\x00')
        # but I don't trust it.
        crcval = crcmod.predefined.Crc('x-25')
        crcval.update(data)
        if crc == struct.pack('H',crcval.crcValue):
            return 1
        return 0

    def full_packet(self, data=None):
        '''Build full packet. Returns failure (0) or full packet'''
        # Test for data and that it is the right size
        if self.p_data == '' and self.size_limit() and data == None:
            print "full_packet: No data or size limite"
            return 0
        if data == None:
            self.p_len = struct.pack('>H',len(self.p_data))
            tmp_data = [self.p_stp, self.p_ident, self.p_ctrl, self.p_seqnbr, self.p_len, self.p_data]
        else:
            tmp_data = data
        # Get CRC or fail
        if not self.crc(data = tmp_data):
            print "full_packet: No CRC"
            return 0
        # Append CRC and return packet
        if data == None:
            return ''.join([self.p_stp, self.p_ident, self.p_ctrl, self.p_seqnbr, self.p_len, self.p_data, self.p_crc])
        else:
            return data + self.p_crc

    def reset_packet(self, ctrl = 0):
        '''Reset the C12.18 packets contents to their default values.'''
        self.p_ack      = False
        self.p_stp      = STP
        self.p_ident    = IDENT
        if ctrl:
            self.p_ctrl = '\x20'
        else:
            self.p_ctrl = '\x00'
        self.p_seqnbr   = '\x00'
        self.p_len      = 1
        self.p_data     = ''
        self.p_crc      = ''
        self.pre_packet = [self.p_stp, self.p_ident, self.p_ctrl, self.p_seqnbr, self.p_len, self.p_data]

    def print_packet(self, data = None):
        '''Returns the results of full_packet() in human-readable and printable format'''
        if data == None:
            data = self.full_packet()
        else:
            # Get CRC or fail
            if data != ACK and self.get_crc == '':
                if not self.crc(data = data):
                    print "print_packet: No CRC"
                    return 0
                data += self.p_crc
        if not data:
            print "print_packet: Failed to build packet"
            return 0
        tstring = []
        for e in data:
            tstring.append('\\\\x'.decode('string_escape') + hex(ord(e))[2:])
        for e in range(len(tstring)):
            if len(tstring[e]) == 3:
                tmp = list(tstring[e])
                tmp.insert(-1,'0')
                tstring[e] = ''.join(tmp)
        return ''.join(tstring)

    def table_crc(self,data=None):
        '''Return data CRC which is the 2's compliment of the sum of all bytes (ignore overflow).'''
        if data == None:
            return data
        tmp = 0
        for e in data:
            tmp += ord(e)

        # Subtract one and Get rid of overflow
        tmp = (tmp - 1) & 0xff
        # Flip bits and get absolute value of result. Do this to avoid signed number which breaks packing.
        tmp = abs((tmp ^ 0xff))
        return struct.pack('B',tmp)

    def full_read(self, table=None):
        '''Return the data for a full table read. Requires a table number.'''
        # Read Table
        # <full-read> ::= 30H <tableid>
        # <tableid> ::= <word16>

        if table == None:
            return 0
        self.p_data = '\x30' + struct.pack('>H',table)
        return 1

    def full_write(self, table=None, data=None):
        '''Return the data for a full table write. Requires a table number and some data.'''
        # Write Table
        # <full-write> ::= 40H <tableid><table-data>
        # <tableid>       ::= <word16>
        # <table-data>    ::= <count><data><cksum>
        # <count>         ::= <word16>
        # <data>          ::= <byte>*
        # <cksum>         ::= <byte>

        if table == None or data == None:
            return 0
        # data will already be packed
        data_crc = self.table_crc(data)
        data_len = struct.pack('>H',len(data))
        w_data = data_len + data + data_crc
        self.p_data = '\x40' + struct.pack('>H',table) + w_data
        return 1

    def partial_write(self, table=None, offset=None, data=None):
        '''Return the data for a partial table write. Requires a table number, and offset, and some data.'''
        # Write Table
        # <pwrite-offset> ::= 4FH <tableid><offset><table-data>
        # <tableid>       ::= <word16>
        # <offset>        ::= <word24>
        # <table-data>    ::= <count><data><cksum>
        # <count>         ::= <word16>
        # <data>          ::= <byte>*
        # <cksum>         ::= <byte>
        if table == None or offset == None or data == None:
            return 0
        # data will already be packed
        data_crc = self.table_crc(data)
        data_len = struct.pack('>H',len(data))
        d_offset = struct.pack('>L',len(offset))[1:]
        w_data = data_len + data + data_crc
        self.p_data = '\x4f' + struct.pack('>H',table) + w_data
        return 1

    def logon_num(self, num=None,data='\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39'):
        '''Return the data for a user logon id'''
        if num == None:
            return 0
        self.p_data = '\x50' + struct.pack('>H',num) + data
        return 1

    def ident(self):
        '''Return the data for a ident'''
        self.p_data = '\x20'
        return 1

    def nego(self):
        '''Return the data for a ident'''
        # TODO: c12_18_optical_client.py: nego: Baud rate and other data should not be set automatically
        data = '\x01\x00\x01\x06'
        self.p_data = '\x61' + data
        return 1

    def passwd(self, passwd=None):
        '''Return the data for a security packet. Incoming passwd should be a properly formatted 20-byte string. Padded by \x20 if necessary.\n
    \'\\xXX\\xXX\\xXX\\xXX\\xXX\\xXX\\xXX\\xXX\\xXX\\xXX\\x20\\x20\\x20\\x20\\x20\\x20\\x20\\x20\\x20\\x20\' '''
        if passwd == None:
            return 0
        self.p_data = '\x51' + passwd
        return 1

    def proc(self, proc=None, data = ''):
        '''Return the data for a procedure request. Requires a procedure number. Calls self.full_write'''
        if proc == None:
            return 0

        #global PROC_SEQ

        table = 7 # To run procedures we write to Table 07
        proc_data = struct.pack('<H',proc) + struct.pack('B',self.proc_seq) + data
        self.proc_seq += 1
        self.full_write(table=table,data=proc_data)
        return 1

    def logoff(self):
        '''Return the data for a logoff'''
        self.p_data = '\x52'
        return 1

    def term(self):
        '''Return the data for a terminate session'''
        self.p_data = '\x21'
        return 1

    ##########################################################
    # C12.18 Interaction Functions
    ##########################################################
        
    def toggle_debug(self):
        '''Toggle the state of debug. If off then turn on. If on then turn off.'''
        if self.debug:
            self.debug = False
        else:
            self.debug = True
        return
        
    def toggle_nego(self):
        '''Toggle the state of whether or not to send negotiation service. If off then turn on. If on then turn off.'''
        if self.nego_on:
            self.nego_on = False
        else:
            self.nego_on = True
        return

    def state_nego(self):
        '''Return the state of nego_on. Zero is off. One is on.'''
        return self.nego_on

    def set_debug(self, data):
        '''Set debug to incoming.'''
        self.debug = data

    def set_nego(self,data):
        '''Set nego to incoming.'''
        self.nego_on = data

    def send_data(self,ser_conn, data = None):
        '''Send C12.18 packet'''
        if data == None:
            if self.debug: print "send_data: No data"
            #sys.exit()
            return FAIL

        if not ser_conn.write_bytes(data = data):
            print "send_data: Serial Write Failed"
            #sys.exit()
            return FAIL

    def send_ack(self,ser_conn,pause=0):
        '''Send C12.18 ack packet'''
        # Pause for just a bit in case blind ack
        if pause:
            delay(pause)
        
        if not ser_conn.write_bytes(data = ACK):
            print "send_ack: Serial Write Failed"
            #sys.exit()
            return FAIL

        if self.debug: print "    Sent ACK"

    def send_nack(self,ser_conn,pause=0):
        '''Send C12.18 ack packet'''
        # Pause for just a bit in case blind ack
        if pause:
            delay(pause)
        
        if not ser_conn.write_bytes(data = NAK):
            print "send_ack: Serial Write Failed"
            #sys.exit()
            return FAIL
            
        if self.debug: print "    Sent NACK"

    def read_response(self,ser_conn):
        '''Get serial input and return list. [ok/nok,data]'''
        # <packet> ::= <stp><identity><ctrl><seq-nbr><length><data><crc>
        #               B    B         B     B        W      Var   W
        # Read ack and test for '\x06' else return error
        # Read 6 bytes, test first byte for <stp>, test ctrl for multi-packet, and then get length
        # Read in len + 2 to get all data plus packet <crc>
        # return data


        read_ok  = True     # Results are bad
        read_nok = False    # Results are good
        multi    = 1        # Number of incoming packets
        header   = 6        # Default size of packet header
        plength  = 0        # Incoming size of packet's data section
        pdata    = ''       # Incoming packet's data
        mdata    = ''       # Combined incoming data
        inbyte   = ''       # Initial storage
        fdata    = ''
        fail     = 2        # Fail after 5 bad attempts


        # Read until ACK
        inbyte = ser_conn.read_byte()
        while inbyte not in ack_bytes:
            if self.debug and (inbyte not in ack_bytes): print "read_response: did not receive ack byte:",bt.print_data(inbyte)
            if not fail:
                #return [read_nok,'Nothing returned'] 
                #return [read_nok,bt.print_data(inbyte)] 
                self.send_nack(ser_conn)
                fail = 2
            fail -= 1
            inbyte = ser_conn.read_byte()
        if inbyte == NAK:
            return [read_nok,'No ACK'] 

        # Get multiple packets by starting with at least one packet
        while multi:
            # Grab header
            inbyte = ser_conn.read_sbytes(header)
            # Test STP
            if inbyte[0] != STP:
                return [read_nok,'Bad STP Value'] 
            # Test for multiple packets by looking at seq_num
            multi = struct.unpack('B',inbyte[3])[0]
            # Get data length
            plength = struct.unpack('>H',inbyte[-2:])[0]
            # Get data
            pdata = ser_conn.read_sbytes(plength)
            # Get Packet CRC
            pcrc  = ser_conn.read_sbytes(2)
            fdata = inbyte + pdata
            if self.debug: print "read_response: received data: ", bt.print_data(fdata + pcrc)
            if not self.test_crc(data=fdata,crc=pcrc):
                # TODO: c12_18_optical_client.py: make read_response read again for 3 (?) tries before error
                return [read_nok,'Packet CRC failed'] 
            # Pull multiple packet data together
            mdata += pdata
            # If multiple packets send ACK to get next packet
            if multi:
                self.send_ack(ser_conn,cmd_pause)

        # Send ACK and return read is ok and any data received
        self.send_ack(ser_conn,cmd_pause)
        return [read_ok,mdata]

    def parse_rtn_data(self,data):
        '''Parse the data returned from a table read'''
        if not data:
            return []
        length = struct.unpack('>H',data[1:3])[0]
        # Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>
        return [data[:1], length, data[3:(3 + length)], data[-1:]]

    def send_logoff(self,ser_conn):
        '''Sends logoff message'''

        # Create and reset packet
        #packet = c12packet.C1218_packet()

        #Send ident
        resp = [False,'']
        #packet.reset_packet(ctrl = self.seq)
        self.reset_packet(ctrl = self.seq)
        if not self.logoff():
            print "send_logoff: Failed to build packet"
        data = self.full_packet()
        while resp[0] == False:
            if self.debug: print "Sending: %s: %s" % ('logoff',self.print_packet(data))
            if not self.send_data(ser_conn,data):
                return FAIL

            # Read Response
            resp = self.read_response(ser_conn)
            if resp[0] == False:
                print "send_logoff: ident response failed - ",resp[1]

        # This should return OK
        if self.debug: print "Incoming data: ",bt.print_data(resp[1])
        result = struct.unpack('B',resp[1][0])[0]
        
        # Cycle Control Byte
        self.seq ^= 1

        if result:
            print "send_logoff: Failed logoff - ", resp_names[result]
            return FAIL

        # Return the sequence where we left off
        return SUCCESS

    def send_terminate(self,ser_conn):
        '''Sends terminate message'''

        # Create and reset packet
        #global SEQ
        #packet = c12packet.C1218_packet()

        #Send ident
        resp = [False,'']
        self.reset_packet(ctrl = self.seq)
        if not self.term():
            print "send_terminate: Failed to build packet"
        data = self.full_packet()
        while resp[0] == False:
            if self.debug: print "Sending: %s: %s" % ('terminate',self.print_packet(data))
            self.send_data(ser_conn,data)

            # Read Response
            resp = self.read_response(ser_conn)
            if resp[0] == False:
                print "send_terminate: ident response failed - ",resp[1]

        # This should return OK
        if self.debug: print "Incoming data: ",bt.print_data(resp[1])
        result = struct.unpack('B',resp[1][0])[0]
        
        # Cycle Control Byte
        #SEQ ^= 1
        self.seq ^= 1

        if result:
            print "send_terminate: Failed termination of connection - ", resp_names[result]
            return FAIL

        # Return the sequence where we left off
        return SUCCESS

    def login_setup(self,ser_conn):
        '''Initiates logon sequence. Handles the ident and negotiate messages'''
        if self.debug: print "Using login_setup which combines ident_setup and nego_setup"
        if not self.ident_setup(ser_conn):
            return FAIL
        if not self.nego_setup(ser_conn):
            return FAIL
        return SUCCESS

    def ident_setup(self,ser_conn):
        '''Initiates ident sequence. Handles the ident message'''

        # Create and reset packet
        #global SEQ
        #packet = c12packet.C1218_packet()

        fail = 5

        #Send ident
        resp = [False,'']
        self.reset_packet(ctrl = self.seq)
        if not self.ident():
            print "ident_setup: Failed to build ident"
        data = self.full_packet()
        while resp[0] == False:
            if self.debug: print "Sending: %s: %s" % ('ident',self.print_packet(data))
            self.send_data(ser_conn,data)

            # Read Response
            resp = self.read_response(ser_conn)
            if resp[0] == False:
                print "ident_setup: ident response failed - ",resp[1]
                return FAIL

        # This should return OK
        if self.debug: print "Incoming data: ",bt.print_data(resp[1])
        result = struct.unpack('B',resp[1][0])[0]
        
        # Cycle Control Byte
        #SEQ ^= 1
        self.seq ^= 1

        if result:
            print "ident_setup: Failed ident - ", resp_names[result]
            return FAIL

        # Return the sequence where we left off
        return SUCCESS
        
    def nego_setup(self,ser_conn):
        '''Initiates nego sequence. Handles the negotiate message'''

        # Create and reset packet
        #global SEQ
        #packet = c12packet.C1218_packet()

        # Test if turned off and just return success
        if not self.nego_on:
            return SUCCESS

        #Send ident
        resp = [False,'']
        self.reset_packet(ctrl = self.seq)

        #Send nego
        resp = [False,'']
        self.reset_packet(ctrl = self.seq)
        if not self.nego():
            print "login_setup: Failed to build nego"
        data = self.full_packet()
        while resp[0] == False:
            if self.debug: print "Sending: %s: %s" % ('nego',self.print_packet(data))
            self.send_data(ser_conn,data)

            # Read Response
            resp = self.read_response(ser_conn)
            if resp[0] == False:
                print "login_setup: nego response failed - ",resp[1]

        # This should return OK plus negotiation data
        if self.debug: print "Incoming data: ",bt.print_data(resp[1])
        result = struct.unpack('B',resp[1][0])[0]
        
        # Cycle Control Byte
        #SEQ ^= 1
        self.seq ^= 1

        if result:
            print "login_setup: Failed nego - ", resp_names[result]
            return FAIL

        # Return the sequence where we left off
        return SUCCESS
        
    def login_passwd(self,ser_conn, passwd):
        '''Provides the ability to logon using a specific user and specific passwd. Sends logon and security messages.'''
        # Create and reset packet
        #global SEQ
        #packet = c12packet.C1218_packet()
        resp = [False,'']
        
        #Send security
        resp = [False,'']
        self.reset_packet(ctrl = self.seq)
        if not self.passwd(passwd=passwd):
            print "login_passwd: Failed to build security"
        data = self.full_packet()
        while resp[0] == False:
            if self.debug: print "Sending: %s: %s" % ('security',self.print_packet(data))
            self.send_data(ser_conn,data)

            # Read Response
            resp = self.read_response(ser_conn)
            if resp[0] == False:
                print "login_passwd: security response failed - ",resp[1]
                return FAIL

        # This should return OK
        if self.debug: print "Incoming data: ",bt.print_data(resp[1])
        result = struct.unpack('B',resp[1][0])[0]
        
        # Cycle Control Byte
        #SEQ ^= 1
        self.seq ^= 1

        if result:
            print "login_passwd: Failed security - ", resp_names[result]
            return FAIL

        # Return the sequence where we left off
        return SUCCESS

    def login_user(self,ser_conn, user,user_str=''):
        '''Provides the ability to logon using a specific user and specific passwd. Sends logon and security messages.'''
        # Create and reset packet
        #global SEQ
        #packet = c12packet.C1218_packet()
        resp = [False,'']

        #Send logon
        self.reset_packet(ctrl = self.seq)
        if user_str:
            if not self.logon_num(num=user,data=user_str):
                print "login_user: Failed to build logon"
        else:
            if not self.logon_num(num=user):
                print "login_user: Failed to build logon"
        data = self.full_packet()

        while resp[0] == False:
            if self.debug: print "Sending: %s: %s" % ('logon',self.print_packet(data))
            self.send_data(ser_conn,data)

            # Read Response
            resp = self.read_response(ser_conn)
            if resp[0] == False:
                print "login_user: logon response failed - ",resp[1]

        # This should return OK
        if self.debug: print "Incoming data: ",bt.print_data(resp[1])
        result = struct.unpack('B',resp[1][0])[0]
        
        # Cycle Control Byte
        #SEQ ^= 1
        self.seq ^= 1
        
        if result:
            print "login_user: Failed logon - ", resp_names[result]
            return FAIL

        # Return the sequence where we left off
        return SUCCESS

    def login_seq_passwd(self,ser_conn, user, passwd):
        '''Provides the ability to logon using a specific user and specific passwd. Sends logon and security messages.'''
        # Create and reset packet
        #global SEQ
        #packet = c12packet.C1218_packet()
        resp = [False,'']

        #Send logon
        self.reset_packet(ctrl = self.seq)
        if not self.logon_num(num=user):
            print "login_seq_passwd: Failed to build logon"
        data = self.full_packet()

        while resp[0] == False:
            if self.debug: print "Sending: %s: %s" % ('logon',self.print_packet(data))
            self.send_data(ser_conn,data)

            # Read Response
            resp = self.read_response(ser_conn)
            if resp[0] == False:
                print "login_seq_passwd: logon response failed - ",resp[1]
                return FAIL

        # This should return OK
        if self.debug: print "Incoming data: ",bt.print_data(resp[1])
        result = struct.unpack('B',resp[1][0])[0]
        
        # Cycle Control Byte
        #SEQ ^= 1
        self.seq ^= 1
        
        if result:
            print "login_seq_passwd: Failed logon - ", resp_names[result]
            #sys.exit()
            return FAIL
        
        #Send security
        resp = [False,'']
        self.reset_packet(ctrl = self.seq)
        if not self.passwd(passwd=passwd):
            print "login_seq_passwd: Failed to build security"
        data = self.full_packet()

        if self.debug: print "Sending: %s: %s" % ('security',self.print_packet(data))
        self.send_data(ser_conn,data)

        # Read Response
        resp = self.read_response(ser_conn)
        if resp[0] == False:
            print "login_seq_passwd: security response failed - ",resp[1]
            return FAIL

        # This should return OK
        if self.debug: print "Incoming data: ",bt.print_data(resp[1])
        result = struct.unpack('B',resp[1][0])[0]
        
        # Cycle Control Byte
        #SEQ ^= 1
        self.seq ^= 1

        if result:
            print "login_seq_passwd: Failed security - ", resp_names[result]
            return FAIL

        # Return the sequence where we left off
        return SUCCESS

    def full_table_read(self,ser_conn, table):
        '''Do a full table read. If success then return results.'''

        # Create and reset packet
        #global SEQ
        #packet = c12packet.C1218_packet()

        #Send ident
        resp = [False,'']
        self.reset_packet(ctrl = self.seq)
        if not self.full_read(table=table):
            print "full_table_read: Failed to build packet"
        data = self.full_packet()
        while resp[0] == False:
            if self.debug: print "Sending: %s: %s" % ('full_table_read',self.print_packet(data))
            self.send_data(ser_conn,data)

            # Read Response
            resp = self.read_response(ser_conn)
            if resp[0] == False:
                print "full_table_read: full table read response failed - ",resp[1]
                break

        result = struct.unpack('B',resp[1][0])[0]
        
        # Cycle Control Byte
        #SEQ ^= 1
        self.seq ^= 1

        if result:
            if self.debug: print "full_table_read: Failed to read table - ", resp_names[result]
            return [FAIL,'']

        # Return the sequence where we left off
        return [SUCCESS,resp[1]]
        
    def full_table_write(self,ser_conn, table, data):
        '''Do a full table write of <data> to <table>. If success then return results.'''

        # Create and reset packet
        #global SEQ
        #packet = c12packet.C1218_packet()

        #Send ident
        resp = [False,'']
        self.reset_packet(ctrl = self.seq)
        if not self.full_write(table=table,data=data):
            print "full_table_write: Failed to build packet"
        data = self.full_packet()
        while resp[0] == False:
            if self.debug: print "Sending: %s: %s" % ('full_table_write',self.print_packet(data))
            self.send_data(ser_conn,data)

            # Read Response
            resp = self.read_response(ser_conn)
            if resp[0] == False:
                print "full_table_write: full table write response failed - ",resp[1]

        result = struct.unpack('B',resp[1][0])[0]
        
        # Cycle Control Byte
        #SEQ ^= 1
        self.seq ^= 1

        if result:
            if self.debug: print "full_table_write: Failed to run proc - ", resp_names[result]
            return [FAIL,'']

        # Return the sequence where we left off
        return [SUCCESS,resp[1]]

    def run_proc(self,ser_conn, proc, indata=''):
        '''Run the specified procedure. Standard or Manufacturer table shoule be handled before the call.'''

        # Create and reset packet
        #global SEQ
        #packet = c12packet.C1218_packet()

        #Send ident
        resp = [False,'']
        self.reset_packet(ctrl = self.seq)
        if not self.proc(proc=proc,data=indata):
            print "run_proc: Failed to build packet"
        data = self.full_packet()
        while resp[0] == False:
            if self.debug: print "Sending: %s: %s" % ('run_proc',self.print_packet(data))
            self.send_data(ser_conn,data)

            # Read Response
            resp = self.read_response(ser_conn)
            if resp[0] == False:
                print "run_proc: ident response failed - ",resp[1]

        # This should return OK
        if self.debug: print "Incoming data: ",bt.print_data(resp[1])
        result = struct.unpack('B',resp[1][0])[0]
        
        # Cycle Control Byte
        #SEQ ^= 1
        self.seq ^= 1

        if result:
            print "run_proc: Failed to run proc - ", resp_names[result]
            return FAIL

        # Return the sequence where we left off
        return SUCCESS

    ##########################################################
        
if __name__ == "__main__":

    # Test Normal Initialization
    packet = C1218_packet( p_stp = STP, p_ident = IDENT, p_ctrl = '\x00' , p_seqnbr = '\x00', p_len = '\x01', p_data = '', p_crc = '')
    for cnt in range(10):
        if not packet.full_read(table=cnt):
            print "Failed to build full_read"
        print packet.print_packet()

    print ""

    for e in logon_req_seq[0]:
        print packet.print_packet(e)

    print ""

    packet.reset_packet()
