# c12_18_optical_client.py - Client for reading and writing to C12.19 
# Standard and Manufacturer tables and running Standard and Manufacturer 
# procedures via the ANSI Type-2 Optical Port.
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

# TODO: c12_18_optical_client.py: Toggle user number query
# TODO: c12_18_optical_client.py: Address Fix me issues
# TODO: c12_18_optical_client.py: Make it so action functions can accept input
# TODO: c12_18_optical_client.py: Format logging output to make it easier to use and read
# TODO: c12_18_optical_client.py: Make log and output header a configuration variable
# TODO: c12_18_optical_client.py: Add table parsers for Standard Tables
# TODO: c12_18_optical_client.py: Convert this to an optical client class for better state tracking

import os
import sys
import time
import struct
import binascii
import byte_tools as bt
import c12_18_serial as c12serial
import c12_18_packet as c12packet
import c12_18_table00_parser as c12tbl00
import c12_18_log_lines as c12loglines
import ConfigParser
import warnings

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
    if optic.DEBUG: print "Original Serial Invert:",optic.INVERT
    optic.INVERT ^= 1
    optic.SER_CONN0.close()
    optic.SER_CONN0 = c12serial.SERCONN(debug = optic.DEBUG)
    optic.SER_CONN0.serInit(port = optic.COMM_PORT, invert = optic.INVERT)
    if optic.DEBUG: print "New Serial Invert:",optic.INVERT

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
    if optic.ONF: optic.ONF.write("Running: Terminate Session function\n")

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
    if optic.ONF: optic.ONF.write("Running: Logoff function\n")

    print "Stop Time:",time.strftime('%X %x %Z')
    if optic.ONF: optic.ONF.write("Stop Time: " + time.strftime('%X %x %Z') + "\n")
    optic.ONF.close()

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
    '''Action: Reset serial connection'''

    print "Running: Logoff Function"
    if optic.ONF: optic.ONF.write("Running: Logoff function\n")

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
# Logon without the negotiation sequence
############################
def do_action_test_nego(optic):
    '''Action: Test if meter requires Negotiation Service. Some meters to do need it and 
    actions will fail if they are enabled.'''

    print "Running: Test Negotiation Function"
    if optic.ONF: optic.ONF.write("Running: Test Negotiation Function\n")

    # Get new user number or use default from configuration file
    user_num = raw_input(user_menu)
    if user_num == '':
        user_num = optic.USER_NUM
    else:
        user_num = int(user_num)

    print "Logging on as User: ",user_num
    if optic.ONF: optic.ONF.write("Logging on as User: " + str(user_num) + "\n")
    
    # Setup meter connection
    if not optic.packet.ident_setup(optic.SER_CONN0):
        print "Ident setup failed."
        return

    # Logon
    if not optic.packet.login_user(optic.SER_CONN0, user_num):
        print "Logon setup failed."
        return

    # Send security code
    if optic.packet.login_passwd(optic.SER_CONN0, optic.PASSWD):
        print "Test negotiate sequence successful. Modifying negotiation state."
        if optic.ONF: optic.ONF.write("Test negotiate sequence successful. Modifying negotiation state.\n")

        # If it is negotiation state is on then turn it off
        if optic.packet.state_nego():
            optic.packet.toggle_nego()
    else:
        print "Test negotiate sequence failed. Negotiation state unmodified."
        if optic.ONF: optic.ONF.write("Test negotiate sequence failed. Negotiation state unmodified.\n")

    # Logoff
    #if not optic.packet.send_logoff(optic.SER_CONN0):
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Logoff failed."

    # Return
    return
############################
# End Logon without the negotiation sequence
############################

############################
# Test logon
############################
def do_action_test(optic):
    '''Action: Test the current password. Allows the user to change default password.'''

    # Global used so that other functions can use updated password
    #global PASSWD

    print "Running: Test Logon Function"
    if optic.ONF: optic.ONF.write("Running: Test Logon function\n")
    print "Current password: ",bt.print_data(optic.PASSWD)
    if optic.ONF: optic.ONF.write("Current password: " + bt.print_data(optic.PASSWD) + "\n\n")

    # Get new user number or use default from configuration file
    user_num = raw_input(user_menu)
    if user_num == '':
        user_num = optic.USER_NUM
    else:
        user_num = int(user_num)

    # Ask user for security code to test
    test_pwd = raw_input(pwd_menu)
    if test_pwd == '':
        test_pwd = optic.PASSWD
    else:
        test_pwd = bt.str2hex(test_pwd)
        # Test for passwd length and pad if necessary
        if len(test_pwd) < 20:
            test_pwd = test_pwd + ('\x20' * (20 - len(test_pwd)))

    print "Logging on as User: ",user_num
    if optic.ONF: optic.ONF.write("Logging on as User: " + str(user_num) + "\n")
    print "Using password:",bt.print_data(test_pwd)
    if optic.ONF: optic.ONF.write("Using password:" + bt.print_data(test_pwd) + "\n")

    # Setup meter connection
    if not optic.packet.login_setup(optic.SER_CONN0):
        print "Logon setup failed."
        return

    # Logon and send security code
    if not optic.packet.login_seq_passwd(optic.SER_CONN0, user_num, test_pwd):
        print "Logon setup failed."
        return

    # Logoff
    #if not optic.packet.send_logoff(optic.SER_CONN0):
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Logoff setup failed."

    print "Logged on as User: ",user_num
    if optic.ONF: optic.ONF.write("Logged on as User: " + str(user_num) + "\n")

    # Check if user wants to use the security code they provided
    chg_pwd = raw_input('    Enter Y if you would like to update default password:')
    # Force the user to use a capitol Y
    if chg_pwd == 'Y':
        optic.PASSWD = test_pwd
        print "Password updated to:",bt.print_data(optic.PASSWD)
        if optic.ONF: optic.ONF.write("Password updated to:" + bt.print_data(optic.PASSWD) + "\n")
    else:
        print "Password not updated"
        if optic.ONF: optic.ONF.write("Password not updated\n")

    # Return
    return
############################
# End Test logon
############################

############################
# Parse the Configuration Table (Table 00)
############################
def do_action_tread00(optic):
    '''Action: Parse the configuration table to determine Standard and Manufacturer 
    Tables and Procedures in use by the meter. This information should be verified 
    as active tables and procedures many not be documented here.'''

    print "Running: Parse Configuration Table Function"
    if optic.ONF: optic.ONF.write("Running: Parse Configuration Table function\n")

    # Get new user number or use default from configuration file
    user_num = raw_input(user_menu)
    if user_num == '':
        user_num = optic.USER_NUM
    else:
        user_num = int(user_num)

    print "Logging on as User: ",user_num
    if optic.ONF: optic.ONF.write("Logging on as User: " + str(user_num) + "\n")

    # Get Table information
    table_num  = 0      # Configuration Table is Table 00

    # Setup meter connection
    if not optic.packet.login_setup(optic.SER_CONN0):
        print "Logon setup failed."
        return

    # Logon and send security code
    if not optic.packet.login_seq_passwd(optic.SER_CONN0, user_num, optic.PASSWD):
        print "Logon sequence passwd failed."
        return

    # Read Table
    print "Reading Table:",table_num
    if optic.ONF: optic.ONF.write("Reading Table: " + str(table_num) + "\n")

    results = optic.packet.full_table_read(optic.SER_CONN0, table_num)
    if not results[0]:
        print "Read table failed."
        return
    else:
        print "Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>"
        if optic.ONF: optic.ONF.write("Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>\n")
        print "Table ",table_num," results: ",bt.print_data(results[1])
        if optic.ONF: optic.ONF.write("Table " + str(table_num) + " results: " + bt.print_data(results[1]) + "\n")

    # Logoff early because we are just parsing from here
    #if not optic.packet.send_logoff(optic.SER_CONN0):
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Logoff setup failed."
        # Logging off doesn't really matter, provide information

    # Parsed Data - incoming values [data[:1], length, data[3:(3 + length)], data[-1:]]
    r_response, data_len, r_data, r_crc = optic.packet.parse_rtn_data(results[1])

    print "\nParsed Configuration Table Data:",bt.print_data(r_data),"\n"
    if optic.ONF: optic.ONF.write("\nParsed Configuration Table Data: " + bt.print_data(r_data) + "\n\n")

    # Sort returned data
    format_cnt_1      = r_data[0]
    format_cnt_2      = r_data[1]
    format_cnt_3      = r_data[2]
    device_class      = r_data[3:7]
    nameplate_type    = ord(r_data[7])
    default_set_used  = ord(r_data[8])
    max_proc_parm_len = ord(r_data[9])
    max_resp_data_len = ord(r_data[10])
    std_version_no    = ord(r_data[11])
    std_revision_no   = ord(r_data[12])
    dim_std_tbls_used = ord(r_data[13])
    dim_mfg_tbls_used = ord(r_data[14])
    dim_std_proc_used = ord(r_data[15])
    dim_mfg_proc_used = ord(r_data[16])
    dim_mfg_stat_used = ord(r_data[17])
    nbr_pending       = ord(r_data[18])

    if optic.DEBUG: print 'format_cnt_1',bt.print_data(format_cnt_1)
    if optic.DEBUG: print 'format_cnt_2',bt.print_data(format_cnt_2)
    if optic.DEBUG: print 'format_cnt_3',bt.print_data(format_cnt_3)
    if optic.DEBUG: print 'device_class',bt.print_data(device_class)
    if optic.DEBUG: print 'nameplate_type',nameplate_type
    if optic.DEBUG: print 'default_set_used',default_set_used
    if optic.DEBUG: print 'max_proc_parm_len',max_proc_parm_len
    if optic.DEBUG: print 'max_resp_data_len',max_resp_data_len
    if optic.DEBUG: print 'std_version_no',std_version_no
    if optic.DEBUG: print 'std_revision_no',std_revision_no
    if optic.DEBUG: print 'dim_std_tbls_used',dim_std_tbls_used
    if optic.DEBUG: print 'dim_mfg_tbls_used',dim_mfg_tbls_used
    if optic.DEBUG: print 'dim_std_proc_used',dim_std_proc_used
    if optic.DEBUG: print 'dim_mfg_proc_used',dim_mfg_proc_used
    if optic.DEBUG: print 'dim_mfg_stat_used',dim_mfg_stat_used
    if optic.DEBUG: print 'nbr_pending',nbr_pending

    tbl_start         = 19
    std_tbls_used     = r_data[tbl_start:(tbl_start + dim_std_tbls_used)]
    if optic.DEBUG: print 'std_tbls_used',bt.print_data(std_tbls_used)

    tbl_start         = tbl_start + dim_std_tbls_used
    mfg_tbls_used     = r_data[tbl_start:(tbl_start + dim_mfg_tbls_used)]
    if optic.DEBUG: print 'mfg_tbls_used',bt.print_data(mfg_tbls_used)

    tbl_start         = tbl_start + dim_mfg_tbls_used
    std_proc_used     = r_data[tbl_start:(tbl_start + dim_std_proc_used)]
    if optic.DEBUG: print 'std_proc_used',bt.print_data(std_proc_used)
    
    tbl_start         = tbl_start + dim_std_proc_used
    mfg_proc_used     = r_data[tbl_start:(tbl_start + dim_mfg_proc_used)]
    if optic.DEBUG: print 'mfg_proc_used',bt.print_data(mfg_proc_used)

    tbl_start         = tbl_start + dim_mfg_proc_used
    std_tbls_write    = r_data[tbl_start:(tbl_start + dim_std_tbls_used)]
    if optic.DEBUG: print 'std_tbls_write',bt.print_data(std_tbls_write)

    tbl_start         = tbl_start + dim_std_tbls_used
    mfg_tbls_write    = r_data[tbl_start:(tbl_start + dim_mfg_proc_used)]
    if optic.DEBUG: print 'mfg_tbls_write',bt.print_data(mfg_tbls_write)
    
    # Print lists of tables and procedures for later use
    print 'Standard Tables',c12tbl00.get_tables(std_tbls_used,c12tbl00.std_base)
    if optic.ONF: optic.ONF.write("\nStandard Tables: " + str(c12tbl00.get_tables(std_tbls_used,c12tbl00.std_base)) + "\n\n")
    print 'Manufacturer Tables',c12tbl00.get_tables(mfg_tbls_used,c12tbl00.mfg_base)
    if optic.ONF: optic.ONF.write("\nManufacturer Tables: " + str(c12tbl00.get_tables(mfg_tbls_used,c12tbl00.mfg_base)) + "\n\n")
    print 'Standard Procedures',c12tbl00.get_procs(std_proc_used,c12tbl00.std_base)
    if optic.ONF: optic.ONF.write("\nStandard Procedures: " + str(c12tbl00.get_procs(std_proc_used,c12tbl00.std_base)) + "\n\n")
    print 'Manufacturer Procedures',c12tbl00.get_procs(mfg_proc_used,c12tbl00.mfg_proc_base)
    if optic.ONF: optic.ONF.write("\nManufacturer Procedures: " + str(c12tbl00.get_procs(mfg_proc_used,c12tbl00.mfg_proc_base)) + "\n\n")
    print 'Standard Writable Tables',c12tbl00.get_tables(std_tbls_write,c12tbl00.std_base)
    if optic.ONF: optic.ONF.write("\nStandard Writable Tables: " + str(c12tbl00.get_tables(std_tbls_write,c12tbl00.std_base)) + "\n\n")
    print 'Manufacturer Writable Tables',c12tbl00.get_tables(mfg_tbls_write,c12tbl00.mfg_base)
    if optic.ONF: optic.ONF.write("\nManufacturer Writable Tables: " + str(c12tbl00.get_tables(mfg_tbls_write,c12tbl00.mfg_base)) + "\n\n")

    # Return
    return
############################
# End Parse the Configuration Table (Table 00)
############################

############################
# Parse the General Manufacturer Identification Table (Table 01)
############################
def do_action_tread01(optic):
    '''Action: Parse the General manufacturer Identificaiton Table (Table 01). This table 
    provides manufacturer name, meter model, serial number, firmware version, and hardware 
    version information.'''

    print "Running: Parse General Manufacturer Identification Table Function"
    if optic.ONF: optic.ONF.write("Running: Parse General Manufacturer Identification Table Function\n")

    # Get new user number or use default from configuration file
    user_num = raw_input(user_menu)
    if user_num == '':
        user_num = optic.USER_NUM
    else:
        user_num = int(user_num)
    
    print "Logging on as User: ",user_num
    if optic.ONF: optic.ONF.write("Logging on as User: " + str(user_num) + "\n")

    # Get Table information
    table_num  = 1      # General manufacturer Identification Table is Table 01

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
    if optic.ONF: optic.ONF.write("Reading Table: " + str(table_num) + "\n")

    results = optic.packet.full_table_read(optic.SER_CONN0, table_num)
    if not results[0]:
        print "Read table failed."
        return
    else:
        print "Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>"
        if optic.ONF: optic.ONF.write("Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>\n")
        print "Table ",table_num," results: ",bt.print_data(results[1])
        if optic.ONF: optic.ONF.write("Table " + str(table_num) + " results: " + bt.print_data(results[1]) + "\n")

    # Logoff early because we are just parsing from here
    #if not optic.packet.send_logoff(optic.SER_CONN0):
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Logoff setup failed."
        # Logging off doesn't really matter, provide information

    # Parsed Data - incoming values [data[:1], length, data[3:(3 + length)], data[-1:]]
    r_response, data_len, r_data, r_crc = optic.packet.parse_rtn_data(results[1])

    print "\nParsed General manufacturer Identification Table Data:",bt.print_data(r_data),"\n"
    if optic.ONF: optic.ONF.write("\nParsed General manufacturer Identification Table Data: " + bt.print_data(r_data) + "\n\n")

    # Sort returned data
    manufacturer      = r_data[0:4]
    ed_model          = r_data[4:12]
    hw_version_nm     = ord(r_data[13])
    hw_revision_nm    = ord(r_data[14])
    fw_version_nm     = ord(r_data[15])
    fw_revision_nm    = ord(r_data[16])
    mfg_serial_nm     = r_data[17:]
    
    # Print lists of tables and procedures for later use
    print 'Manufacturer',manufacturer
    if optic.ONF: optic.ONF.write("\nManufacturer: " + manufacturer + "\n\n")
    print 'End Device Model',ed_model
    if optic.ONF: optic.ONF.write("\nEnd Device Model: " + ed_model + "\n\n")
    print 'Hardware Version Number',hw_version_nm
    if optic.ONF: optic.ONF.write("\nHardware Version Number: " + str(hw_version_nm) + "\n\n")
    print 'Hardware Revision Number',hw_version_nm
    if optic.ONF: optic.ONF.write("\nHardware Revision Number: " + str(hw_version_nm) + "\n\n")
    print 'Firmware Version Number',fw_version_nm
    if optic.ONF: optic.ONF.write("\nHardware Version Number: " + str(fw_version_nm) + "\n\n")
    print 'Firmware Revision Number',fw_version_nm
    if optic.ONF: optic.ONF.write("\nHardware Revision Number: " + str(fw_version_nm) + "\n\n")
    print 'Manufacturer Serial Number',mfg_serial_nm
    if optic.ONF: optic.ONF.write("\nManufacturer Serial Number: " + mfg_serial_nm + "\n\n")

    # Return
    return
############################
# End Parse the General Manufacturer Identification Table (Table 01)
############################

############################
# Read a table
############################
def do_action_tread(optic):
    '''Action: Read the Standard or Manufacturer table provided by the user.'''

    print "Running: Read Table Function"
    if optic.ONF: optic.ONF.write("Running: Read Table function\n")

    # Get new user number or use default from configuration file
    user_num = raw_input(user_menu)
    if user_num == '':
        user_num = optic.USER_NUM
    else:
        user_num = int(user_num)
    print "Logging on as User: ",user_num
    if optic.ONF: optic.ONF.write("Logging on as User: " + str(user_num) + "\n")

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
    if optic.ONF: optic.ONF.write("Reading Table: " + str(table_num) + "\n")

    results = optic.packet.full_table_read(optic.SER_CONN0, table_num)
    if not results[0]:
        print "Read table failed."
        return
    else:
        print "Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>"
        if optic.ONF: optic.ONF.write("Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>\n")
        print "Table ",table_num," results: ",bt.print_data(results[1])
        if optic.ONF: optic.ONF.write("Table " + str(table_num) + " results: " + bt.print_data(results[1]) + "\n")

    # Logoff
    #if not optic.packet.send_logoff(optic.SER_CONN0):
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Logoff setup failed."

    # Return
    return
############################
# End Read a table
############################

############################
# Read a multiple tables
############################
def do_action_mread(optic):
    '''
    Action: Read multiple tables. User will provide a comma separated list of table numbers or read all.
    Standard Tables: Range 0 thru 170
    Manufacture Tables: Range 2040 thru 2159

    Note: this run is timed.
    '''

    print "Running: Read Multiple Tables Function"
    if optic.ONF: optic.ONF.write("Running: Read Multiple Tables Function\n")

    # Get new user number or use default from configuration file
    user_num = raw_input(user_menu)
    if user_num == '':
        user_num = optic.USER_NUM
    else:
        user_num = int(user_num)

    print "Logging on as User: ",user_num
    if optic.ONF: optic.ONF.write("Logging on as User: " + str(user_num) + "\n")

    # Get Table information
    table_type = raw_input(table_menu)
    table_type = int(table_type)

    table_nums  = raw_input(mtable_menu)
    if table_nums == '' or table_nums.lower() == 'all':
        if table_type:
            table_nums = range(2040,2160)
        else:
            table_nums = range(170)
    else:
        table_nums  = table_nums.split(',')
        for e in range(len(table_nums)):
            table_nums[e] = int(table_nums[e])

    if table_type:
        print "Reading Manufacture Tables"
        if optic.ONF: optic.ONF.write("Reading Manufacture Tables\n")
    else:
        print "Reading Standard Tables"
        if optic.ONF: optic.ONF.write("Reading Standard Tables\n")

    # Time run for future efforts
    print "Multi-table Read Start Time:",time.strftime('%X %x %Z')
    if optic.ONF: optic.ONF.write("Multi-table Read Start Time: " + time.strftime('%X %x %Z') + "\n")

    # Setup meter connection
    if not optic.packet.login_setup(optic.SER_CONN0):
        print "Logon setup failed."
        return

    # Logon and send security code
    if not optic.packet.login_seq_passwd(optic.SER_CONN0, user_num, optic.PASSWD):
        print "Logon setup failed."
        return

    for table_num in table_nums:
        # Read Table
        print "Reading Table:",table_num
        if optic.ONF: optic.ONF.write("Reading Table: " + str(table_num) + "\n")

        results = optic.packet.full_table_read(optic.SER_CONN0, table_num)
        if not results[0]:
            print "Read table failed."
            return
        else:
            print "Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>"
            if optic.ONF: optic.ONF.write("Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>\n")
            print "Table",table_num,"results:",bt.print_data(results[1])
            if optic.ONF: optic.ONF.write("Table " + str(table_num) + " results: " + bt.print_data(results[1]) + "\n")

    # Logoff
    #if not optic.packet.send_logoff(optic.SER_CONN0):
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Logoff setup failed."

    # Stop and record time
    print "Multi-table Read Stop Time:",time.strftime('%X %x %Z')
    if optic.ONF: optic.ONF.write("Multi-table Read Stop Time: " + time.strftime('%X %x %Z') + "\n")

    # Return
    return
############################
# End Read a multiple tables
############################

############################
# Read multiple tables as different users
############################
def do_action_fmread(optic):
    '''
    Action: Read multiple tables as different users. User will provide a list of users
    or select all users which is user number 0 thru 15. User will also be prompted for
    a list of tables.
    '''

    print "Running: Read Multiple Tables as different users Function"
    if optic.ONF: optic.ONF.write("Running: Read Multiple Tables as different users Function\n")

    # Get a range of user numbers to use
    print fuser_menu
    user_num_s = raw_input(fuser_menu_s)
    if user_num_s == 'all':
        user_num_s = 0
        user_num_e = 15
    else:
        if user_num_s == '':
            user_num_s = 0
        else:
            user_num_s = int(user_num_s)
        user_num_e = raw_input(fuser_menu_e)
        if user_num_e == '':
            user_num_e = 65536
        else:
            user_num_e = int(user_num_e)

    #FIXME: c12_18_optical_client.py: do_action_fmread: Query for table list first and then Standard/Manufacturer if not provided
    # Get Table Type information
    table_type = raw_input(table_menu)
    table_type = int(table_type)

    table_nums  = raw_input(mtable_menu)
    if table_nums.lower() == 'all':
        if table_type:
            table_nums = range(2040,2160)
        else:
            table_nums = range(170)
    else:
        table_nums  = table_nums.split(',')
        for e in range(len(table_nums)):
            table_nums[e] = int(table_nums[e])

    if table_type:
        print "Reading Manufacture Tables"
        if optic.ONF: optic.ONF.write("Reading Manufacture Tables\n")
    else:
        print "Reading Standard Tables"
        if optic.ONF: optic.ONF.write("Reading Standard Tables\n")

    # Time run for future efforts
    print "Multi-table Read with different users Start Time:",time.strftime('%X %x %Z')
    if optic.ONF: optic.ONF.write("Multi-table Read with different users Start Time: " + time.strftime('%X %x %Z') + "\n")

    if not optic.packet.login_setup(optic.SER_CONN0):
        print "Logon setup failed."
        return

    # Read all tables as one user at a time
    for user in range(user_num_s,user_num_e):
        # Setup meter connection
        print "Logged on as User: ",user
        if optic.ONF: optic.ONF.write("Logged on as User: " + str(user) + "\n")

        if not optic.packet.login_setup(optic.SER_CONN0):
            print "Logon setup failed."
            return

        # Logon
        if not optic.packet.login_seq_passwd(optic.SER_CONN0, user, optic.PASSWD):
            print "Logon setup failed."
            return

        # Loop thru tables
        for table_num in table_nums:
            # Read Table
            print "Reading Table:",table_num
            if optic.ONF: optic.ONF.write("Reading Table: " + str(table_num) + "\n")

            results = optic.packet.full_table_read(optic.SER_CONN0, table_num)
            if not results[0]:
                print "Read table failed."
                #continue
            else:
                print "Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>"
                if optic.ONF: optic.ONF.write("Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>\n")
                print "Table",table_num,"results:",bt.print_data(results[1])
                if optic.ONF: optic.ONF.write("Table " + str(table_num) + " results: " + bt.print_data(results[1]) + "\n")

        # Logoff
        #if not optic.packet.send_logoff(optic.SER_CONN0):
        if not optic.packet.send_terminate(optic.SER_CONN0):
            print "Logoff setup failed."
    
    # Stop and record time
    print "Multi-table Read with different users Stop Time:",time.strftime('%X %x %Z')
    if optic.ONF: optic.ONF.write("Multi-table Read with different users Stop Time: " + time.strftime('%X %x %Z') + "\n")

    # Return
    return
############################
# End Read multiple tables as different users
############################

############################
# Try a single table as different users
############################
def do_action_fsread(optic):
    '''
    Action: Read a single table as different users. User will provide a list of users
    or select all users which is user number 0 thru 15. User will also be prompted for
    the table to read.
    '''

    print "Running: Read Table as different users Function"
    if optic.ONF: optic.ONF.write("Running: Read Table as different users Function\n")

    # FIXME: c12_18_optical_client.py: do_action_fsread: User list can be handled better
    # Get a range of user numbers to use
    print fuser_menu
    user_num_s = raw_input(fuser_menu_s)
    if user_num_s == 'all':
        user_num_s = 0
        user_num_e = 15
    else:
        if user_num_s == '':
            user_num_s = 0
        else:
            user_num_s = int(user_num_s)
        user_num_e = raw_input(fuser_menu_e)
        if user_num_e == '':
            user_num_e = 65536
        else:
            user_num_e = int(user_num_e)

    print "\n   Enter Table Number: ",
    table_num  = raw_input(num_menu)
    table_num  = int(table_num)

    # Time run for future efforts
    print "Single Table Read as different users Start Time:",time.strftime('%X %x %Z')
    if optic.ONF: optic.ONF.write("Single Table Read as different users Start Time: " + time.strftime('%X %x %Z') + "\n")

    for user in range(user_num_s,user_num_e):
        # Setup meter connection
        print "Logging on as User: ",user
        if optic.ONF: optic.ONF.write("Logged on as User: " + str(user) + "\n")

        # Setup meter connection
        if not optic.packet.login_setup(optic.SER_CONN0):
            print "Logon setup failed."
            return

        # Logon and security code
        if not optic.packet.login_seq_passwd(optic.SER_CONN0, user, optic.PASSWD):
            print "Logon setup failed."
            return

        # Read Table
        print "Single Table Read as different users Reading Table:",table_num
        if optic.ONF: optic.ONF.write("Single Table Read as different users Reading Table: " + str(table_num) + "\n")

        results = optic.packet.full_table_read(optic.SER_CONN0, table_num)
        if not results[0]:
            print "Read table failed."
            #return
        else:
            print "Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>"
            if optic.ONF: optic.ONF.write("Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>\n")
            print "Table",table_num,"results:",bt.print_data(results[1])
            if optic.ONF: optic.ONF.write("Table" + str(table_num) + "results:" + bt.print_data(results[1]) + "\n")

        # Logoff
        #if not optic.packet.send_logoff(optic.SER_CONN0):
        if not optic.packet.send_terminate(optic.SER_CONN0):
            print "Logoff setup failed."
    
    # Stop and record time
    print "Stop Time:",time.strftime('%X %x %Z')
    if optic.ONF: optic.ONF.write("Stop Time: " + time.strftime('%X %x %Z') + "\n")

    # Return
    return
############################
# End Try a single table as different users
############################

############################
# Read all tables in a decade
############################
def do_action_dread(optic):
    '''
    Action: Read all of the tables is the user specified decade. Will attempt to read all 
    ten tables for the decade. This can be a Standard or a Manufacturer decade and is only
    dependant on the number provided by the user
    '''

    print "Running: Read decade Function"
    if optic.ONF: optic.ONF.write("Running: Read decade Function\n")

    # Get new user number or use default from configuration file
    user_num = raw_input(user_menu)
    if user_num == '':
        user_num = optic.USER_NUM
    else:
        user_num = int(user_num)
    print "Logging on as User: ",user_num
    if optic.ONF: optic.ONF.write("Logging on as User: " + str(user_num) + "\n")

    # Get decade to read
    print decade_menu
    table_nums = raw_input(num_menu)
    table_nums = int(table_nums) * 10

    # Setup meter connection
    if not optic.packet.login_setup(optic.SER_CONN0):
        print "Logon setup failed."
        return

    # Logon and send security code
    if not optic.packet.login_seq_passwd(optic.SER_CONN0, user_num, optic.PASSWD):
        print "Logon setup failed."
        return
    
    # Read Decade
    for table_num in range(table_nums,(table_nums + 10)):
        # Read each Table separately
        print "Reading Table:",table_num
        if optic.ONF: optic.ONF.write("Reading Table: " + str(table_num) + "\n")

        results = optic.packet.full_table_read(optic.SER_CONN0, table_num)
        if not results[0]:
            print "Read table failed."
            #return
        else:
            print "Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>"
            if optic.ONF: optic.ONF.write("Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>\n")
            print "Table",table_num,"results:",bt.print_data(results[1])
            if optic.ONF: optic.ONF.write("Table " + str(table_num) + " results: " + bt.print_data(results[1]) + "\n")

    # Logoff
    #if not optic.packet.send_logoff(optic.SER_CONN0):
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Logoff setup failed."

    # Return
    return
############################
# End Read all tables in a decade
############################

############################
# Run a procedure and get results
############################
def do_action_rproc(optic):
    '''
    Action: Runs the procedure specified by the user. Will request data to send to the procedure.
    Some procedures require specifically formatted data and some do not require any data. Data
    must be pre-formatted by the user and provided appropriately. Each procedure run will also be
    followed by a read from Table 8 to determine if the procedure provided any informaiton.
    '''

    print "Running: Run Procedure Function"
    if optic.ONF: optic.ONF.write("Running: Run Procedure Function\n")

    # Get new user number or use default from configuration file
    user_num = raw_input(user_menu)
    if user_num == '':
        user_num = optic.USER_NUM
    else:
        user_num = int(user_num)
    print "Logging on as User: ",user_num
    if optic.ONF: optic.ONF.write("Logging on as User: " + str(user_num) + "\n")

    # Get Procedure information
    print "\n    Select procedure number"
    proc_num  = raw_input(num_menu)
    proc_num  = int(proc_num)

    # Get data from user. MUST be formatted by user
    data_str  = raw_input(data_menu_default)
    if data_str:
        data_str  = bt.str2hex(data_str)
        print "Sending data:",bt.print_data(data_str)
        if optic.ONF: optic.ONF.write("Sending data: " + bt.print_data(data_str) + "\n")

    # Setup meter connection
    print "Logging on as User: ",user_num
    if optic.ONF: optic.ONF.write("Logging on as User: " + str(user_num) + "\n")
    if not optic.packet.login_setup(optic.SER_CONN0):
        print "Logon setup failed."
        return

    # Logon and send security code
    if not optic.packet.login_seq_passwd(optic.SER_CONN0, user_num, optic.PASSWD):
        print "Logon passwd failed."
        return

    # Run Procedure
    if not optic.packet.run_proc(optic.SER_CONN0, proc_num, data_str):
        print "Run procedure failed."
        return

    # Read results from Table 8
    read_table = 8
    results = optic.packet.full_table_read(optic.SER_CONN0, read_table)
    if not results[0]:
        print "Read procedure results failed."
        return
    else:
        print "Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>"
        if optic.ONF: optic.ONF.write("Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>\n")
        print "Procedure ",proc_num," results: ",bt.print_data(results[1])
        if optic.ONF: optic.ONF.write("Procedure" + str(proc_num) + "results:" + bt.print_data(results[1]) + "\n")

    # Logoff
    #if not optic.packet.send_logoff(optic.SER_CONN0):
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Logoff setup failed."

    # Return
    return
############################
# End Run a procedure and get results
############################

############################
# Run multiple procedures
############################
def do_action_mproc(optic):
    '''
    Action: Runs multiple procedures specified by the user. Will request data to send to each procedure.
    Some procedures require specifically formatted data and some do not require any data. Data
    must be pre-formatted by the user and provided appropriately. Each procedure run will also be
    followed by a read from Table 8 to determine if the procedure provided any informaiton.
    '''

    print "Running: Run Multiple Procedures Function"
    if optic.ONF: optic.ONF.write("Running: Run Multiple Procedures Function\n")

    # Get new user number or use default from configuration file
    user_num = raw_input(user_menu)
    if user_num == '':
        user_num = optic.USER_NUM
    else:
        user_num = int(user_num)
    print "Logging on as User: ",user_num
    if optic.ONF: optic.ONF.write("Logging on as User: " + str(user_num) + "\n")

    # Get Procedure information
    proc_type = raw_input(proc_menu)
    proc_type = int(proc_type)
    if proc_type:
        print "Running against Manufacture Procedures"
        if optic.ONF: optic.ONF.write("Running against Manufacture Procedures\n")
        base = c12packet.MFG_PROC_BASE
    else:
        print "Running against Standard Procedures"
        if optic.ONF: optic.ONF.write("Running against Standard Procedures\n")
        base = c12packet.STD_PROC_BASE

    # All Procedures
    if not base:
        # Standard Procs
        proc_nums = range(c12packet.STD_PROC_SIZE)
    else:
        # Manufacturer Procs
        proc_nums = range(base,base+c12packet.MFG_PROC_SIZE)

    data_str  = raw_input(data_menu_default)

    # Get data from user. MUST be formatted by user if necessary
    if data_str:
        data_str  = bt.str2hex(data_str)
        print "Sending data:",bt.print_data(data_str)

    # Setup meter connection
    if not optic.packet.login_setup(optic.SER_CONN0):
        print "Logon setup failed."
        return

    # Logon and send security code
    if not optic.packet.login_seq_passwd(optic.SER_CONN0, user_num, optic.PASSWD):
        print "Logon setup failed."
        return

    # Loop thru procedures
    for proc_num in proc_nums:
        # Run Procedure
        print "Running Procedure:",proc_num
        if optic.ONF: optic.ONF.write("Running Procedure: " + str(proc_num) + "\n")
        if not optic.packet.run_proc(optic.SER_CONN0, proc_num, data_str):
            print "Run procedure failed."
            # Keep going
            continue

        # Read results from Table 8
        read_table = 8
        results = optic.packet.full_table_read(optic.SER_CONN0, read_table)
        if not results[0]:
            print "Read procedure results failed."
            # Keep going
            continue
        else:
            print "Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>"
            if optic.ONF: optic.ONF.write("Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>\n")
            print "Procedure",proc_num,"results:",bt.print_data(results[1])
            if optic.ONF: optic.ONF.write("Procedure " + str(proc_num) + " results: " + bt.print_data(results[1]) + "\n")

    # Logoff
    #if not optic.packet.send_logoff(optic.SER_CONN0):
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Logoff setup failed."

    # Return
    return
############################
# End Run multiple procedures
############################

############################
# Run multiple procedures without login
############################
def do_action_mproc_nl(optic):
    '''
    Action: Runs multiple procedures without logon with good security code.
    Will request data to send to each procedure. Some procedures require specifically 
    formatted data and some do not require any data. Data must be pre-formatted by 
    the user and provided appropriately. Each procedure run will also be followed by 
    a read from Table 8 to determine if the procedure provided any informaiton.
    '''

    print "Running: Run Multiple Procedures Function"
    if optic.ONF: optic.ONF.write("Running: Run Multiple Procedures Function\n")

    # Get new user number or use default from configuration file
    user_num = raw_input(user_menu)
    if user_num == '':
        user_num = optic.USER_NUM
    else:
        user_num = int(user_num)
    print "Logging on as User: ",user_num
    if optic.ONF: optic.ONF.write("Logging on as User: " + str(user_num) + "\n")

    # Get Procedure information
    proc_type = raw_input(proc_menu)
    proc_type = int(proc_type)
    if proc_type:
        print "Running against Manufacture Procedures"
        if optic.ONF: optic.ONF.write("Running against Manufacture Procedures\n")
        base = c12packet.MFG_PROC_BASE
    else:
        print "Running against Standard Procedures"
        if optic.ONF: optic.ONF.write("Running against Standard Procedures\n")
        base = c12packet.STD_PROC_BASE

    # All Procedures
    if not base:
        # Standard Procs
        proc_nums = range(c12packet.STD_PROC_SIZE)
    else:
        # Manufacturer Procs
        proc_nums = range(base,base+c12packet.MFG_PROC_SIZE)

    data_str  = raw_input(data_menu_default)

    if data_str:
        data_str  = bt.str2hex(data_str)
        print "Sending data:",bt.print_data(data_str)

    # Setup meter connection
    if not optic.packet.login_setup(optic.SER_CONN0):
        print "Logon setup failed."
        return

    # Skipping logon to detect any procedures that can be run
    # without logging on
    # Logon
    #if not optic.packet.login_seq_passwd(optic.SER_CONN0, user_num, optic.PASSWD):
        #print "Logon setup failed."
        #return

    # Run selected procedures
    for proc_num in proc_nums:
        # Run Procedure
        print "Running Procedure:",proc_num
        if optic.ONF: optic.ONF.write("Running Procedure: " + str(proc_num) + "\n")
        if not optic.packet.run_proc(optic.SER_CONN0, proc_num, data_str):
            print "Run procedure failed."
            # Keep going
            continue
        else:
            print "Successfully Ran Procedure Without Providing Password"
            if optic.ONF: optic.ONF.write("\n\nSuccessfully Ran Procedure Without Providing Password\n\n")

        # Read results from Table 8
        read_table = 8
        results = optic.packet.full_table_read(optic.SER_CONN0, read_table)
        if not results[0]:
            print "Read procedure results failed."
            # Keep going
            continue
        else:
            print "Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>"
            if optic.ONF: optic.ONF.write("Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>\n")
            print "Procedure",proc_num,"results:",bt.print_data(results[1])
            if optic.ONF: optic.ONF.write("Procedure " + str(proc_num) + " results: " + bt.print_data(results[1]) + "\n")

    # Logoff
    #if not optic.packet.send_logoff(optic.SER_CONN0):
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Logoff setup failed."

    # Return
    return
############################
# End Run multiple procedures without login
############################
    
############################
# Write data to a table
############################
def do_action_wtable(optic):
    '''
    Action: Write to a table. User will provide data. Data must be formatted properly
    if needing to write to a specific offset. This function starts with a read of the
    specified table to determine initial content and finishes with a table read to 
    show success or failure. The full_table_write will compute data information such 
    as length and data CRC.
    '''

    print "Running: Write to Table Function"
    if optic.ONF: optic.ONF.write("Running: Write to Table Function\n")

    # Get new user number or use default from configuration file
    user_num = raw_input(user_menu)
    if user_num == '':
        user_num = optic.USER_NUM
    else:
        user_num = int(user_num)
    print "Logging on as User: ",user_num
    if optic.ONF: optic.ONF.write("Logging on as User: " + str(user_num) + "\n")

    # Get Table information
    print "   Enter Table Number: "
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
    print "Reading Table Before Change:",table_num
    if optic.ONF: optic.ONF.write("Reading Table Before Change: " + str(table_num) + "\n")

    results = optic.packet.full_table_read(optic.SER_CONN0, table_num)
    if not results[0]:
        print "Read table failed."
        return
    else:
        print "Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>"
        if optic.ONF: optic.ONF.write("Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>\n")
        print "Table ",table_num," results: ",bt.print_data(results[1])
        if optic.ONF: optic.ONF.write("Table " + str(table_num) + " results: " + bt.print_data(results[1]) + "\n")

    # Parsed Data - incoming values [data[:1], length, data[3:(3 + length)], data[-1:]]
    r_response, data_len, r_data, r_crc = optic.packet.parse_rtn_data(results[1])
    print "The following table data has been parsed to only include the table data."
    if optic.ONF: optic.ONF.write("The following table data has been parsed to only include the table data.\n")
    print "It DOES NOT contain the response byte, data length, or data crc."
    if optic.ONF: optic.ONF.write("It DOES NOT contain the response byte, data length, or data crc.\n")
    print "Use the following data to maintain basic table integrity."
    if optic.ONF: optic.ONF.write("Use the following data to maintain basic table integrity.\n")
    print "Only modify the specific bytes that need to be updated."
    if optic.ONF: optic.ONF.write("Only modify the specific bytes that need to be updated.\n")
    print "Be sure to manage the Endian-ness of each element properly."
    if optic.ONF: optic.ONF.write("Be sure to manage the Endian-ness of each element properly.\n")

    print "\nParsed Table Data:",bt.print_data(r_data),"\n"
    if optic.ONF: optic.ONF.write("\nParsed Table Data: " + bt.print_data(r_data) + "\n\n")

    # Of course, this all takes time and the session may time out
    # Log out and then back in to handle gracefully
    # Logoff
    #if not optic.packet.send_logoff(optic.SER_CONN0):
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Logoff setup failed."

    # Now get data to write
    # This makes it easy for the user to cut and paste the original
    # values and just modify what they want.
    # We do this to avoid issues with data element size which could
    # vary from table to table and affect partial writes to offsets.

    # Get data to write
    data_str  = raw_input(data_menu_no_default)
    if not data_str:
        return
    data_str  = bt.str2hex(data_str)

    # Setup meter connection
    if not optic.packet.login_setup(optic.SER_CONN0):
        print "Logon setup failed."
        return

    # Logon
    if not optic.packet.login_seq_passwd(optic.SER_CONN0, user_num, optic.PASSWD):
        print "Logon setup failed."
        return
    
    print "Writing",bt.print_data(data_str)
    if optic.ONF: optic.ONF.write("Writing " + bt.print_data(data_str))

    results = optic.packet.full_table_write(optic.SER_CONN0, table_num,data_str)
    if not results[0]:
        print "Write table failed."
        return
    else:
        print "Write table successful."
        if optic.ONF: optic.ONF.write( "Write table successful.\n")

    # Read Table
    print "Reading Table After Change:",table_num
    if optic.ONF: optic.ONF.write("Reading Table After Change: " + str(table_num) + "\n")

    results = optic.packet.full_table_read(optic.SER_CONN0, table_num)
    if not results[0]:
        print "Read table failed."
        return
    else:
        print "Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>"
        if optic.ONF: optic.ONF.write("Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>\n")
        print "Table",table_num,"results: ",bt.print_data(results[1])
        if optic.ONF: optic.ONF.write("Table " + str(table_num) + " results: " + bt.print_data(results[1]) + "\n")

    # Parsed Data - incoming values [data[:1], length, data[3:(3 + length)], data[-1:]]
    r_response, data_len, r_data, r_crc = optic.packet.parse_rtn_data(results[1])

    print "\nParsed Table Data:",bt.print_data(r_data),"\n"
    if optic.ONF: optic.ONF.write("\nParsed Table Data: " + bt.print_data(r_data) + "\n\n")

    # Logoff
    #if not optic.packet.send_logoff(optic.SER_CONN0):
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Logoff setup failed."

    # Return
    return
############################
# End Write data to a table
############################
    
############################
# Brute force the security password
############################
def do_action_brute(optic):
    '''
    Action: Brute Force login. This function takes security codes from a file and
    runs through each until a successful login is detected. Each login attempt will
    take approximately two seconds. This process should be monitored to determine if
    it is functioning properly.

    NOTE: Some meters return login success for any security code provided. These types
    of meters check level of access provided by the security code. In these cases,
    use the alternate brute forcing function which detects success by reading a
    restricted table.
    '''

    #global PASSWD_FILE
    print "Running: Brute Force Security Password Function"
    if optic.ONF: optic.ONF.write("Running: Brute Force Security Password Function\n")

    # Get new user number or use default from configuration file
    user_num = raw_input(user_menu)
    if user_num == '':
        user_num = optic.USER_NUM
    else:
        user_num = int(user_num)
    print "Brute forcing as User: ",user_num
    if optic.ONF: optic.ONF.write("Brute forcing as User: " + str(user_num) + "\n")

    file_name = raw_input(file_menu)
    if file_name:
        passwd_file = file_name
    else:
        passwd_file = optic.PASSWD_FILE

    # Open file and grab contents 21 bytes at a time
    # Strip new line character off end and use raw bytes
    # as the password
    passwds = [binascii.a2b_hex(l.strip()) for l in open(passwd_file,'rb')]

    # Setup meter connection
    if not optic.packet.login_setup(optic.SER_CONN0):
        print "Logon setup failed."
        return

    # Logon
    if not optic.packet.login_user(optic.SER_CONN0, user_num):
        print "Logon setup failed."
        return

    # Roll thru security codes
    for passwd in passwds:
        # Send security code
        if optic.packet.login_passwd(optic.SER_CONN0, optic.PASSWD):
            print "Logon successful using:",bt.print_data(optic.PASSWD)
            if optic.ONF: optic.ONF.write("Logon successful using: " + bt.print_data(optic.PASSWD) + "\n")

            # Logoff
            #if not optic.packet.send_logoff(optic.SER_CONN0):
            if not optic.packet.send_terminate(optic.SER_CONN0):
                print "Logoff failed."

            break

        print "Logon failed using:",bt.print_data(optic.PASSWD)
        c12packet.delay(c12packet.logon_pause)

    print "Brute force logon sequence completed."
    if optic.ONF: optic.ONF.write("Brute force logon sequence completed.\n")

    # Return
    return
############################
# End Brute force the security password
############################

############################
# Alternate Brute force the security password
############################
def do_action_alt_brute(optic):
    '''
    Action: Alternate Brute Force login. This function takes security codes from a file and
    runs through each until a successful login is detected. Each login attempt will
    take approximately two seconds. This process should be monitored to determine if
    it is functioning properly.

    NOTE: Some meters return login success for any security code provided. These types
    of meters check level of access provided by the security code. In these cases,
    use the alternate brute forcing function which detects success by reading a
    restricted table.
    '''

    #global PASSWD_FILE

    print "Running: Alternate Brute Force Security Password Function"
    if optic.ONF: optic.ONF.write("Running: Alternate Brute Force Security Password Function\n")

    # Get new user number or use default from configuration file
    user_num = raw_input(user_menu)
    if user_num == '':
        user_num = optic.USER_NUM
    else:
        user_num = int(user_num)
    print "Brute forcing as User: ",user_num
    if optic.ONF: optic.ONF.write("Brute forcing as User: " + str(user_num) + "\n")

    file_name = raw_input(file_menu)
    if file_name:
        passwd_file = file_name
    else:
        passwd_file = optic.PASSWD_FILE

    # Open file and grab contents 21 bytes at a time
    # Strip new line character off end and use raw bytes
    # as the password
    passwds = [binascii.a2b_hex(l.strip()) for l in open(passwd_file,'rb')]

    # Setup meter connection
    if not optic.packet.login_setup(optic.SER_CONN0):
        print "Logon setup failed."
        return

    # Logon
    if not optic.packet.login_user(optic.SER_CONN0, user_num):
        print "Logon setup failed."
        return

    # Roll thru security code list
    for passwd in passwds:
        # Send security code
        if optic.packet.login_passwd(optic.SER_CONN0, optic.PASSWD):

            # For Alternate Brute Force we need to test
            # successful logins by reading a restricted table
            table_num = 45

            # Read Table
            #print "Reading Table:",table_num
            #if optic.ONF: optic.ONF.write("Reading Table: " + str(table_num) + "\n")

            results = optic.packet.full_table_read(optic.SER_CONN0, table_num)
            if not results[0]:
                #print "Read table failed."
                print "Logon failed using:",bt.print_data(optic.PASSWD)
                c12packet.delay(c12packet.logon_pause)
                continue
            else:
                print "Logon successful using:",bt.print_data(optic.PASSWD)
                if optic.ONF: optic.ONF.write("Logon successful using: " + bt.print_data(optic.PASSWD) + "\n")

                # Logoff
                #if not optic.packet.send_logoff(optic.SER_CONN0):
                if not optic.packet.send_terminate(optic.SER_CONN0):
                    print "Logoff failed."

                break

    print "Alternate Brute Force logon sequence completed."
    if optic.ONF: optic.ONF.write("Alternate Brute Force logon sequence completed.\n")

    # Return
    return
############################
# End Alternate Brute force the security password
############################

############################
# Run through all user ids to see if they can be used
############################
def do_action_userid(optic):
    '''
    DEPRECATED
    Action: Brute Force User ID. This function is deprecated but has been left in
    in to help build User ID fuzzing functionality if it is ever desired.
    '''

    print "Running: Brute Force User ID Function"
    if optic.ONF: optic.ONF.write("Running: Brute Force User ID Function\n")

    name_data = raw_input(userid_menu)

    # Convert name to hex
    user_name = ""
    for x in range(len(name_data)):
        user_name += bt.str2hex("%.02x"%ord(name_data[x]))
    if len(user_name) > 10:
        user_name = user_name[:10]
    elif len(user_name) < 10:
        user_name += '\x20' * (10 - len(user_name))
    
    print "Walking User-ids as User: ",bt.print_data(user_name)
    if optic.ONF: optic.ONF.write("Walking User-ids as User: " + bt.print_data(user_name) + "\n")

    # Setup meter connection
    if not optic.packet.login_setup(optic.SER_CONN0):
        print "Logon setup failed."
        return

    # Roll through user numbers for each username
    for e in range(65):
        # Send security code
        if not optic.packet.login_user(optic.SER_CONN0, e, user_name):
            print "Logon setup failed."
            sys.exit()
        else:
            print "Logon successful for User Number:",e
            if optic.ONF: optic.ONF.write("Logon successful for User Number: " + str(e) + "\n")

            # Logoff
            #if not optic.packet.send_logoff(optic.SER_CONN0):
            if not optic.packet.send_terminate(optic.SER_CONN0):
                print "Logoff failed."

            # Setup meter connection
            if not optic.packet.login_setup(optic.SER_CONN0):
                print "Logon setup failed."
                return

        c12packet.delay(c12packet.logon_pause)

    print "Brute force User ID completed."
    if optic.ONF: optic.ONF.write("Brute force User ID completed.\n")

    # Return
    return
############################
# End Run through all user ids to see if they can be used
############################

############################
# Parse the modify Table 13 Demand Control Table
############################
def do_action_twrite13(optic):
    '''
    Action: Modify Table 13 Demand Control Table. This function is used to demonstrate
    proof of concept that meter table data can be modified. Table 11 is read to determine
    how the meter is configured. Table 13 is then displayed for the user and new data is
    requested. Table 13 is then modified, read again, and the updated data is displayed
    to the user.
    '''

    print "Running: Modify Table 13 Demand Control Table Function"
    if optic.ONF: optic.ONF.write("Running: Modify Table 13 Demand Control Table Function\n")

    # Get new user number or use default from configuration file
    user_num = raw_input(user_menu)
    if user_num == '':
        user_num = optic.USER_NUM
    else:
        user_num = int(user_num)
    print "Logging on as User: ",user_num
    if optic.ONF: optic.ONF.write("Logging on as User: " + str(user_num) + "\n")

    # Get Table 11 information
    table_num  = 11     # Table 11 Actual Data Sources Limiting Table is Table 01

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
    if optic.ONF: optic.ONF.write("Reading Table: " + str(table_num) + "\n")

    results = optic.packet.full_table_read(optic.SER_CONN0, table_num)
    if not results[0]:
        print "Read table failed."
        return
    else:
        print "Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>"
        if optic.ONF: optic.ONF.write("Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>\n")
        print "Table ",table_num," results: ",bt.print_data(results[1])
        if optic.ONF: optic.ONF.write("Table " + str(table_num) + " results: " + bt.print_data(results[1]) + "\n")

    # Logoff early because we are just parsing from here
    #if not optic.packet.send_logoff(optic.SER_CONN0):
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Logoff setup failed."

    # Parsed Data - incoming values [data[:1], length, data[3:(3 + length)], data[-1:]]
    r_response, data_len, r_data, r_crc = optic.packet.parse_rtn_data(results[1])

    print "\nParsed Table 11 Actual Data Sources Limiting Table Data:",bt.print_data(r_data),"\n"
    if optic.ONF: optic.ONF.write("\nParsed Table 11 Actual Data Sources Limiting Table Data: " + bt.print_data(r_data) + "\n\n")

    # Sort returned data
    source_flags_bfld = r_data[0]

    # Get Table 11 information
    table_num  = 13      # Table 13 Demand Control Table

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
    if optic.ONF: optic.ONF.write("Reading Table: " + str(table_num) + "\n")

    results = optic.packet.full_table_read(optic.SER_CONN0, table_num)
    if not results[0]:
        print "Read table failed."
        return
    else:
        print "Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>"
        if optic.ONF: optic.ONF.write("Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>\n")
        print "Table ",table_num," results: ",bt.print_data(results[1])
        if optic.ONF: optic.ONF.write("Table " + str(table_num) + " results: " + bt.print_data(results[1]) + "\n")

    # Logoff early because we are just parsing from here
    #if not optic.packet.send_logoff(optic.SER_CONN0):
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Logoff setup failed."

    # Parsed Data - incoming values [data[:1], length, data[3:(3 + length)], data[-1:]]
    r_response, data_len, r_data, r_crc = optic.packet.parse_rtn_data(results[1])

    print "\nParsed Table 13 Demand Control Table Data:",bt.print_data(r_data),"\n"
    if optic.ONF: optic.ONF.write("\nParsed Table 13 Demand Control Table Data: " + bt.print_data(r_data) + "\n\n")

    if source_flags_bfld:
        sub_int        = r_data[0]
        int_multiplier = r_data[1]
        print 'Minutes in subinterval',bt.print_data(sub_int)
        if optic.ONF: optic.ONF.write("\nMinutes in subinterval: " + bt.print_data(sub_int) + "\n\n")
        print 'Sub_Int Multiplier',bt.print_data(int_multiplier)
        if optic.ONF: optic.ONF.write("\nSub_Int Multiplier: " + bt.print_data(int_multiplier) + "\n\n")
    else:
        int_length     = r_data[0:2]
        print 'Minutes in demand interval',bt.print_data(int_length)
        if optic.ONF: optic.ONF.write("\nMinutes in demand interval: " + bt.print_data(int_length) + "\n\n")

    # Get data to write
    new_data = list(r_data)
    if source_flags_bfld:
        print "    Enter minutes in subinterval. Value 0 - 255. Hit enter to keep original value."
        sub_data_str  = raw_input(data_menu_default)
        if sub_data_str:
            new_data[0]  = bt.str2hex(sub_data_str)
        print "    Enter Sub_Int Multiplier. Value 0 - 255. Hit enter to keep original value."
        int_data_str  = raw_input(data_menu_default)
        if int_data_str:
            new_data[1]  = bt.str2hex(int_data_str)
        new_data = ''.join(new_data)
    else:
        print "    Enter minutes in demand interval. Value 0 - 65535. Hit enter to keep original value."
        data_str  = raw_input(data_menu_default)
        if data_str:
            data_str  = bt.str2hex(data_str)
            new_data[0] = data_str[0]
            new_data[1] = data_str[1]
        else:
            return
        new_data = ''.join(new_data)

    # Setup meter connection
    if not optic.packet.login_setup(optic.SER_CONN0):
        print "Logon setup failed."
        return

    # Logon and send security code
    if not optic.packet.login_seq_passwd(optic.SER_CONN0, user_num, optic.PASSWD):
        print "Logon setup failed."
        return
    
    print "Writing",bt.print_data(new_data)
    if optic.ONF: optic.ONF.write("\nWriting " + bt.print_data(new_data) + "\n\n")

    results = optic.packet.full_table_write(optic.SER_CONN0, table_num,new_data)
    if not results[0]:
        print "Write table failed."
        if optic.ONF: optic.ONF.write( "\nWrite table failed.\n")
        return
    else:
        print "Write table successful."
        if optic.ONF: optic.ONF.write( "\nWrite table successful.\n")

    # Read Table
    print "Reading Table:",table_num
    if optic.ONF: optic.ONF.write("\nReading Table: " + str(table_num) + "\n")

    results = optic.packet.full_table_read(optic.SER_CONN0, table_num)
    if not results[0]:
        print "Read table failed."
        return
    else:
        print "Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>"
        if optic.ONF: optic.ONF.write("\nData Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>\n")
        print "Table ",table_num," results: ",bt.print_data(results[1])
        if optic.ONF: optic.ONF.write("\nTable " + str(table_num) + " results: " + bt.print_data(results[1]) + "\n")

    # Logoff early because we are just parsing from here
    # Logoff
    #if not optic.packet.send_logoff(optic.SER_CONN0):
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Logoff setup failed."

    # Parsed Data - incoming values [data[:1], length, data[3:(3 + length)], data[-1:]]
    r_response, data_len, r_data, r_crc = optic.packet.parse_rtn_data(results[1])

    print "\nParsed Table 13 Demand Control Table Data:",bt.print_data(r_data),"\n"
    if optic.ONF: optic.ONF.write("\nParsed Table 13 Demand Control Table Data: " + bt.print_data(r_data) + "\n\n")

    if source_flags_bfld:
        sub_int        = r_data[0]
        int_multiplier = r_data[1]
        print 'Minutes in subinterval',bt.print_data(sub_int)
        if optic.ONF: optic.ONF.write("\nMinutes in subinterval: " + bt.print_data(sub_int) + "\n\n")
        print 'Sub_Int Multiplier',bt.print_data(int_multiplier)
        if optic.ONF: optic.ONF.write("\nSub_Int Multiplier: " + bt.print_data(int_multiplier) + "\n\n")
    else:
        int_length     = r_data[0:2]
        print 'Minutes in demand interval',bt.print_data(int_length)
        if optic.ONF: optic.ONF.write("\nMinutes in demand interval: " + bt.print_data(int_length) + "\n\n")

    # Return
    return
############################
# End Parse the modify Table 13 Demand Control Table
############################

############################
# Run a procedure to use the Direct Load Control procedure to turn the meter off
############################
# FIXME: c12_18_optical_client.py: do_action_tmeterld0: Consolidate this with do_action_tmeterld100
def do_action_tmeterld0(optic):
    '''
    Action: Set Direct Load Control to 0%. This function will run Standard Procedure 21
    and set the load control to 0%. In some cases this will disconnect the meter. If
    successful the meter will emit an audible click.
    '''

    print "Running: Set Meter Direct Load Control to 0%"
    if optic.ONF: optic.ONF.write("Running: Set Meter Direct Load Control to 0%\n")

    # Get new user number or use default from configuration file
    user_num = raw_input(user_menu)
    if user_num == '':
        user_num = optic.USER_NUM
    else:
        user_num = int(user_num)
    print "Logging on as User: ",user_num
    if optic.ONF: optic.ONF.write("Logging on as User: " + str(user_num) + "\n")

    # Get Table information
    table_num  = 111     

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
    if optic.ONF: optic.ONF.write("Reading Table: " + str(table_num) + "\n")

    results = optic.packet.full_table_read(optic.SER_CONN0, table_num)
    if not results[0]:
        print "Read table failed."
        return
    else:
        print "Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>"
        if optic.ONF: optic.ONF.write("Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>\n")
        print "Table ",table_num," results: ",bt.print_data(results[1])
        if optic.ONF: optic.ONF.write("Table " + str(table_num) + " results: " + bt.print_data(results[1]) + "\n")

    # Logoff early because we are just parsing from here
    #if not optic.packet.send_logoff(optic.SER_CONN0):
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Logoff setup failed."

    # Parsed Data - incoming values [data[:1], length, data[3:(3 + length)], data[-1:]]
    r_response, data_len, r_data, r_crc = optic.packet.parse_rtn_data(results[1])

    print "\nParsed Configuration Table Data:",bt.print_data(r_data),"\n"
    if optic.ONF: optic.ONF.write("\nParsed Configuration Table Data: " + bt.print_data(r_data) + "\n\n")

    # Sort returned data
    # First byte of DIM_LOAD_CONTROL_BFLD is all we need
    if (ord(r_data[0]) & 1):
        print "Meter uses duration for determining time settings"
        if optic.ONF: optic.ONF.write("\nMeter uses duration for determining time settings\n")
    else:
        print "Meter uses randomination for determining time settings"
        if optic.ONF: optic.ONF.write("\nMeter uses randomination for determining time settings\n")
    num_cntp      = r_data[2] # The NBR_OF_CONTROL_POINTS

    # Run Procedure
    proc_num = 21
    level    = '\x64'    # 100% off, Yes, this is weird, but it is how it is done
    cnt_pnts = struct.pack('B',((ord(num_cntp) + 7) / 8))

    # FIXME: c12_18_optical_client.py: do_action_tmeterld0: Test and implement delays correctly
#    print "    The following delays may not work as expected. This is included for testing."
#    print "    Press enter for the following values to use the default of 0. All 0's make the change perminate."
#    hours = raw_input('    Enter hours (0-23): ')
#    if not hours:
#        hours = 0
#    else:
#        hours = int(hours)
#        if hours > 23:
#            hours = 23
#    mins = raw_input('    Enter minutes (0-59): ')
#    if not mins:
#        mins = 0
#    else:
#        mins = int(mins)
#        if mins > 59:
#            mins = 59
#    secs = raw_input('    Enter seconds (0-59): ')
#    if not secs:
#        secs = 0
#    else:
#        secs = int(secs)
#        if secs > 59:
#            secs = 59
#    print "Meter will turn off for",hours,"hours and",mins,"minutes and",secs,"seconds"
#    if optic.ONF: optic.ONF.write("\nMeter will turn off for " + str(hours) + " hours and " + str(mins) + " minutes and " + str(secs) + " seconds\n\n")

    hours = 0
    mins = 0
    secs = 0

    data_str  = level + cnt_pnts
    for e in (hours, mins, secs):
        data_str += struct.pack('B',e)

    print "Running Toggle Meter Off"
    if optic.ONF: optic.ONF.write("Running Toggle Meter Off" + "\n")

    print "Sending data:",bt.print_data(data_str)
    if optic.ONF: optic.ONF.write("Sending data: " + bt.print_data(data_str) + "\n")
    
    # Setup meter connection
    print "Logging on as User: ",user_num

    # Setup meter connection
    if not optic.packet.login_setup(optic.SER_CONN0):
        print "Logon setup failed."
        return

    # Logon and send security code
    if not optic.packet.login_seq_passwd(optic.SER_CONN0, user_num, optic.PASSWD):
        print "Logon passwd failed."
        return

    # Run Procedure
    if not optic.packet.run_proc(optic.SER_CONN0, proc_num, data_str):
        print "Run procedure failed."
        return

    # Logoff
    #if not optic.packet.send_logoff(optic.SER_CONN0):
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Logoff setup failed."

    # Return
    return
############################
# End Run a procedure to use the Direct Load Control procedure to turn the meter off
############################
    
############################
# Run a procedure to use the Direct Load Control procedure to turn the meter on
############################
# FIXME: c12_18_optical_client.py: do_action_tmeterld100: Consolidate this with do_action_tmeterld0
def do_action_tmeterld100(optic):
    '''
    Action: Set Direct Load Control to 100%. This function will run Standard Procedure 21
    and set the load control to 100%. In some cases this will connect the meter. If
    successful the meter will emit an audible click.
    '''

    print "Running: Set Meter Direct Load Control to 100%"
    if optic.ONF: optic.ONF.write("Running: Set Meter Direct Load Control to 100%\n")

    # Get new user number or use default from configuration file
    user_num = raw_input(user_menu)
    if user_num == '':
        user_num = optic.USER_NUM
    else:
        user_num = int(user_num)
    print "Logging on as User: ",user_num
    if optic.ONF: optic.ONF.write("Logging on as User: " + str(user_num) + "\n")

    # Get Table information
    table_num  = 111      # Configuration Table is Table 00

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
    if optic.ONF: optic.ONF.write("Reading Table: " + str(table_num) + "\n")

    results = optic.packet.full_table_read(optic.SER_CONN0, table_num)
    if not results[0]:
        print "Read table failed."
        return
    else:
        print "Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>"
        if optic.ONF: optic.ONF.write("Data Format: <OK - 1 byte><Data length - 2 bytes><Data><Data CRC - 1 byte>\n")
        print "Table ",table_num," results: ",bt.print_data(results[1])
        if optic.ONF: optic.ONF.write("Table " + str(table_num) + " results: " + bt.print_data(results[1]) + "\n")

    # Logoff early because we are just parsing from here
    #if not optic.packet.send_logoff(optic.SER_CONN0):
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Logoff setup failed."

    # Parsed Data - incoming values [data[:1], length, data[3:(3 + length)], data[-1:]]
    r_response, data_len, r_data, r_crc = optic.packet.parse_rtn_data(results[1])

    print "\nParsed Configuration Table Data:",bt.print_data(r_data),"\n"
    if optic.ONF: optic.ONF.write("\nParsed Configuration Table Data: " + bt.print_data(r_data) + "\n\n")

    # Sort returned data
    # First byte of DIM_LOAD_CONTROL_BFLD is all we need
    if (ord(r_data[0]) & 1):
        print "Meter uses duration for determining time settings"
        if optic.ONF: optic.ONF.write("\nMeter uses duration for determining time settings\n")
    else:
        print "Meter uses randomination for determining time settings"
        if optic.ONF: optic.ONF.write("\nMeter uses randomination for determining time settings\n")
    num_cntp      = r_data[2] # The NBR_OF_CONTROL_POINTS

    proc_num = 21
    level    = '\x00' # 0% off, Yes, this is weird, but it is how it is done
    cnt_pnts = struct.pack('B',((ord(num_cntp) + 7) / 8))

    # FIXME: c12_18_optical_client.py: do_action_tmeterld100: Test and implement delays correctly
#    print "    The following delays may not work as expected. This is included for testing."
#    print "    Press enter for the following values to use the default of 0. All 0's make the change perminate."
#    hours = raw_input('    Enter hours (0-23): ')
#    if not hours:
#        hours = 0
#    else:
#        hours = int(hours)
#        if hours > 23:
#            hours = 23
#    mins = raw_input('    Enter minutes (0-59): ')
#    if not mins:
#        mins = 0
#    else:
#        mins = int(mins)
#        if mins > 59:
#            mins = 59
#    secs = raw_input('    Enter seconds (0-59): ')
#    if not secs:
#        secs = 0
#    else:
#        secs = int(secs)
#        if secs > 59:
#            secs = 59
#    print "Meter will turn on for",hours,"hours and",mins,"minutes and",secs,"seconds"
#    if optic.ONF: optic.ONF.write("\nMeter will turn on for " + str(hours) + " hours and " + str(mins) + " minutes and " + str(secs) + " seconds\n\n")

    hours = 0
    mins = 0
    secs = 0

    data_str = level + cnt_pnts
    for e in (hours, mins, secs):
        data_str += struct.pack('B',e)

    print "Running Toggle Meter Off"
    if optic.ONF: optic.ONF.write("Running Toggle Meter Off\n")

    print "Sending data:",bt.print_data(data_str)
    if optic.ONF: optic.ONF.write("Sending data: " + bt.print_data(data_str) + "\n")

    # Setup meter connection
    print "Logging on as User: ",user_num
    if optic.ONF: optic.ONF.write("Logging on as User: " + str(user_num) + "\n")

    # Setup meter connection
    if not optic.packet.login_setup(optic.SER_CONN0):
        print "Logon setup failed."
        return

    # Logon and send security code
    if not optic.packet.login_seq_passwd(optic.SER_CONN0, user_num, optic.PASSWD):
        print "Logon passwd failed."
        return

    # Run Procedure
    if not optic.packet.run_proc(optic.SER_CONN0, proc_num, data_str):
        print "Run procedure failed."
        return

    # Logoff
    #if not optic.packet.send_logoff(optic.SER_CONN0):
    if not optic.packet.send_terminate(optic.SER_CONN0):
        print "Logoff setup failed."

    # Return
    return
############################
# End Run a procedure to use the Direct Load Control procedure to turn the meter on
############################

############################
# Fuzz Security Code
############################
def do_action_fuzz_sec(optic):
####STOPPED####
    '''
    Action: Fuzz C12.18 Security Code. This function will attempt to send malformed
    C12.18 Security Codes to see if the meter responds differently when provided
    with unexpected data.

    NOTE: Some meters return login success for any security code provided. These types
    of meters check level of access provided by the security code. In these cases,
    use the alternate fuzzing security code function which detects success by reading a
    restricted table.
    '''

    print "Running: Fuzz Security Code Function"
    if optic.ONF: optic.ONF.write("Running: Fuzz Security Code function\n")
    print "Current password: ",bt.print_data(optic.PASSWD)
    if optic.ONF: optic.ONF.write("Current password: " + bt.print_data(optic.PASSWD) + "\n\n")

    # Passwords can be provided using an external file.
    
    #global PASSWDS
    passwds = []
    fpasswds = []

    # Check if user wants to use the password file provided
    chg_pwd = raw_input('    Enter Y if you would like to use password list from file:')
    # Force the user to use a capitol Y
    if chg_pwd == 'Y':

        file_name = raw_input(file_menu)
        if file_name:
            passwd_file = file_name
        else:
            passwd_file = optic.PASSWD_FILE

        print "Using password file:",passwd_file
        if optic.ONF: optic.ONF.write("Using password file: " + passwd_file +"\n")

        # Open file and grab contents 21 bytes at a time
        # Strip new line character off end and use raw bytes
        # as the password
        passwds = [binascii.a2b_hex(l.strip()) for l in open(passwd_file,'rb')]

        fpasswds = passwds

    else:
        print "Not using password file."
        if optic.ONF: optic.ONF.write("Not using password file\n")

    # Generate list of passwords for fuzzing
    # 21 character passwords, one good, one bad
    fpasswds.extend([optic.PASSWD + '\x20','\x20' * 21])
    # Grow good password one byte without padding
    for e in range(len(optic.PASSWD)+1):
        fpasswds.append(optic.PASSWD[0:e])
    # Grow good password one byte with padding
    for e in range(len(optic.PASSWD)):
        ptmp = optic.PASSWD[0:e]
        if len(ptmp) < 20:
            ptmp = ptmp + ('\x20' * (20 - len(ptmp)))
            fpasswds.append(ptmp)
    # Extra large passwords - turn on if necessary
    #for e in range(10):
        #ptmp = (e * 1000) * '\x20'
        #fpasswds.append(ptmp)

    # Get new user number or use default from configuration file
    user_num = raw_input(user_menu)
    if user_num == '':
        user_num = optic.USER_NUM
    else:
        user_num = int(user_num)

    print "Logging on as User: ",user_num
    if optic.ONF: optic.ONF.write("Logging on as User: " + str(user_num) + "\n")

    # Setup meter connection
    if not optic.packet.login_setup(optic.SER_CONN0):
        print "Logon setup failed."
        return

    # Logon
    if not optic.packet.login_user(optic.SER_CONN0, user_num):
        print "Logon setup failed. Try restarting."
        return

    # Roll through security codes
    for passwd in fpasswds:
        print "Using password:",bt.print_data(passwd)
        if optic.ONF: optic.ONF.write("Using password:" + bt.print_data(passwd) + "\n")

        # Send security code
        if optic.packet.login_passwd(optic.SER_CONN0, passwd):
            print "   Logon Successful"
            if optic.ONF: optic.ONF.write("   Logon Successful\n")

            # Logoff
            #if not optic.packet.send_logoff(optic.SER_CONN0):
            if not optic.packet.send_terminate(optic.SER_CONN0):
                print "Logoff failed."

            # Setup meter connection
            if not optic.packet.login_setup(optic.SER_CONN0):
                print "Logon setup failed."
                return

            # Logon
            if not optic.packet.login_user(optic.SER_CONN0, user_num):
                print "Logon setup failed. Try restarting."
                break
        else:
            print "   Logon Failed"
            if optic.ONF: optic.ONF.write("   Logon Failed\n")

        # Pause allows meter to remain stable
        c12packet.delay(c12packet.logon_pause)

    print "Fuzz Security Code Function completed"
    if optic.ONF: optic.ONF.write("Fuzz Security Code function completed\n")

    # Return
    return
############################
# End Fuzz Security Code
############################

############################
# Alternate Fuzz Security Code
############################
def do_action_alt_fuzz_sec(optic):
    '''
    Action: Alternate Fuzz C12.18 Security Code. This function will attempt to 
    send malformed C12.18 Security Codes to see if the meter responds differently 
    when provided with unexpected data.

    NOTE: Some meters return login success for any security code provided. These types
    of meters check level of access provided by the security code. In these cases,
    use the alternate brute forcing function which detects success by reading a
    restricted table.
    '''

    print "Running: Fuzz Security Code Function"
    if optic.ONF: optic.ONF.write("Running: Fuzz Security Code function\n")
    print "Current password: ",bt.print_data(optic.PASSWD)
    if optic.ONF: optic.ONF.write("Current password: " + bt.print_data(optic.PASSWD) + "\n\n")

    # Passwords can be provided using an external file.
    #global PASSWDS
    passwds = []
    fpasswds = []

    # Check if user wants to use the password file provided
    chg_pwd = raw_input('    Enter Y if you would like to use password list from file:')
    # Force the user to use a capitol Y
    if chg_pwd == 'Y':

        file_name = raw_input(file_menu)
        if file_name:
            passwd_file = file_name
        else:
            passwd_file = optic.PASSWD_FILE

        print "Using password file:",passwd_file
        if optic.ONF: optic.ONF.write("Using password file: " + passwd_file +"\n")

        # Open file and grab contents 21 bytes at a time
        # Strip new line character off end and use raw bytes
        # as the password
        passwds = [binascii.a2b_hex(l.strip()) for l in open(passwd_file,'rb')]

        fpasswds = passwds
    else:
        print "Not using password file."
        if optic.ONF: optic.ONF.write("Not using password file\n")

    # Generate list of passwords for fuzzing
    # 21 character passwords, one good, one bad
    fpasswds.extend([optic.PASSWD + '\x20','\x20' * 21])
    # Grow good password one byte without padding
    for e in range(len(optic.PASSWD)+1):
        fpasswds.append(optic.PASSWD[0:e])
    # Grow good password one byte with padding
    for e in range(len(optic.PASSWD)):
        ptmp = optic.PASSWD[0:e]
        if len(ptmp) < 20:
            ptmp = ptmp + ('\x20' * (20 - len(ptmp)))
            fpasswds.append(ptmp)
    # Extra large passwords - turn on if necessary
    #for e in range(10):
        #ptmp = (e * 1000) * '\x20'
        #fpasswds.append(ptmp)

    # Get new user number or use default from configuration file
    user_num = raw_input(user_menu)
    if user_num == '':
        user_num = optic.USER_NUM
    else:
        user_num = int(user_num)

    print "Logging on as User: ",user_num
    if optic.ONF: optic.ONF.write("Logging on as User: " + str(user_num) + "\n")

    # Setup meter connection
    if not optic.packet.login_setup(optic.SER_CONN0):
        print "Logon setup failed."
        return

    # Logon
    if not optic.packet.login_user(optic.SER_CONN0, user_num):
        print "Logon setup failed. Try restarting."
        return

    # Loop thru security codes
    for passwd in fpasswds:
        print "Using password:",bt.print_data(passwd)
        if optic.ONF: optic.ONF.write("Using password:" + bt.print_data(passwd) + "\n")

        # Send security code
        if optic.packet.login_passwd(optic.SER_CONN0, passwd):

            # For Alternate Fuzz Security Code we need to test
            # successful logins by reading a restricted table
            table_num = 45

            # Read Table
            results = optic.packet.full_table_read(optic.SER_CONN0, table_num)
            if results[0]:
                print "   Logon Successful"
                if optic.ONF: optic.ONF.write("   Logon Successful\n")

                # Logoff
                #if not optic.packet.send_logoff(optic.SER_CONN0):
                if not optic.packet.send_terminate(optic.SER_CONN0):
                    print "Logoff failed."
                    break

                # Setup meter connection
                if not optic.packet.login_setup(optic.SER_CONN0):
                    print "Logon setup failed."
                    return

                # Logon
                if not optic.packet.login_user(optic.SER_CONN0, user_num):
                    print "Logon setup failed. Try restarting."
                    break
            else:
                print "   Logon Failed"
                if optic.ONF: optic.ONF.write("   Logon Failed\n")
        else:
            print "   Passwd Failed"
            if optic.ONF: optic.ONF.write("   Passwd Failed\n")

        # Pause allows meter to remain stable
        c12packet.delay(c12packet.sec_pause)

    print "Alternate Fuzz Security Code Function completed"
    if optic.ONF: optic.ONF.write("Alternate Fuzz Security Code function completed\n")

    # Return
    return
############################
# End Alternate Fuzz Security Code
############################

##########################################################
## c12_optic()
##########################################################
class c12_optic():

    def __init__(self, comm_port = "/dev/ttyUSB0",comm_baud = 9600, config_file='c12_18_config.txt'):
        self.TIME           = time.strftime('%Y%m%d%H%M%S')
        self.DEBUG          = False
        self.CONFIG_FILE    = config_file
        self.COMM_PORT      = comm_port
        self.COMM_BAUD      = comm_baud
        self.PASSWD         = ('\x20' * 20)
        self.USER_STR       = ('\x53\x4d\x41\x43\x4B' + '\x20' * 5) # SMACK
        self.USER_NUM       = 2
        self.INVERT         = 0
        self.NEGO_ON        = False
        self.PASSWD_FILE    = ''
        self.LOG_DIR        = os.path.join(os.path.abspath(os.curdir),'logs')
        if not os.path.isdir(self.LOG_DIR):
            os.makedirs(self.LOG_DIR)
        #self.OUTFILE        = 'c1218_optical_results_' + self.TIME + '.txt'
        self.OUTFILE        = os.path.join(self.LOG_DIR,'c1218_optical_results_' + self.TIME + '.txt')

        # Parse configuration file
        self.config()

        # Try to write output to a file
        # Output will also be written to STDOUT
        # Debugging information is NOT written to the output file
        self.ONF = ''
        if self.OUTFILE:
            try:
                self.ONF = open(self.OUTFILE,'w')
            except:
                print "Could not open output file. Continuing, but output will NOT be saved to file."
                
        # Initialize Comm Port    
        self.SER_CONN0 = c12serial.SERCONN(debug = self.DEBUG)
        self.SER_CONN0.serInit(port = self.COMM_PORT, baud = self.COMM_BAUD, invert = self.INVERT)

        # Setup and configure packet
        self.packet = self.config_packet()
        self.packet.set_debug(self.DEBUG)
        self.packet.set_nego(self.NEGO_ON)

        if self.DEBUG: print 'Debug:',self.DEBUG
        if self.DEBUG: print 'config file:',self.CONFIG_FILE
        if self.DEBUG: print 'comm_port:',self.COMM_PORT
        if self.DEBUG: print 'comm_baud:',self.COMM_BAUD
        if self.DEBUG: print 'outfile:',self.OUTFILE
        if self.DEBUG: print 'passwd:',bt.print_data(self.PASSWD)
        if self.DEBUG: print 'user_str:',bt.print_data(self.USER_STR)
        if self.DEBUG: print 'user_num:',self.USER_NUM
        if self.DEBUG: print 'Invert:',self.INVERT
        if self.DEBUG: print 'Negotiation:',self.NEGO_ON
        if self.DEBUG: print 'passwd_file:',self.PASSWD_FILE
        if self.DEBUG: print 'log_dir:',self.LOG_DIR

    def config(self):
        '''Process configuration file.'''

        config      = ConfigParser.ConfigParser()
        if len(config.read(self.CONFIG_FILE)) == 0:
            print "No configuration file found."
        else:
            try:

                self.DEBUG       = config.getint('C1218Optical','debug')
                self.USER_NUM    = config.getint('C1218Optical','user_num')
                self.USER_STR    = bt.str2hex(config.get('C1218Optical','user_str'))[:10]
                self.USER_STR    += ('\x20' * (10 - len(self.USER_STR)))
                self.PASSWD      = bt.str2hex(config.get('C1218Optical','passwd'))
                self.PASSWD      += ('\x20' * (20 - len(self.PASSWD)))
                self.PASSWD_FILE = config.get('C1218Optical','passwd_file')
                self.COMM_PORT   = config.get('C1218Optical','comm_port')
                self.COMM_BAUD   = config.get('C1218Optical','comm_baud')
                self.INVERT      = config.getint('C1218Optical','invert')
                self.NEGO_ON     = config.get('C1218Optical','nego_on')

                # Make output file unique
                self.OUTFILE     = config.get('C1218Optical','outfile')
                self.TMP_OUTFILE = self.OUTFILE.split('.')
                #self.OUTFILE     = self.TMP_OUTFILE[0] + '_' + self.TIME + '.' + self.TMP_OUTFILE[1]
                self.LOG_DIR     = os.path.join(os.path.abspath(os.curdir),config.get('C1218Optical','log_dir'))
                if not os.path.isdir(self.LOG_DIR):
                    os.makedirs(self.LOG_DIR)
                self.OUTFILE     = os.path.join(self.LOG_DIR, self.TMP_OUTFILE[0] + '_' + self.TIME + '.' + self.TMP_OUTFILE[1])
                
                print "Successfully parsed configuration file:",self.CONFIG_FILE
                return
            except:
                print "Config file parsing problem: " + self.CONFIG_FILE
                pass

        print "Using defaults."

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
    ["Test Negotiation Sequence", do_action_test_nego], \
    ["Test Logon", do_action_test], \
    ["Parse Configuration Table", do_action_tread00 ], \
    ["Parse General Manufacturer Identification Table", do_action_tread01 ], \
    ["Read Table", do_action_tread ], \
    ["Read Multiple Tables", do_action_mread ], \
    ["Read Decade", do_action_dread ], \
    ["Run Procedure", do_action_rproc ], \
    ["Run Multiple Procedures", do_action_mproc ], \
    ["Run Multiple Procedures without login", do_action_mproc_nl ], \
    ["Write Table", do_action_wtable ], \
    ["Brute Force Logon", do_action_brute ], \
    ["Alternate Brute Force Logon (Read Table Verification)", do_action_alt_brute ], \
    ["Fuzz Security code", do_action_fuzz_sec ], \
    ["Alternate Fuzz Security code", do_action_alt_fuzz_sec ], \
    ["Read Single Table walking User IDs", do_action_fsread ], \
    ["Read Multiple Table walking User IDs", do_action_fmread ], \
    ["Write Table 13 Demand Control Table. Table write Proof of Concept only. ", do_action_twrite13 ], \
    ["Run Procedure 21 Direct Load Control and set 0 percent load", do_action_tmeterld0 ], \
    ["Run Procedure 21 Direct Load Control and set 100 percent load", do_action_tmeterld100 ], \
    ["Toggle Negotiation", do_action_tnego ], \
    ["Terminate Session", do_action_term ], \
    ["Reset Serial", do_action_srestart ], \
    ["Toggle Debug", do_action_tdebug ], \
    ["Toggle Invert", do_action_tinvert ], \
]

# User Menus
user_menu   = "\n   Logon as User Number. Hit enter for default.\n   Enter number (0-65535): "
fuser_menu  = "\n   Range of User Numbers to use to fuzz logon. Range is between 0 - 65535 or use \'all\'. "
fuser_menu_s= "\n   Start Number. Hit enter for 0: "
fuser_menu_e= "\n   Stop Number. Hit enter for 65535: "
table_menu  = "\n   0) Standard Table\n   1) Manufacturer Table\n   Enter Table Type: " 
mtable_menu = "\n   Enter comma separated list of tables.\n   For example: 1,2,3,4 (Manufacturers start at 2040)\n   Use \'all\' for tables 0-170 or 2040-2159\n   Enter Tables: "
decade_menu = "\n   Enter Decade Number. Standard Decades are 0 through 16.  Manufacturer Decades are 204 through 215."
proc_menu   = "\n   0) Standard Procedure\n   1) Manufacturer Procedure\n   Enter Procedure Type: " 
mproc_menu  = "\n   Enter comma separated list of procedures. For example: 1,2,3,4\n   Enter Tables: "
num_menu    = "\n   Enter Number: "
data_menu_no_default   = "\n   Data Entry must be hex data entered as straight ascii.\n   For example: \\xee\\xff\\x00\\x01 == eeff0001\n   To cancel just hit enter.\n   Enter data: "
data_menu_default   = "\n   Data Entry must be hex data entered as straight ascii.\n   For example: \\xee\\xff\\x00\\x01 == eeff0001\n   To use default value just hit enter.\n   Enter data: "
userid_menu = "\n   This only tests if a particular User number and identification string is accepted by the meter.\n   It does not send any security codes.\n   Enter User Identification String (max: 10 character): "
file_menu   = "\n   Enter file name. Press enter for default: "
pwd_menu   = "\n   Pick a password to test.  Data Entry must be hex data entered as straight ascii.\n   For example: \\xee\\xff\\x00\\x01 == eeff0001\n   To use default just hit enter.\n   Enter data: "
######################################

######################################
# Main Starts Here
######################################

# Set up main object
in_config = 'c12_18_config.txt'
if len(sys.argv) > 1:
    if sys.argv[1] == "-c":
        in_config = sys.argv[2]
    else:
        print "Could not locate configuration file. Using default"
        #sys.exit()

#optic = c12_optic()
optic = c12_optic(config_file=in_config)

print c12loglines.separator_long
if optic.ONF: optic.ONF.write(c12loglines.separator_long + "\n")
print c12loglines.log_header
if optic.ONF: optic.ONF.write(c12loglines.log_header + "\n")
print c12loglines.log_license
if optic.ONF: optic.ONF.write(c12loglines.log_license + "\n")
print c12loglines.separator_long
if optic.ONF: optic.ONF.write(c12loglines.separator_long + "\n")

# Mark starting time selecting quit will mark ending time
print "Start Time:",time.strftime('%X %x %Z')
if optic.ONF: optic.ONF.write("Start Time: " + time.strftime('%X %x %Z') + "\n")

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

