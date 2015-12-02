# c12_18_extract_keys.py - This program is designed to extract possible C12.18 Security
# Codes from a binary file.
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

import os, sys
import time

def usage():
    
    print 'Usage:'
    print '    ',sys.argv[0],'-f <file> [-h] [-d] [-b] [-st Start Size] [-sp Stop Size]'
    print '         INFILE -> the name of the binary file to read'
    print '         -h -> Enable Help mode'
    print '         -d -> Enable Debug mode'
    print '         -b -> Enable Found Bad mode removes c12.18 security codes with 3 consectutive characters. This could skip a valid security code.'
    print '         -st Start Size -> minimum length of C12 security code. Default: 10'
    print '         -sp Stop Size  -> maximum length of C12 security code. Default: 10'
    print ''
    print 'This program is designed to extract possible C12.18 Security'
    print 'Codes from a binary file. These will typically be dumps from memory or'
    print 'firmware.'
    sys.exit()


# Provided as reference
def str2hex(data):
    '''Convert a string to their raw hex representation'''
    tmp = ''
    for e in range(0,len(data),2):
        # Grab 2 characters and decode them as their hex values
        tmp += data[e:e+2].decode('hex_codec')
    return tmp

# Provided as reference
def print_data(data):
    '''Returns the results of incoming data in human-readable and printable format'''
    tstring = []
    for e in data:
        tstring.append('\\\\x'.decode('string_escape') + hex(ord(e))[2:])
    for e in range(len(tstring)):
        if len(string[e]) == 3:
            tmp = list(tstring[e])
            tmp.insert(-1,'0')
            tstring[e] = ''.join(tmp)
    return ''.join(tstring)

# Defaults
DEBUG   = False
BAD     = False
inf     = ''
start   = 10
stop    = 10

while len(sys.argv) > 1:
    op = sys.argv.pop(1)
    if op == '-h':
        # Help mode
        usage()
    if op == '-f':
        # input file
        inf = sys.argv.pop(1)
    if op == '-d':
        # Debugging mode
        DEBUG = True
    if op == '-b':
        # Enable 'found bad'
        BAD = True
    if op == '-st':
        # Min size of C12 security code
        start = int(sys.argv.pop(1))
        if not start:
            start = 1
    if op == '-sp':
        # Max size of C12 security code
        stop = int(sys.argv.pop(1))
        if stop > 20:
            stop = 20

# Process file
try:
    if DEBUG: print "In File:",inf
    INF = open(inf,'rb')
    data = INF.read()
    INF.close()
except:
    print sys.arg[0] + ": Could not parse: " + sys.arg[1]
    usage()

keys = []

if DEBUG: print "Start Size:",start,"Stop Size:",stop
if DEBUG: print "Start Time:",time.strftime('%X %x %Y')
if DEBUG: print "BAD Mode:", BAD

for size in range(start,stop+1):
    tmp = ''
    # C12.18 pads Security Code with Spaces to make 20 bytes
    padding = '20' * (20 - size)
    for cnt in range(len(data)):
        tmp = data[cnt:cnt+size]
        tmp2 = []
        tmp3 = ''

        # Make easy to parse from a text file AND readable
        for e in tmp:
            tmp3 = hex(ord(e))[2:]
            if len(tmp3) == 1:
                tmp3 = '0' + tmp3
            tmp2.append(tmp3)
            # Test for and drop BAD security codes
            if BAD and len(tmp2) >= 3:
                # This tests the last three bytes to determine if they are the same
                # This should be faster than looping through all characters
                if tmp2[-1] == tmp2[-2] and tmp2[-1] == tmp2[-3]:
                    tmp2 = []
                    break

        # Handle the skips and bytes at the EOF
        if len(tmp2) == size:
            keys.append(''.join(tmp2) + padding)

if DEBUG: print "Possible Keys Identified:",str(len(sorted(list(set(keys)))))

# output to STDOUT
if not DEBUG:
    for e in sorted(list(set(keys))):
        print e
        
if DEBUG: print "Completed Time:",time.strftime('%X %x %Y')
