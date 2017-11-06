#!/usr/bin/env python
"""Set flag sample_is_non_sync_sample in trun box if sample_depends_on != 2."""

# The copyright in this software is being made available under the BSD License,
# included below. This software may be subject to other third party and contributor
# rights, including patent rights, and no such rights are granted under this license.
#
# Copyright (c) 2017, Dash Industry Forum.
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

import os
import argparse

import mp4filter
from structops import str_to_uint32, uint32_to_str


class TrunFilter(mp4filter.MP4Filter):
    """Process trun and set the non-sync sample flag of samples."""

    def __init__(self, file_name, offset=None):
        super(TrunFilter, self).__init__(file_name)
        self.offset = offset
        self.relevant_boxes = ["moof"]

    def filterbox(self, box_type, data, file_pos, path=""):
        "Filter box or tree of boxes recursively."
        if path == "":
            path = box_type
        else:
            path = "%s.%s" % (path, box_type)
        output = ""
        if path in ("moof", "moof.traf"):
            output += data[:8]
            pos = 8
            while pos < len(data):
                size, box_type = self.check_box(data[pos:pos + 8])
                output += self.filterbox(box_type, data[pos:pos+size],
                                         file_pos + len(output), path)
                pos += size
        elif path == "moof.traf.trun":
            output = self.process_trun(data, output)
        else:
            output = data
        return output

    def process_trun(self, data, output):
        """Adjust time of tfdt if offset set."""
        version_and_flags = str_to_uint32(data[8:12])
        # version = version_and_flags >> 24
        flags = version_and_flags & 0xffffff
        sample_count = str_to_uint32(data[12:16])
        offset = 16
        if flags & 0x1:  # data_offset_present
            offset += 4
        if flags & 0x4:  # first_sample_flags
            offset += 4
        output += data[:offset]
        for i in range(sample_count):
            if flags & 0x100:  # sample_duration present
                output += data[offset:offset + 4]
                offset += 4
            if flags & 0x200:  # sample_size present
                output += data[offset:offset + 4]
                offset += 4
            if flags & 0x400:  # sample_flags present
                sample_flags = str_to_uint32(data[offset:offset + 4])
                if sample_flags != 0x2000000:  # Depends on other samples
                    sample_flags |= 0x10000
                output += uint32_to_str(sample_flags)
                offset += 4
            if flags & 0x800:  # composition_time_offset present
                output += data[offset:offset + 4]
                offset += 4
        return output


def main():
    "Add non-sync-sample flag in trun box for all samples which depend."

    parser = argparse.ArgumentParser(description="Add non-sync-sample flags "
                                                 "to ISO segments.")
    parser.add_argument('-o', '--outputdir', required=True)
    parser.add_argument('infile', nargs='+')
    args = parser.parse_args()

    for filepath in args.infile:
        tfilter = TrunFilter(filepath)
        tfilter.filter_top_boxes()
        output = tfilter.output
        filename = os.path.split(filepath)[1]
        outpath = os.path.join(args.outputdir, filename)
        print('%s -> %s  %dB' % (filepath, outpath, len(output)))
        with open(outpath, 'wb') as ofh:
            ofh.write(output)


if __name__ == "__main__":
    main()
