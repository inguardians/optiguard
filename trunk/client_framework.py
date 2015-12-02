# client_framework.py - basic optical client. Use this to start 
#                       custom client and functionality
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

import sys
import time
import struct
import binascii
import byte_tools as bt
import c12_18_serial as c12serial
import c12_18_packet as c12packet
import c12_18_log_lines as c12loglines

######################################
# Menu Action Definitions 
######################################

######################################
# Dummy Action
######################################
def do_action_dummy(optic):
    return
######################################
# End Dummy Action
######################################

############################
# Toggle Debug Option
############################
def do_action_tdebug(optic):
    '''
    Action: Toggle whether or not debugging information is being displayed.
    '''
    optic.DEBUG ^= 1
    if optic.DEBUG:
        print "Debug turned ON"
    else:
        print "Debug turned OFF"

    # Return
    return
############################
# End Toggle Debug Option
############################

############################
# Toggle Invert Option
############################
def do_action_tinvert(optic):
    '''
    Action: Toggle whether or not invert the tranmission state.
    '''
            
    # Initialize Comm Port    
    optic.INVERT ^= 1
    optic.SER_CONN0.close()
    optic.SER_CONN0 = c12serial.SERCONN(debug = optic.DEBUG)
    optic.SER_CONN0.serInit(port = optic.COMM_PORT, invert = optic.INVERT)

    if optic.INVERT:
        print "Invert turned ON"
    else:
        print "Invert turned OFF"

    # Return
    return
############################
# End Toggle Invert Option
############################

############################
# Toggle Negotiation Option
############################
def do_action_tnego(optic):
    '''
    Action: Toggle whether or not to use the Negotiation Service.
    '''
    if optic.packet.state_nego():
        optic.packet.set_nego(False)
        print "Negotiation turned OFF"
    else:
        optic.packet.set_nego(True)
        print "Negotiation turned ON"

    # Set optic.NEGO_ON to new value
    optic.NEGO_ON = optic.packet.state_nego()

    # Return
    return
############################
# End Toggle Negotiation Option
############################

############################
# Terminate Session
############################
def do_action_term(optic):
    '''
    Action: Terminate current session. This often helps when functions are returning errors.
    '''
    print "Running: Terminate Session Function"

    # Logoff
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Terminate setup failed."

    # Return
    return
############################
# End Terminate Session
############################

############################
# Quit
############################
def do_action_logoff(optic):
    '''Action: Quit application and close log file'''

    print "Running: Logoff Function"

    print "Stop Time:",time.strftime('%X %x %Z')

    # Close serial conneciton and quit
    print "Done, Closing out"
    optic.SER_CONN0.close()
    sys.exit()
############################
# End Quit
############################

############################
# Serial Restart
############################
def do_action_srestart(optic):
    '''Action: Restart serial connection.'''

    print "Running: Logoff Function"

    # Close serial conneciton and quit
    print "Stopping serial connection"
    optic.SER_CONN0.close()

    print "Starting serial connection"
    optic.SER_CONN0 = c12serial.SERCONN(debug = optic.DEBUG)
    optic.SER_CONN0.serInit(port = optic.COMM_PORT, invert = optic.INVERT)

    # Return
    return

############################
# End Serial Restart
############################

############################
# Read a table
############################
def do_action_tread(optic):
    '''Action: Read the Standard or Manufacturer table provided by the user.'''

    print "Running: Read Table Function"

    # Get new user number or use default from configuration file
    user_num = raw_input(user_menu)
    if user_num == '':
        user_num = optic.USER_NUM
    else:
        user_num = int(user_num)
    print "Logging on as User: ",user_num

    # Get Table information
    table_num  = raw_input(num_menu)
    table_num  = int(table_num)

    # Setup meter connection
    if not optic.packet.login_setup(optic.SER_CONN0):
        print "Logon setup failed."
        return

    # Logon and send security code
    if not optic.packet.login_seq_passwd(optic.SER_CONN0, user_num, optic.PASSWD):
        print "Logon setup failed."
        return

    # Read Table
    print "Reading Table:",table_num

    results = optic.packet.full_table_read(optic.SER_CONN0, table_num)
    if not results[0]:
        print "Read table failed."
        return
    else:
        print "Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>"
        print "Table ",table_num," results: ",bt.print_data(results[1])

    # Logoff
    #if not optic.packet.send_logoff(optic.SER_CONN0):
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Logoff setup failed."

    # Return
    return
############################
# End Read a table
############################

##########################################################
## c12_optic()
##########################################################
class c12_optic():

    def __init__(self, comm_port = "/dev/ttyUSB0"):
        self.TIME           = time.strftime('%Y%m%d%H%M%S')
        self.DEBUG          = True
        self.COMM_PORT      = comm_port
        self.PASSWD         = ('\x20' * 20)
        self.USER_STR       = ('\x53\x4d\x41\x43\x4B' + '\x20' * 5) # SMACK
        self.USER_NUM       = 2
        self.INVERT         = 0
        self.NEGO_ON        = True
                
        # Initialize Comm Port    
        self.SER_CONN0 = c12serial.SERCONN(debug = self.DEBUG)
        self.SER_CONN0.serInit(port = self.COMM_PORT, invert = self.INVERT)

        # Setup and configure packet
        self.packet = self.config_packet()
        self.packet.set_debug(self.DEBUG)
        self.packet.set_nego(self.NEGO_ON)

        if self.DEBUG: print 'Debug:',self.DEBUG
        if self.DEBUG: print 'comm_port:',self.COMM_PORT
        if self.DEBUG: print 'passwd:',bt.print_data(self.PASSWD)
        if self.DEBUG: print 'user_str:',bt.print_data(self.USER_STR)
        if self.DEBUG: print 'user_num:',self.USER_NUM
        if self.DEBUG: print 'Negotiation:',self.NEGO_ON
        if self.DEBUG: print 'Invert:',self.INVERT


    def config_packet(self):
        '''Setup C12.18 packet.'''
        packet = c12packet.C1218_packet()
        return packet

##########################################################
## End c12_optic()
##########################################################

######################################
# User Input Action Menu
######################################
action_menu = [ \
    ["Quit", do_action_logoff], \
    ["Read Table", do_action_tread ], \
    ["Toggle Debug", do_action_tdebug ], \
    ["Toggle Invert", do_action_tinvert ], \
    ["Toggle Negotiation", do_action_tnego ], \
    ["Terminate Session", do_action_term ], \
    ["Reset Serial", do_action_srestart ], \
]

# User Menus
user_menu   = "\n   Logon as User Number. Hit enter for default.\n   Enter number (0-65535): "
num_menu    = "\n   Enter Number: "
######################################

######################################
# Main Starts Here
######################################

# Set up main object
optic = c12_optic()

# FIXME: c12_18_optical_client.py: main: Move this header information to an external file
print c12loglines.separator_long
print c12loglines.log_header
print c12loglines.log_license
print c12loglines.separator_long

# Mark starting time selecting quit will mark ending time
print "Start Time:",time.strftime('%X %x %Z')

while (True):
    # Determine the action to perform
    print c12loglines.separator_short
    for i in range(len(action_menu)):
        print "## {0}) {1}".format(i, action_menu[i][0])
    print c12loglines.separator_short

    action_num = raw_input('Enter Action Selection: ')
    try:
        action_num = int(action_num)
        action_menu[action_num][1](optic)
    except (ValueError, IndexError):
        print "Error: action must be a number from 0 to {0}".format(len(action_menu))

