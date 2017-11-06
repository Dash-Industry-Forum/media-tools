"""Extract data from DASH OnDemand/CMAF track"""


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

from collections import namedtuple

from structops import str_to_uint16, uint32_to_str
from structops import str_to_uint32, str_to_uint64
from mp4filter import MP4Filter

SampleData = namedtuple("SampleData", "start dur size offset flags cto")


class TrackDataExtractor(MP4Filter):
    "Extract data from DASH Ondemand/CMAF Track. "

    def __init__(self, file_name, verbose=False):
        super(TrackDataExtractor, self).__init__(file_name)
        self.verbose = verbose
        self.relevant_boxes = ["moov", "moof", "sidx"]
        self.track_timescale = None
        self.default_sample_duration = None
        self.default_sample_cto = None
        self.default_sample_flags = None
        self.default_sample_size = None
        self.input_segments = []
        self.samples = []
        self.last_moof_start = 0
        self.segment_start = None
        self.styp = ""  # styp box, if any
        self.tfhd = ""
        self.tfdt_size = None
        self.trun_base_size = None  # Base size for trun
        self.trun_sample_flags = None  # Sample flags
        self.sidx_data = None

    def filterbox(self, box_type, data, file_pos, path=""):
        "Filter box or tree of boxes recursively."
        containers = ("moov", "moov.trak", "moov.trak.mdia", "moov.mvex",
                      "moof", "moof.traf")
        if path == "":
            path = box_type
        else:
            path = "%s.%s" % (path, box_type)
        output = ""
        if path == "emsg":
            ValueError("emsg not supported")
        if path == "styp":
            if self.segment_start is None:
                self.segment_start = file_pos
            self.styp = data
        if path in containers:
            if path == "moof":
                if self.segment_start is None:
                    self.segment_start = file_pos
                self.last_moof_start = file_pos
            output += data[:8]
            pos = 8
            while pos < len(data):
                size, box_type = self.check_box(data[pos:pos + 8])
                output += self.filterbox(box_type, data[pos:pos+size],
                                         file_pos + len(output), path)
                pos += size
        elif path == "moov.mvex.trex":
            output = self.process_trex(data)
        elif path == "moov.trak.mdia.mdhd":
            output = self.process_mdhd(data)
        elif path == "moof.mfhd":
            output = self.process_mfhd(data)
        elif path == "moof.traf.tfhd":
            output = self.process_tfhd(data)
        elif path == "moof.traf.tfdt":
                output = self.process_tfdt(data)
        elif path == "moof.traf.trun":
            output = self.process_trun(data)
        elif path == "sidx":
            output = self.process_sidx(data, file_pos)
        elif path == "mdat":
            curr_seg = self.segments[-1]
            curr_seg['start'] = self.segment_start
            curr_seg['size'] = file_pos + len(data) - self.segment_start
        else:
            output = data
        return output

    def process_trex(self, data):
        "Get potential default values."
        self.track_id = str_to_uint32(data[12:16])
        self.default_sample_description_index = str_to_uint32(data[16:20])
        self.default_sample_duration = str_to_uint32(data[20:24])
        self.default_sample_size = str_to_uint32(data[24:28])
        self.default_sample_flags = str_to_uint32(data[28:32])
        return data

    def process_mdhd(self, data):
        "Extract track timescale."
        version = ord(data[8])
        if version == 1:
            offset = 28
        else:
            offset = 20
        self.track_timescale = str_to_uint32(data[offset:offset+4])
        return data

    def process_sidx(self, data, file_pos):
        "Extract sidx parts."
        version = ord(data[8])
        timescale = str_to_uint32(data[16:20])
        if version == 0:
            earliest_time = str_to_uint32(data[20:24])
            first_offset = str_to_uint32(data[24:28])
            pos = 28
        else:
            earliest_time = str_to_uint32(data[20:28])
            first_offset = str_to_uint64(data[28:36])
            pos = 36
        if first_offset != 0:
            raise ValueError("Only supports first_offset == 0")
        pos += 2
        reference_count = str_to_uint16(data[pos:pos+2])
        pos += 2
        sidx_data = {'timescale': timescale, 'segments': []}
        offset = file_pos + len(data) + first_offset
        start = earliest_time
        for i in range(reference_count):
            field = str_to_uint32(data[pos:pos+4])
            pos += 4
            reference_type = field >> 31
            if reference_type != 0:
                raise ValueError("Only sidx reference type == 0 supported")
            size = field & 0x7fffffff
            duration = str_to_uint32(data[pos:pos+4])
            if self.verbose:
                print("Input sidx %d: dur=%d" % (i + 1, duration))
            pos += 4
            field = str_to_uint32(data[pos:pos+4])
            pos += 4
            starts_with_sap = field >> 31
            if starts_with_sap != 1:
                raise ValueError("Only sidx with starts_with_sap supported")
            sap_type = (field >> 28) & 0x7
            if sap_type != 1:
                raise ValueError("Only sap type 1 supported, not %d" %
                                 sap_type)
            sap_delta_time = field & 0x0fffffff
            if sap_delta_time != 0:
                raise ValueError("Only sap_delta_time == 0 supported")
            seg_data = {'offset': offset, 'size': size, 'start': start,
                        'duration': duration}
            sidx_data['segments'].append(seg_data)
            offset += size
            start += duration
        self.sidx_data = sidx_data
        return data

    def process_mfhd(self, data):
        "Extract sequence number."
        sequence_number = str_to_uint32(data[12:16])
        segment = {'sequence_number': sequence_number,
                   'moof_start_offset': self.last_moof_start}
        self.input_segments.append(segment)
        return data

    def process_tfhd(self, data):
        """Check flags and set default values.

        We are only interested in some values."""
        tf_flags = str_to_uint32(data[8:12]) & 0xffffff
        self.track_id = str_to_uint32(data[12:16])
        pos = 16
        if tf_flags & 0x000001:  # base_data_offset_present
            base_data_offset = str_to_uint64(data[pos:pos+8])
            pos += 8
        if tf_flags & 0x000002:  # sample-description-index-present
            sample_description_index = str_to_uint32(data[pos:pos+4])
            pos += 4
        if tf_flags & 0x000008:  # default_sample_duration_present
            self.default_sample_duration = str_to_uint32(data[pos:pos+4])
            pos += 4
        if tf_flags & 0x000010:  # default_sample_size_present
            self.default_sample_size = str_to_uint32(data[pos:pos+4])
            pos += 4
        if tf_flags & 0x000020:  # default_sample_flags_present
            self.default_sample_flags = str_to_uint32(data[pos:pos+4])
            pos += 4
        return data

    def process_tfdt(self, data):
        "Extract baseMediaDecodeTime."
        version = ord(data[8])
        if version == 0:
            self.base_media_decode_time = str_to_uint32(data[12:16])
        else:
            self.base_media_decode_time = str_to_uint64(data[12:20])
        seg =  self.input_segments[-1]
        seg['base_media_decode_time'] = self.base_media_decode_time
        self.tfdt_size = len(data)
        return data

    def process_trun(self, data):
        """Extract trun information into self.segments[-1] and self.samples"""
        version_and_flags = str_to_uint32(data[8:12])
        # version = version_and_flags >> 24
        flags = version_and_flags & 0xffffff
        sample_count = str_to_uint32(data[12:16])
        first_sample_flags = None
        pos = 16
        start = self.base_media_decode_time
        data_offset = self.last_moof_start
        if flags & 0x1:  # data_offset_present
            data_offset += str_to_uint32(data[pos:pos+4])
            pos += 4
        else:
            raise ValueError("Cannot handle case without data_offset")
        if flags & 0x4:  # first_sample_flags
            first_sample_flags = str_to_uint32(data[pos:pos+4])
            pos += 4
            if flags & 0x400:  # sample_flags present
                raise ValueError("Sample flags are not allowed with first")
        self.trun_base_size = pos  # How many bytes this far
        if self.trun_sample_flags is None:
            self.trun_sample_flags = flags
        for i in range(sample_count):
            sample_duration = self.default_sample_duration
            sample_size = self.default_sample_size
            sample_flags = self.default_sample_flags
            if i == 0 and first_sample_flags is not None:
                sample_flags = first_sample_flags
            cto = self.default_sample_cto
            if flags & 0x100:  # sample_duration present
                sample_duration = str_to_uint32(data[pos:pos + 4])
                pos += 4
            if flags & 0x200:  # sample_size present
                sample_size = str_to_uint32(data[pos:pos + 4])
                pos += 4
            if flags & 0x400:  # sample_flags present
                sample_flags = str_to_uint32(data[pos:pos + 4])
                pos += 4
            if flags & 0x800:  # composition_time_offset present
                cto = str_to_uint32(data[pos:pos + 4])
                pos += 4
            if cto is None:
                cto = 0
            sample = SampleData(start, sample_duration, sample_size,
                                data_offset, sample_flags, cto)
            self.samples.append(sample)
            start += sample_duration
            data_offset += sample_size
        seg = self.input_segments[-1]
        seg['duration'] = start - self.base_media_decode_time
        return data

    def find_header_end(self):
        "Find where the header ends. This part will be left untouched."
        header_end = 0
        for size, box in self.top_level_boxes:
            if box in ('sidx', 'styp', 'moof'):
                break
            header_end += size
        return header_end

    def construct_new_mdat(self, media_info):
        "Return an mdat box with data for samples in media_info."
        start_nr = media_info.start_nr
        end_nr = media_info.end_nr
        sample_data = []
        for i in range(media_info.start_nr, media_info.end_nr):
            sample = self.samples[i]
            sample_data.append(self.data[sample.offset:sample.offset +
                                                       sample.size])
        combined_data = "".join(sample_data)
        return uint32_to_str(8 + len(combined_data)) + 'mdat' + combined_data
