# c12_18_hw_client.py - Client for reading and writing to C12.19 
# Standard and Manufacturer tables and running Standard and Manufacturer 
# procedures via the hardware lines that run between components and boards.
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

import c12_18_serial as c12serial
import c12_18_packet as c12packet
import c12_18_table00_parser as c12tbl00
import byte_tools as bt
import os, sys, time, struct, time
import ConfigParser
import time
import warnings

def usage():
    print "Usage: %s [-h] [-D] [-P <num>] [-f <file>] [-no] -a <action> [-t <num>] [-d <num>] [-p <num>] [-s <data>] [-lp <comma separated list>]" % sys.argv[0]
    print "   -h: print help"
    print "   -D: turn on debugging statements"
    print "   -P <num>: Start pause seconds"
    print "   -a <action>: Perform specific action:"
    print "       test_login"
    print "       read_table: requires -t and table number or defaults to 0"
    print "       read_decade: requires -d and decade number or defaults to 0"
    print "       run_proc: requires -p and procedure number or defaults to 0"
    print "   -f <file>: select configuration file"
    print "   -t <num>: table number"
    print "   -d <num>: decade number"
    print "   -p <num>: procedure number"
    print "   -s <data>: data for sending"
    print "   -lp <data>: comma separated list of procedure numbers"
    print "   -no: turn off negotiation attempts"
    print "\n\n"
    print "NOTE: This tool is fire and forget.  You will need to monitor the hardware lines"
    print "      with a logic analyzer to determine success and failure or to read data."
    print "\n\n"
    sys.exit()
    
if len(sys.argv) == 1:
    usage()

#Default to 100 in case we are doing this from meter start
start_delay = 100

def send_data(ser_conn, data = None):
    '''Send C12.18 packet'''
    if data == None:
        print "send_data: No data"
        sys.exit()

    if not ser_conn.write_bytes(data = data):
        print "send_data: Serial Write Failed"
        sys.exit()

def send_ack(ser_conn,pause=0):
    '''Send C12.19 ack packet'''
    # Pause for just a bit in case blind ack
    if pause:
        c12packet.delay(pause)
    
    #Send Blind ACK
    if not ser_conn.write_bytes(data = c12packet.ACK):
        print "send_ack: Serial Write Failed"
        sys.exit()
        
    print "    Sent ACK"

def login_setup(ser_conn):
    '''Provides the ability to logon using a specific user and specific passwd'''
    global SEQ

    # Create and reset packet
    packet = c12packet.C1218_packet()

    #Send ident
    packet.reset_packet(ctrl = SEQ)
    if not packet.ident():
        print "login_seq_passwd: Failed to build ident"
        return FAIL
    data = packet.full_packet()
    print "Sending: %s: %s" % ('ident:',packet.print_packet(data))
    send_data(ser_conn,data)
    # Blind ACK
    send_ack(ser_conn,cmd_pause)
    # Cycle Control Byte
    SEQ ^= 1

    if NEGO_ON:
        #Send nego
        packet.reset_packet(ctrl = SEQ)
        if not packet.nego():
            print "login_seq_passwd: Failed to build nego"
            return FAIL
        data = packet.full_packet()
        print "Sending: %s: %s" % ('nego:',packet.print_packet(data))
        send_data(ser_conn,data)
        # Blind ACK
        send_ack(ser_conn,cmd_pause)
        # Cycle Control Byte
        SEQ ^= 1

    # Return the sequence where we left off
    return SUCCESS

def login_seq_passwd(ser_conn, user, passwd):
    '''Provides the ability to logon using a specific user and specific passwd'''
    global SEQ

    # Create and reset packet
    packet = c12packet.C1218_packet()

    #Send logon
    packet.reset_packet(ctrl = SEQ)
    if not packet.logon_num(num=user):
        print "login_seq_passwd: Failed to build logon"
    data = packet.full_packet()
    print "Sending: %s: %s" % ('logon:',packet.print_packet(data))
    send_data(ser_conn,data)
    # Blind ACK
    send_ack(ser_conn,cmd_pause)
    # Cycle Control Byte
    SEQ ^= 1

    #Send security
    packet.reset_packet(ctrl = SEQ)
    if not packet.passwd(passwd=passwd):
        print "login_seq_passwd: Failed to build security"
    data = packet.full_packet()
    print "Sending: %s: %s" % ('security:',packet.print_packet(data))
    send_data(ser_conn,data)
    # Blind ACK
    send_ack(ser_conn,cmd_pause)
    # Cycle Control Byte
    SEQ ^= 1

    # Return the sequence where we left off
    return SUCCESS

def full_table_read(ser_conn, table):
    global SEQ

    # Create and reset packet
    packet = c12packet.C1218_packet()
    packet.reset_packet(ctrl = SEQ)

    # Build read packet and send
    packet.full_read(table=table)
    data = packet.full_packet()
    print "Sending: %s: %s" % ('full_read:',packet.print_packet(data))
    send_data(ser_conn,data)

    # Blind ACK
    send_ack(ser_conn,cmd_pause * 3)
    
    # Cycle Control Byte
    SEQ ^= 1

    # Return the sequence where we left off
    return SUCCESS

def run_proc(ser_conn, proc,indata = ''):
    global SEQ

    # Create and reset packet
    packet = c12packet.C1218_packet()
    packet.reset_packet(ctrl = SEQ)

    # Build procedure packet and send
    packet.proc(proc=proc,data=indata)
    data = packet.full_packet()
    print "Sending: %s: %s" % ('run_proc:',packet.print_packet(data))
    send_data(ser_conn,data)

    # Blind ACK
    send_ack(ser_conn,cmd_pause)
    
    # Cycle Control Byte
    SEQ ^= 1

    # Return the sequence where we left off
    return SUCCESS

def term_session(ser_conn):
    global SEQ

    # Create and reset packet
    packet = c12packet.C1218_packet()
    packet.reset_packet(ctrl = SEQ)

    # Build read packet and send
    packet.term()
    data = packet.full_packet()
    print "Sending: %s: %s" % ('term_session:',packet.print_packet(data))
    send_data(ser_conn,data)

    # Blind ACK
    send_ack(ser_conn,cmd_pause)
    
    # Cycle Control Byte
    SEQ ^= 1

    # Return the sequence where we left off
    return SUCCESS

######################################
# Parse C12.18 Optical Configuration file
######################################
inf   = 'c12_18_config.txt'

TIME      = time.strftime('%Y%m%d%H%M%S')
DEBUG     = False
NEGO_ON   = True
TABLE_NUM = 0
DECADE_NUM = 0
PROC_NUM  = 0
COMM_PORT = SEND_DATA = OUTFILE = USER_NUM = USER_STR = PASSWD = PASSWD_FILE = ''
action    = ''

while len(sys.argv) > 1:
    op = sys.argv.pop(1)
    # Action
    if op == '-a':
        action = sys.argv.pop(1)
    # Help
    if op == '-h':
        usage()
    # Debug
    if op == '-D':
        DEBUG = True
    # Configuration file
    if op == '-f':
        inf = sys.argv.pop(1)
    # Pause Time in sections
    if op == '-P':
        start_delay = int(sys.argv.pop(1))
    # Table number
    if op == '-t':
        TABLE_NUM = int(sys.argv.pop(1))
    # Decade number
    if op == '-d':
        DECADE_NUM = int(sys.argv.pop(1))
    # Procedure number
    if op == '-p':
        PROC_NUM = int(sys.argv.pop(1))
    # Send data
    if op == '-s':
        SEND_DATA = bt.str2hex(sys.argv.pop(1))
    # Procedure list
    if op == '-lp':
        lp = sys.argv.pop(1)
        list_proc = lp.split(',')
    # Send data
    if op == '-no':
        NEGO_ON = False

if not action:
    usage()

try:
    print "Using configuration file:",inf
    config      = ConfigParser.ConfigParser()
    config.read(inf)

    DEBUG       = config.getint('C1218Hardware','debug')
    #OUTFILE     = config.get('C1218Hardware','outfile')
    # Make output file unique
    TMP_OUTFILE = OUTFILE.split('.')
    #OUTFILE     = TMP_OUTFILE[0] + '_' + TIME + '.' + TMP_OUTFILE[1]
    USER_NUM    = config.getint('C1218Hardware','user_num')
    USER_STR    = bt.str2hex(config.get('C1218Hardware','user_str'))[:10]
    USER_STR    += ('\x20' * (10 - len(USER_STR)))
    PASSWD      = bt.str2hex(config.get('C1218Hardware','passwd'))
    PASSWD      += ('\x20' * (20 - len(PASSWD)))
    PASSWD_FILE = config.get('C1218Hardware','passwd_file')
    COMM_PORT   = config.get('C1218Hardware','comm_port')
    COMM_BAUD   = config.get('C1218Hardware','comm_baud')
    NEGO_ON     = config.get('C1218Hardware','nego_on')
except:
    print "No configuration file found"

    # Provide some defaults in case configuration file not available
    TIME           = time.strftime('%Y%m%d%H%M%S')
    DEBUG          = False
    CONFIG_FILE    = config_file
    COMM_PORT      = comm_port
    COMM_BAUD      = 9600
    OUTFILE        = 'c1218_optical_results_' + self.TIME + '.txt'
    PASSWD         = ('\x20' * 20)
    USER_STR       = ('\x53\x4d\x41\x43\x4B' + '\x20' * 5) # SMACK
    USER_NUM       = 2
    INVERT         = 0
    NEGO_ON        = False
    PASSWD_FILE    = ''

if DEBUG: print 'Debug:',DEBUG
if DEBUG: print 'config file:',CONFIG_FILE
if DEBUG: print 'comm_port:',COMM_PORT
if DEBUG: print 'comm_baud:',COMM_BAUD
if DEBUG: print 'outfile:',OUTFILE
if DEBUG: print 'passwd:',bt.print_data(PASSWD)
if DEBUG: print 'user_str:',bt.print_data(USER_STR)
if DEBUG: print 'user_num:',USER_NUM
if DEBUG: print 'Invert:',INVERT
if DEBUG: print 'Negotiation:',NEGO_ON
if DEBUG: print 'passwd_file:',PASSWD_FILE
######################################
# End: Parse C12.18 Optical Configuration file
######################################

######################################
# VARIABLES - These values will not  change
######################################
# Delay values
#start_delay = 100
#start_delay = 1
cmd_pause   = .15
no_pause    = 0
logon_pause = 5

# Outcomes
SUCCESS = True
FAIL    = False

# Initialize Comm Port    
SER_CONN0 = c12serial.SERCONN(debug = DEBUG)
SER_CONN0.serInit(port = COMM_PORT,baud = COMM_BAUD, invert = INVERT)

# Setup and configure packet
packet = c12packet.C1218_packet()
packet.set_debug(DEBUG)
packet.set_nego(NEGO_ON)

if action == "test_login":
    '''Test login to determine if password works'''

    print "Running test_login function"
    if DEBUG: print "Start Delay:",start_delay
    c12packet.delay(start_delay)

    if not packet.login_setup(ser_conn0):
        print action,': login_setup failed.'
        sys.exit()
    if not packet.login_seq_passwd(ser_conn0,USER_NUM,PASSWD):
        print action,': login_seq_passwd failed.'
        sys.exit()

    # Close gracefully
    print action,": Successful"
    ser_conn0.close()

if action == "read_table":
    '''Reads all tables in a decade.  STD tables should be between 0 and 169.  MFG decades should be between 2040 and 2200, (MFG dependant).'''

    print "Running read_table function"
    # Read a table
    if DEBUG: print "Reading Table:",TABLE_NUM

    # Login
    if not packet.login_setup(ser_conn0):
        print action,': login_setup failed.'
        sys.exit()
    if not packet.login_seq_passwd(ser_conn0,USER_NUM,PASSWD):
        print action,': login_seq_passwd failed.'
        sys.exit()

    # Read Table
    if not packet.full_table_read(ser_conn0, TABLE_NUM):
        print action,": Failed to full_table_read:",table_num
        sys.exit()

    # Close gracefully
    print action,": Successful"
    ser_conn0.close()

if action == "read_decade":
    '''Reads all tables in a decade.  STD tables should be between 0 and 16.  MFG decades should be between 204 and 220, (MFG dependant).'''

    print "Running read_decade function"
    # Read a decade
    if DEBUG: print "Reading Decade:",TABLE_NUM

    # Login
    if not packet.login_setup(ser_conn0):
        print action,': login_setup failed.'
        sys.exit()
    if not packet.login_seq_passwd(ser_conn0,USER_NUM,PASSWD):
        print action,': login_seq_passwd failed.'
        sys.exit()

    # Read Decade
    for table_num in range(DECADE_NUM*10,(DECADE_NUM*10)+10):
        if not packet.full_table_read(ser_conn0, table_num):
            print action,": Failed to full_table_read:",table_num
            sys.exit()

    # Close gracefully
    print action,": Successful"
    ser_conn0.close()

if action == "run_proc":
    '''Runs a single procedure.  STD procedures should run between 0 and 32. MFG table should run between 2048 and 2340 (MFG dependent).'''

    if not PROC_NUM:
        print action,': must specify procedure number'
        usage()

    # Login
    if not packet.login_setup(ser_conn0):
        print action,': login_setup failed.'
        sys.exit()
    if not packet.login_seq_passwd(ser_conn0,USER_NUM,PASSWD):
        print action,': login_seq_passwd failed.'
        sys.exit()

    # Run Procedure
    if not packet.run_proc(ser_conn0, PROC_NUM,indata = SEND_DATA):
        print action,": Failed to run_proc:",PROC_NUM
        sys.exit()

    # Read Table 8 three times
    for table_num in (8,115, 2162):
        print "Table 8 read number:", table_num
        if not packet.full_table_read(ser_conn0, table_num):
            print action,": Failed to full_table_read:",table_num
            sys.exit()

    if not packet.send_terminate(ser_conn0):
        print action,": Failed to terminate session"
        sys.exit()

    # Done, Close out
    ser_conn0.close()
