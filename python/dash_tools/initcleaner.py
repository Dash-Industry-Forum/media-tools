#!/usr/bin/env python
"""Clean init file and optionally set trackId."""

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
import os

from structops import uint32_to_str, str_to_uint32
from mp4filter import MP4Filter
from backup_handler import make_backup, BackupError

class InitCleanFilter(MP4Filter):
    """Process an init file and clean it.

    Movie duration = 0
    Movie timescale = 90000
    skip and free boxes on top level are removed
    """

    def __init__(self, file_name=None, data=None, new_track_id=None):
        MP4Filter.__init__(self, file_name, data)
        self.new_track_id = new_track_id
        self.relevant_boxes = ['ftyp', 'moov', 'free', 'skip']
        self.movie_timescale = None

    def filterbox(self, box_type, data, file_pos, path=""):
        "Filter box or tree of boxes recursively."
        if path == "":
            path = box_type
        else:
            path = "%s.%s" % (path, box_type)
        output = ""
        if path in ("skip", "free"):
            print "Removing %s box" % box_type # Just let output="" to drop these boxes
        elif path in ("moov", "moov.trak", "moov.trak.mdia"):
            output += data[:8]
            pos = 8
            while pos < len(data):
                size, box_type = self.check_box(data[pos:pos + 8])
                output += self.filterbox(box_type, data[pos:pos + size], file_pos + len(output), path)
                pos += size
        elif path == "moov.mvhd": # Set movie duration
            output = self.process_mvhd(data)
        elif path == "moov.trak.tkhd": # Set trak duration
            output = self.process_tkhd(data)
        elif path == "moov.trak.mdia.mdhd": # Set media duration
            version = ord(data[8])
            if version == 1:
                output += data[:32]
                output += '\x00'*8 # duration
                output += data[40:]
            else: # version = 0
                output += data[:24]
                output += '\x00'*4 # duration
                output += data[28:]
        else:
            output = data
        return output

    def process_mvhd(self, data):
        "Process the mvhd box and set timescale."
        output = ""
        version = ord(data[8])
        if version == 1:
            self.movie_timescale = str_to_uint32(data[28:32])
            output += data[:32]
            output += '\x00'*8 # duration
            output += data[40:]
        else: # version = 0
            self.movie_timescale = str_to_uint32(data[20:24])
            output += data[:24]
            output += '\x00'*4 # duration
            output += data[28:]
        return output

    def process_tkhd(self, data):
        "Process tkhd and set flags, trackId and duration."
        version = ord(data[8])
        output = data[0:9]
        output += '\x00' + '\x00' + '\x07' # Set flags to 0x000007
        pos = 12
        if version == 1:
            drange = 16
        else:
            drange = 8
        output += data[pos:pos+drange]
        pos += drange
        if self.new_track_id is not None:
            old_track_id = str_to_uint32(data[pos:pos+4])
            output += uint32_to_str(self.new_track_id)
            print "Changed trackId from %d to %d" % (old_track_id, self.new_track_id)
        else:
            output += data[pos:pos+4]
        pos += 4
        output += data[pos:pos+4]
        pos += 4
        if version == 1:
            output += '\x00'*8 # duration
            pos += 8
        else: # version = 0
            output += '\x00'*4 # duration
            pos += 4
        output += data[pos:]
        return output


def main():
    "Command-line function."
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("--id", dest="track_id", type="int", help="set new trackID")

    (options, args) = parser.parse_args()

    if len(args) < 1:
        parser.error("Wrong number of arguments")
        sys.exit(1)
    for file_name in args:
        try:
            make_backup(file_name)
        except BackupError:
            print "Backup-file already exists. Skipping file %s" % file_name)
            continue
        init_cleaner = InitCleanFilter(file_name, new_track_id=options.track_id)
        print "Processing %s" % file_name
        output = init_cleaner.filter_top_boxes()
        os.rename(file_name, bup_name)
        with open(file_name, "wb") as ofh:
            ofh.write(output)


if __name__ == "__main__":
    main()
