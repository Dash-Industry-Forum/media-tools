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

REPLACE_STRING = """</div>
 </body>
</tt><tt xmlns="http://www.w3.org/ns/ttml" xmlns:tts="http://www.w3.org/ns/ttml#styling" xml:lang="en" >
 <head >
    <styling >
        <style xml:id="defaultStyle" tts:color="#FFFFFF" tts:textAlign="center" />
        <style xml:id="bgBlack" tts:backgroundColor="#000000" />
    </styling>
    <layout >
        <region xml:id="region1" tts:extent="100% 20%" />
    </layout>
 </head>
 <body style="defaultStyle" >
    <div region="region1" >"""


class STPPFixerFilter(MP4Filter):
    """Process a media segment file. Drop skip, free, and sidx boxes on top level.
    """

    def __init__(self, file_name=None, data=None, new_track_id=None, new_default_sample_duration=None):
        MP4Filter.__init__(self, file_name, data)
        self.new_track_id = new_track_id
        self.new_default_sample_duration = new_default_sample_duration
        self.relevant_boxes = ['styp', 'moof', 'free', 'skip', 'sidx', 'mdat']
        self.composite_boxes = ['moof', 'moof.traf']
        self.ttml_length = None

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
        elif path == "moof.traf.trun": # Set sample count and offset
            output = self.process_trun(data)
        elif path == "mdat": # Fix TTML data
            output = self.process_mdat(data)
        else:
            output = data
        return output

    def process_composite_box(self, path, data):
        "Process composite boxes."
        container_size, container_box_type = self.check_box(data[0:8])
        inner_data = ""
        pos = 8
        while pos < len(data):
            size, box_type = self.check_box(data[pos:pos + 8])
            inner_data += self.filterbox(box_type, data[pos:pos+size], None, path)
            #print "Box:",box_type,", size:",size,", newsize:",len(inner_data)
            pos += size
        new_container_size = 8 + len(inner_data)
        #TODO. If this has changed, make sure that offsets are changes appropriately
        return uint32_to_str(new_container_size) + container_box_type + inner_data

    def process_tfhd(self, data):
        "Process the mvhd box and set timescale."
        tf_flags = str_to_uint32(data[8:12]) & 0xffffff
        #print "tfhd flags = %06x" % tf_flags

        if self.new_default_sample_duration is not None:
            output = uint32_to_str(str_to_uint32(data[0:4]) + 4)
            output += data[4:8]
            output += uint32_to_str(tf_flags | 0x8)
        else:
            output = data[0:8]
            output += uint32_to_str(tf_flags)

        if self.new_track_id is not None:
            old_track_id = str_to_uint32(data[12:16])
            output += uint32_to_str(self.new_track_id)
            print "Changed trackId from %d to %d" % (old_track_id, self.new_track_id)
        else:
            output += data[12:16]

        if self.new_default_sample_duration is not None:
            output += uint32_to_str(self.new_default_sample_duration)
            print "Added new default sample duration: %d"%(self.new_default_sample_duration)

        output += data[16:]
        return output

    def process_trun(self, data):
        tf_flags = str_to_uint32(data[8:12]) & 0xffffff

        output = data[0:8]
        output += uint32_to_str(tf_flags)

        print "Changing trun sample count"
        output += uint32_to_str(1)

        if tf_flags & 1:
            data_offset = str_to_uint32(data[16:20])
            if self.new_default_sample_duration is not None:
                print "Changing trun data offset: %d to %d"%(data_offset, data_offset + 4)
                data_offset += 4

            output += uint32_to_str(data_offset)

            output += data[20:]

        return output

    def process_mdat(self, data):
        print "Merging all ttml samples into one"
        ttml = data[8:]
        #print "------------------------------"
        #print ttml

        # Process TTML
        # TODO Fix this to use something better then string replace
        ttml = ttml.replace(REPLACE_STRING, "")
        self.ttml_length = len(ttml)

        #print "------------------------------"
        #print ttml

        output = uint32_to_str(self.ttml_length + 8)
        output += data[4:8]
        output += ttml

        return output

    def finalize(self):
        print "Changing default sample size"

        if self.new_default_sample_duration:
            newoutput = self.output[:76]
        else:
            newoutput = self.output[:72]

        newoutput += uint32_to_str(self.ttml_length)

        if self.new_default_sample_duration:
            newoutput += self.output[80:]
        else:
            newoutput += self.output[76:]

        self.output = newoutput


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
            print("Backup-file already exists. Skipping file %s" % file_name)
            continue
        stpp_cleaner = STPPFixerFilter(file_name, new_track_id=options.track_id,
                                       new_default_sample_duration=options.dur)
        print "Processing %s" % file_name
        output = stpp_cleaner.filter_top_boxes()
        os.rename(file_name, bup_name)
        with open(file_name, "wb") as ofh:
            ofh.write(output)


if __name__ == "__main__":
    main()
