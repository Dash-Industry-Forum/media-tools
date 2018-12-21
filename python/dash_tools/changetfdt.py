#!/usr/bin/env python
"""Change tfdt with the offset given."""

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
import mp4filter

def main():
    "Change base_media_decode_time in tfdt on multiple segment files."

    argv = sys.argv
    if len(argv) == 2:
        infile = argv[1]
        tfilter = mp4filter.TfdtFilter(infile)
        tfilter.filter_top_boxes()
        tfdt = tfilter.get_tfdt_value()
        print tfdt
    else:
        offset = int(argv[1])
        in_nr = int(argv[2])
        out_nr = int(argv[3])
        more = True
        nr_files_processed = 0
        while more:
            infile_name = "%d.m4s" % in_nr
            outfile_name = "%d.m4s" % out_nr
            if os.path.exists(infile_name):
                tfilter = mp4filter.TfdtFilter(infile_name, offset)
                tfilter.filter_top_boxes()
                ofh = open(outfile_name, "wb")
                data = tfilter.output
                ofh.write(data)
                ofh.close()
                in_nr += 1
                out_nr += 1
                nr_files_processed += 1
            else:
                more = False
                print "Processed %d files" % nr_files_processed


if __name__ == "__main__":
    main()
