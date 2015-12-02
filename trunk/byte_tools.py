# byte_tools.py - functions to parse and modify byte data
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

def str2hex(data):
    '''Convert a string to their hex representation'''
    tmp = ''
    for e in range(0,len(data),2):
        # Grab 2 characters and decode them as their hex values
        tmp += data[e:e+2].decode('hex_codec')
    return tmp

def c12userstr(data):
    # Convert data to hex
    # Based on atlasutils.ascii2hex
    ustr = ''
    for x in range(len(data)):
        ustr += str2hex("%.02x"%ord(data[x]))
    # Make 10 bytes by truncating or padding with spaces '\x20'
    if len(ustr) > 10:
        ustr = ustr[:10]
    elif len(ustr) < 10:
        ustr += '\x20' * (10 - len(ustr))
    return ustr

def print_data(data = ''):
    '''Returns the results of incoming data in human-readable and printable format'''
    if data == '':
        return ''
    tstring = []
    for e in data:
        tstring.append('\\\\x'.decode('string_escape') + hex(ord(e))[2:])
    for e in range(len(tstring)):
        if len(tstring[e]) == 3:
            tmp = list(tstring[e])
            tmp.insert(-1,'0')
            tstring[e] = ''.join(tmp)
    return ''.join(tstring)
