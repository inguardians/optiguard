# c12_18_table00_parser - python module parsing C12.19 Table 00
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

# TODO: c12_18_table00_parser: Fix this so that it is not so complicated to use.

from bitarray import bitarray
import sys

std_base = 0
mfg_base = 2040
mfg_proc_base = 2048

def get_procs(data,base):
    '''Return a list of tables from data bytes.'''

    tmp = bitarray(endian='little')
    tmp.frombytes(data)
    plist = tmp.tolist()
    tlist = []
    for e in range(len(tmp.tolist())):
        if tmp[e]:
            tlist.append(int(str(e+base)))
    return tlist
    
def get_tables(data,base):
    '''Return a list of tables from data bytes.'''

    tmp = bitarray(endian='little')
    tmp.frombytes(data)
    tlist = []
    for e in range(len(tmp.tolist())):
        if tmp[e]:
            tlist.append(int(str(e+base)))
    return tlist

def sget_procs(data,base):
    '''Return a list of tables from string data.'''

    tmp = bitstring(endian='little')
    tmp.frombytes(data)
    plist = tmp.tolist()
    tlist = []
    for e in range(len(tmp.tolist())):
        if tmp[e]:
            tlist.append(int(str(e+base)))
    return tlist
    
def sget_tables(data,base):
    '''Return a list of tables from string data.'''

    tmp = bitarray(endian='little')
    tmp.fromstring(data)
    tlist = []
    for e in range(len(tmp.tolist())):
        if tmp[e]:
            tlist.append(int(str(e+base)))
    return tlist

if __name__ == "__main__":

    try:
        indata = sys.argv[2]
    except:
        print 'User must provide information using string data'

    if sys.argv[1] == 'print_std_tables':
        print 'Standard Tables',sget_tables(std_tbls_used,c12tbl00.std_base)
    if sys.argv[1] == 'print_mfg_tables':
        print 'Manufacturer Tables',sget_tables(indata,c12tbl00.mfg_base)
    if sys.argv[1] == 'print_std_procs':
        print 'Standard Procedures',sget_procs(std_proc_used,c12tbl00.std_base)
    if sys.argv[1] == 'print_mfg_procs':
        print 'Manufacturer Procedures',sget_procs(mfg_proc_used,c12tbl00.mfg_proc_base)
    if sys.argv[1] == 'print_std_rw_tables':
        print 'Standard Writable Tables',sget_tables(std_tbls_write,c12tbl00.std_base)
    if sys.argv[1] == 'print_mfg_rw_tables':
        print 'Manufacturer Writable Tables',sget_tables(mfg_tbls_write,c12tbl00.mfg_base)
