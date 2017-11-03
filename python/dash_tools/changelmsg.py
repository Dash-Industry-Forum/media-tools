#!/usr/bin/env python
"""Add or remove lmsg to a specific DASH segment file."""

# The copyright in this software is being made available under the BSD License,
# included below. This software may be subject to other third party and contributor
# rights, including patent rights, and no such rights are granted under this license.
#
# Copyright (c) 2016, Dash Industry Forum.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright notice, this
#  list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright notice,
#  this list of conditions and the following disclaimer in the documentation and/or
#  other materials provided with the distribution.
#  * Neither the name of Dash Industry Forum nor the names of its
#  contributors may be used to endorse or promote products derived from this software
#  without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS AS IS AND ANY
#  EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#  WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
#  IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
#  INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
#  NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
#  PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
#  WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
#  ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#  POSSIBILITY OF SUCH DAMAGE.

import sys
import cStringIO
from structops import str_to_uint32, uint32_to_str

class StypParser(object):
    "Parser of styp box which can modify the lmsg compatbility brand,"

    def __init__(self, file_path):
        self.file_path = file_path
        self.remove_lmsg_flag = False
        self.add_lmsg_flag = False

    def remove_lmsg(self):
        "Remove lmsg flag."
        self.remove_lmsg_flag = True
        self.process_file()

    def add_lmsg(self):
        "Add an lmsg flag."
        self.add_lmsg_flag = True
        self.process_file()

    def process_file(self):
        "Process the file and add or remove lmsg."
        ifh = open(self.file_path, "rb")
        data = ifh.read()
        styplen = str_to_uint32(data[:4])
        box_type = data[4:8]
        assert box_type == "styp"

        pos = 16
        lmsg_found = False
        while pos < styplen:
            compatible_brand = data[pos:pos+4]
            if compatible_brand == "lmsg":
                lmsg_found = True
                if self.remove_lmsg_flag:
                    print "Found lmsg to remove"
                    break
            pos += 4
        ofh = cStringIO.StringIO()
        if self.add_lmsg_flag and not lmsg_found:
            ofh.write(uint32_to_str(styplen+4))
            ofh.write(data[4:styplen])
            ofh.write("lmsg")
            ofh.write(data[styplen:])
            print "Adding lmsg"
        elif self.remove_lmsg_flag and lmsg_found:
            ofh.write(uint32_to_str(styplen-4))
            ofh.write(data[4:pos])
            ofh.write(data[pos+4:])
        else:
            print "No change done to %s" % self.file_path
            return # Nothing to do
        ifh.close()
        replace = open(self.file_path, "wb")
        replace.write(ofh.getvalue())
        replace.close()
        print "Wrote %s" % self.file_path

def usage():
    "Usage file."
    print "Usage: -a or -r file.m4s"
    sys.exit(1)

def main():
    "Command-line function."
    if len(sys.argv) < 3:
        usage()
    styp_parser = StypParser(sys.argv[2])
    if sys.argv[1] == "-a":
        styp_parser.add_lmsg()
    elif sys.argv[1] == "-r":
        styp_parser.remove_lmsg()
    else:
        usage()

if __name__ == "__main__":
    main()





