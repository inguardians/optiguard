# c12_18_csv_parser.py - This program is designed to parse C12.18-based
# CSV data from a Saleae Logic Analyzer.
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

import os, sys, struct, time
from distutils.version import StrictVersion

TIME        = time.strftime('%Y%m%d%H%M%S')
MARKED      = False
TMP_OUTFILE = ''
RXD         = ''
TXD         = ''

def str2hex(data):
    '''Convert a string to their hex representation'''
    tmp = ''
    for e in range(0,len(data),2):
        # Grab 2 characters and decode them as their hex values
        tmp += data[e:e+2].decode('hex_codec')
    return tmp

def usage():
    print 'Usage:'
    print '    ',sys.argv[0],'-rxd <file> -txd <file> [-h] [-m] [-o <file>]'
    print '         -h -> Enable Help mode'
    print '         -rxd -> A CSV file that contains the response portion of data transmission'
    print '         -txd -> A CSV file that contains the request portion of data transmission'
    print '         -m -> Generate an output file that is marked according to the ANSI C12.18'
    print '               standard. This output may fail if the file contains errors'
    print '         -o -> Name of the output files.  This will be renamed to contain the'
    print '               date and time to make the file unique.  The filename will also be'
    print '               marked with COMBO for a normal combined output and COMBO-MARKED for'
    print '               the file marked according to the ANSI C12.18 standard.'
    print ''
    print 'This program is designed to parse CSV data from a Saleae Logic Analyzer.'
    print 'The input files should contain the hex byte output from the Async-Serial'
    print 'analyzer.  This data should follow the ANSI C12.18 packet structure.'
    print 'This tool will generate a combined CSV file that has been sorted.  If'
    print 'specified, the tool will also mark the bytes according to the ANSI'
    print 'C12.18 standard.'
    sys.exit()
    
while len(sys.argv) > 1:
    op = sys.argv.pop(1)
    if op == '-h':
        # Help mode
        usage()
    if op == '-rxd':
        # input file
        RXD = sys.argv.pop(1)
    if op == '-txd':
        # input file
        TXD = sys.argv.pop(1)
    if op == '-m':
        MARKED = True
    if op == '-o':
        # Make output file unique
        TMP_OUTFILE = sys.argv.pop(1).split('.')
        COMBO      = TMP_OUTFILE[0] + '_COMBO_' + TIME + '.' + TMP_OUTFILE[1]

if not RXD or not TXD:
    usage()

if MARKED:
    if TMP_OUTFILE:
        MCOMBO = TMP_OUTFILE[0] + '_COMBO-MARKED_' + TIME + '.' + TMP_OUTFILE[1]
    else:
        COMBO  = 'COMBO_' + TIME + '.csv'
        MCOMBO = 'COMBO-MARKED_' + TIME + '.csv'

# Open, grab, and close
rxd = open(RXD,'r')
txd = open(TXD,'r')
rlines = rxd.readlines()
rxd.close()
tlines = txd.readlines()
txd.close()

# Grab header line, add extra columns, remove from data we are about to process
header = rlines[0][:-1] + ",Direction,Contents,Notes\n"
rlines.pop(0)
tlines.pop(0)

# Cycle through the RXD lines, split, add extra columns, and prep time field for sorting
for e in range(len(rlines)):
    tmp = []
    rlines[e] = rlines[e][:-1].split(',')
    rlines[e].append("RXD")
    rlines[e].append(" ")
    rlines[e].append(" \n")
    # Make sure that the milliseconds has 10 digits for sorting
    tmp = rlines[e][0].split('.')
    milli_len = len(tmp[1])
    if milli_len < 10:
        tmp[1] += ('0' * (10 - milli_len))
    rlines[e][0] = '.'.join(tmp)

# Cycle through the TXD lines, split, add extra columns, and prep time field for sorting
for e in range(len(tlines)):
    tmp = []
    tlines[e] = tlines[e][:-1].split(',')
    tlines[e].append("TXD")
    tlines[e].append(" ")
    tlines[e].append(" \n")
    # Make sure that the milliseconds has 10 digits for sorting
    tmp = tlines[e][0].split('.')
    milli_len = len(tmp[1])
    if milli_len < 10:
        tmp[1] += ('0' * (10 - milli_len))
    tlines[e][0] = '.'.join(tmp)

# Combine Lists
clines = []
clines = rlines
clines.extend(tlines)

# Sort according to the time field
#nlines = sorted(clines,key=lambda x:x[0])
# 'Sorted' should work BUT python messes up the float point values
# So, do ugly sort
##############################3
j      = {}
tmp    = []
tmp2   = []
nlines = []

# Grab Time Stamps and make a list, they should all be unique strings
for c in range(len(clines)):
    tmp.append(clines[c][0])

# Sort as it the Time Stamps are version numbers
#print tmp
tmp.sort(key=StrictVersion)

# Split the lines into a dictionary of elements
for e in clines:
    j[e[0]] = e[1:]

# Use sorted Time Stamps to pull data from dictionary and rebuild 
for e in tmp:
    tmp2.append(e)
    tmp2.extend(j[e])
    nlines.append(tmp2)
    tmp2 = []
##############################3

# Write sorted data to the Combo file and close it
combo = open(COMBO,'w')
combo.write(header)
for e in nlines:
    e[0] = str(e[0])
    combo.write(','.join(e))
combo.close()

# Exit if we don't want marked output file
# Done, Good Bye
if not MARKED:
    print "Files processed successfully."
    print "Output written to:",COMBO
    sys.exit()

# Prep storage
tmp    = []

# Variables for control and management
value_field   = 1
content_field = 5
packet        = 0
tmp_len       = ''
len_val       = 0
ack           = '0x06'
ACK           = 'ACK'
nack          = '0x15'
NACK          = 'NACK'
stp           = '0xEE'
STP           = 'STP'
ident         = '0x00'
IDENT         = 'IDENT'
cntl_bytes    = ['0x00','0x20']
CNTL          = 'CNTL'
SEQ_NBR       = 'SEQ_NBR'
LENS          = ['LEN0','LEN1']
CRC           = 'CRC'
crc_iter      = 0

# Open output file
mcombo = open(MCOMBO,'w')

# Process data and mark appropriately
# We could probably make this a function, BUT
# it will actually be easier to watch where we are in the
# C12.18 packet and handle it as we except to see it
for tmp in nlines:
    if tmp[0] == 'Time [s]' or tmp[2].lower() == 'error' or tmp[3].lower() == 'error':
        mcombo.write(','.join(tmp))
        packet = 0
        continue
    # Test for NACK and ACK
    if not packet and (tmp[value_field] == ack or tmp[value_field] == nack):
        if tmp[value_field] == ack:
            tmp[content_field] = ACK
        else:
            tmp[content_field] = NACK
        mcombo.write(','.join(tmp))
        continue
    # Test for first packet byte and STP
    # Process STP
    if not packet and tmp[value_field] == stp:
        tmp[content_field] = STP
        mcombo.write(','.join(tmp))
        packet = 1
        continue
    # Proccess Packet
    # Process IDENT
    #if packet == 1 and tmp[value_field] == ident:
    if packet == 1:
        tmp[content_field] = IDENT
        mcombo.write(','.join(tmp))
        packet = 2
        continue
    # Process Control Byte
    #if packet == 2 and tmp[value_field] in cntl_bytes:
    if packet == 2:
        tmp[content_field] = CNTL
        mcombo.write(','.join(tmp))
        packet = 3
        continue
    # Process Sequence Number
    if packet == 3:
        tmp[content_field] = SEQ_NBR
        mcombo.write(','.join(tmp))
        packet = 4
        continue
    # Process first Length Byte
    if packet == 4:
        tmp[content_field] = LENS[0]
        mcombo.write(','.join(tmp))
        # Store first byte to determine length
        tmp_len += tmp[value_field][2:]
        packet = 5
        continue
    # Process second Length Byte
    if packet == 5:
        tmp[content_field] = LENS[1]
        mcombo.write(','.join(tmp))
        # Store second byte to determine length
        tmp_len += tmp[value_field][2:]
        # Determine the number of bytes left
        len_val = struct.unpack('>H',str2hex(tmp_len))[0]
        packet = 6
        continue
    # Process the number of bytes indicated by length
    if packet == 6 and len_val:
        mcombo.write(','.join(tmp))
        len_val -= 1
        continue
    # Process CRC
    if packet == 6 and not len_val:
        tmp[content_field] = CRC
        mcombo.write(','.join(tmp))
        if not crc_iter:
            crc_iter += 1
            continue
    # Reset VAlues
    # Just print anything that didn't get caught 
    if not packet:
        mcombo.write(','.join(tmp))
    packet  = 0
    tmp_len  = ''
    crc_iter = 0
        
# Done, Good Bye
print "Files processed successfully."
print "Output written to:",COMBO
print "and:",MCOMBO
mcombo.close()



