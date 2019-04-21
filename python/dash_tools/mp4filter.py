"""Filter MP4 files and produce modified versions.

The filter is streamlined for DASH or other content with one track per file.
"""

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

from structops import str_to_uint32, str_to_sint32, uint32_to_str, sint32_to_str
from structops import str_to_uint64, uint64_to_str


def get_timescale(file_name=None, data=None):
    "Get timescale from track box."
    init_filter = InitFilter(file_name, data)
    init_filter.filter_top_boxes()
    return init_filter.get_track_timescale()


class MP4Filter(object):
    """Base class for filters.

    Call filter_top_boxes() to get a filtered version of the file."""

    def __init__(self, file_name=None, data=None):
        if file_name is not None:
            self.data = open(file_name, "rb").read()
        else:
            self.data = data
        self.output = ""
        self.relevant_boxes = [] # Boxes at top-level to filter_top_boxes
        self.top_level_boxes = []  # List of top_level boxes (size, type)
        #print "MP4Filter with %s" % file_name

    def check_box(self, data):
        "Check the type of box starting at position pos."
        #pylint: disable=no-self-use
        size = str_to_uint32(data[:4])
        box_type = data[4:8]
        return (size, box_type)

    def filter_top_boxes(self):
        "Top level box parsing. The lower-level parsing is done in self.filterbox(). "
        self.output = ""
        pos = 0
        while pos < len(self.data):
            size, box_type = self.check_box(self.data[pos:pos + 8])
            self.top_level_boxes.append((size, box_type))
            box_data = self.data[pos:pos+size]
            if box_type in self.relevant_boxes:
                self.output += self.filterbox(box_type, box_data,
                                              len(self.output))
            else:
                self.output += box_data
            pos += size
        self.finalize()
        return self.output

    def filterbox(self, box_type, data, file_pos, path=""):
        "Filter box or tree of boxes recursively. Override in subclass."
        #pylint: disable=unused-argument,no-self-use
        return data

    def finalize(self):
        "Hook to do final adjustments."
        pass


class InitFilter(MP4Filter):
    "Filter init file and extract track timescale."

    def __init__(self, file_name=None, data=None):
        MP4Filter.__init__(self, file_name, data)
        self.relevant_boxes = ['moov']
        self.track_timescale = -1
        self.handler_type = None

    def filterbox(self, box_type, data, file_pos, path=""):
        "Filter box or tree of boxes recursively."
        if path == "":
            path = box_type
        else:
            path = "%s.%s" % (path, box_type)
        output = ""
        if path in ("moov", "moov.trak", "moov.trak.mdia"):
            output += data[:8]
            pos = 8
            while pos < len(data):
                size, box_type = self.check_box(data[pos:pos + 8])
                output += self.filterbox(box_type, data[pos:pos+size], file_pos + len(output), path)
                pos += size
        elif path == "moov.trak.mdia.mdhd": # Find timescale
            self.track_timescale = str_to_uint32(data[20:24])
            #print "Found track_timescale=%d" % self.track_timescale
            output = data
        elif path == "moov.trak.mdia.hdlr": # Find track type
            self.handler_type = data[16:20]
            output = data
        else:
            output = data
        return output

    def get_track_timescale(self):
        "Return track timescale."
        return self.track_timescale

    def get_handler_type(self):
        "Return handler type."
        return self.handler_type


class InitLiveFilter(MP4Filter):
    "Process an init file and set the durations to maxint."

    def __init__(self, file_name=None, data=None):
        MP4Filter.__init__(self, file_name, data)
        self.relevant_boxes = ['moov']
        self.movie_timescale = -1

    def filterbox(self, box_type, data, file_pos, path=""):
        "Filter box or tree of boxes recursively."
        #pylint: disable=too-many-branches
        if path == "":
            path = box_type
        else:
            path = "%s.%s" % (path, box_type)
        output = ""
        if path in ("moov", "moov.trak", "moov.trak.mdia"):
            output += data[:8]
            pos = 8
            while pos < len(data):
                size, box_type = self.check_box(data[pos:pos + 8])
                output += self.filterbox(box_type, data[pos:pos + size], file_pos + len(output), path)
                pos += size
        elif path == "moov.mvhd": # Set movie duration
            version = ord(data[8])
            if version == 1:
                self.movie_timescale = str_to_uint32(data[28:32])
                output += data[:32]
                output += '\xff'*8 # duration
                output += data[40:]
            else: # version = 0
                self.movie_timescale = str_to_uint32(data[20:24])
                output += data[:24]
                output += '\xff'*4 # duration
                output += data[28:]
        elif path == "moov.trak.tkhd": # Set trak duration
            version = ord(data[8])
            if version == 1:
                output += data[:36]
                output += '\xff'*8 # duration
                output += data[44:]
            else: # version = 0
                output += data[:28]
                output += '\xff'*4 # duration
                output += data[32:]
        elif path == "moov.trak.mdia.mdhd": # Set media duration
            version = ord(data[8])
            if version == 1:
                output += data[:32]
                output += '\xff'*8 # duration
                output += data[40:]
            else: # version = 0
                output += data[:24]
                output += '\xff'*4 # duration
                output += data[28:]
        else:
            output = data
        return output


class SidxFilter(MP4Filter):
    "Remove sidx from file."

    def __init__(self, file_name=None, data=None):
        MP4Filter.__init__(self, file_name, data)
        self.relevant_boxes = ['sidx']

    def filterbox(self, box_type, data, file_pos, path=""):
        "Remove sidx, leave other boxes."
        if box_type == "sidx":
            output = ""
        else:
            output = data
        return output


class ShiftCompositionTimeOffset(MP4Filter):
    "Shift composition_time_offest in trun boxes to start at 0."

    def __init__(self, file_name):
        MP4Filter.__init__(self, file_name)
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
                output += self.filterbox(box_type, data[pos:pos+size], file_pos + len(output), path)
                pos += size
        elif path == "moof.traf.trun": # Down at trun level
            output = self.process_trun(data, output)
        else:
            output = data
        return output

    def process_trun(self, data, output):
        """Adjust composition_time_offset to start at 0 if present."""
        version_and_flags = str_to_uint32(data[8:12])
        version = version_and_flags >> 24
        flags = version_and_flags & 0x00ffffff

        cto_present = flags & 0x000800   # composition_time_offset_present

        if not cto_present:
            return data   # Nothing to do

        output = data[:8] + '\x01' + data[9:12]  # Full header version 1

        sample_count = str_to_uint32(data[12:16])
        offset = 16

        if flags & 0x000001:  # data-offset-present
            offset += 4

        if flags & 0x000004:  # first-sample-flags-present
            offset += 4

        output += data[12:offset]
        cto_shift = None

        optional_bytes_before_cto = 0
        if flags & 0x000100:  # sample-duration-present
            optional_bytes_before_cto += 4
        if flags & 0x000200:  # sample-size-present
            optional_bytes_before_cto += 4
        if flags & 0x000400:  # sample-flags-present
            optional_bytes_before_cto += 4

        for i in range(sample_count):
            output += data[offset:offset + optional_bytes_before_cto]
            offset += optional_bytes_before_cto

            cto = str_to_sint32(data[offset:offset + 4])
            if i == 0:
                cto_shift = -cto
            cto += cto_shift
            output += sint32_to_str(cto)
            offset += 4

        return output


class TfdtFilter(MP4Filter):
    """Process a file. Change the offset of tfdt if set, and write to outFileName.

    In addition, set sequence number if provided and drop sidx box.
    """

    def __init__(self, file_name, offset=None, seq_nr=None):
        MP4Filter.__init__(self, file_name)
        self.offset = offset
        self.seq_nr = seq_nr
        self.relevant_boxes = ["moof", "sidx"]
        self.tfdt = None

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
                output += self.filterbox(box_type, data[pos:pos+size], file_pos + len(output), path)
                pos += size
        elif path == "moof.traf.tfdt": # Down at tfdt level
            output = self.process_tfdt(data, output)
        elif path == "moof.mfhd": # Down at mfhd
            output = self.process_mfhd(data, output)
        elif path == "sidx":
            pass # Just drop sidx
        else:
            output = data
        return output

    def process_tfdt(self, data, output):
        """Adjust time of tfdt if offset set."""
        version = ord(data[8])
        if version == 0: # 32-bit baseMediaDecodeTime
            tfdt = str_to_uint32(data[12:16])
            if self.offset != None:
                tfdt += self.offset
                output += data[:12] + uint32_to_str(tfdt) + data[16:]
            else:
                output += data
        else:
            output = data[:12]
            tfdt = str_to_uint64(data[12:20])
            if self.offset != None:
                tfdt += self.offset
                output += uint64_to_str(tfdt)
            else:
                output += data
        self.tfdt = tfdt
        return output

    def process_mfhd(self, data, output):
        "Set the sequence number in mfhd."
        if self.seq_nr is not None:
            output += data[:12] + uint32_to_str(self.seq_nr)
        else:
            output += data
        return output

    def get_tfdt_value(self):
        "Return tfdt value."
        return self.tfdt
