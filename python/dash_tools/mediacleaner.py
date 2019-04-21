#!/usr/bin/env python
"""Clean media segment file and optionally set trackId."""

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


class MediaCleanFilter(MP4Filter):
    """Process a media segment file. Drop skip, free, and sidx boxes on top level.
    """
    # pylint: disable=unused-argument
    def __init__(self, file_name=None, data=None, new_track_id=None, new_default_sample_duration=None):
        MP4Filter.__init__(self, file_name, data)
        self.new_track_id = new_track_id
        self.relevant_boxes = ['styp', 'moof', 'free', 'skip', 'sidx']
        self.composite_boxes = ['moof', 'moof.traf']

    # pylint: disable=unused-argument
    def filterbox(self, box_type, data, file_pos, path=""):
        "Filter box or tree of boxes recursively."
        if path == "":
            path = box_type
        else:
            path = "%s.%s" % (path, box_type)
        output = ""
        if path in ("skip", "free", "sidx"):
            print "Removing %s box" % box_type # Just let output="" to drop these boxes
        elif path in self.composite_boxes:
            output = self.process_composite_box(path, data)
        elif path == "moof.traf.tfhd": # Set movie duration
            output = self.process_tfhd(data)
        else:
            output = data
        return output

    def process_composite_box(self, path, data):
        "Process a composite box."
        #pylint: disable=unused-variable
        container_size, container_box_type = self.check_box(data[0:8])
        inner_data = ""
        pos = 8
        while pos < len(data):
            size, box_type = self.check_box(data[pos:pos + 8])
            inner_data += self.filterbox(box_type, data[pos:pos+size], None, path)
            pos += size
        new_container_size = 8 + len(inner_data)
        #Note. If this has changed, make sure that offsets are changes appropriately
        return uint32_to_str(new_container_size) + container_box_type + inner_data

    def process_tfhd(self, data):
        "Process the mvhd box and set timescale."
        tf_flags = str_to_uint32(data[8:12]) & 0xffffff
        print "tfhd flags = %06x" % tf_flags
        output = data[0:12]
        if self.new_track_id is not None:
            old_track_id = str_to_uint32(data[12:16])
            output += uint32_to_str(self.new_track_id)
            print "Changed trackId from %d to %d" % (old_track_id, self.new_track_id)
        else:
            output += data[12:16]
        output += data[16:]
        return output


def main():
    "Command-line function."
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("--id", dest="track_id", type="int", help="set new trackID")
    parser.add_option("--dur", dest="dur", type="int", help="set new default_sample_duration")

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
        init_cleaner = MediaCleanFilter(file_name, new_track_id=options.track_id)
        print "Processing %s" % file_name
        output = init_cleaner.filter_top_boxes()
        with open(file_name, "wb") as ofh:
            ofh.write(output)

if __name__ == "__main__":
    main()
