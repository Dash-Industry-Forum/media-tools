"""Resegment a CMAF track to new exact average duration.

Useful to get audio segments with a specified average duration."""


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

from argparse import ArgumentParser
from collections import namedtuple

from structops import str_to_uint16, uint16_to_str, uint32_to_str
from structops import str_to_uint32, str_to_uint64, uint64_to_str
from mp4filter import MP4Filter


SegmentData = namedtuple("SegmentData", "nr start dur size data")
SampleData = namedtuple("SampleData", "start dur size offset flags cto")
SegmentInfo = namedtuple("SegmentInfo", "start_nr end_nr start_time dur")



class SampleMetadataExtraction(MP4Filter):
    "Extract sample information from a CMAF track file."

    def __init__(self, file_name, verbose=False):
        super(SampleMetadataExtraction, self).__init__(file_name)
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
        self.styp = ""  # styp box, if any
        self.tfhd = ""
        self.tfdt_size = None
        self.trun_base_size = None  # Base size for trun
        self.trun_sample_flags = None  # Sample flags

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
            self.styp = data
        if path in containers:
            if path == "moof":
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
            output = self.process_sidx(data)
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

    def process_sidx(self, data):
        "Extract sidx parts."
        version = ord(data[8])
        if version == 0:
            first_offset = str_to_uint32(data[24:28])
            pos = 28
        else:
            first_offset = str_to_uint64(data[28:36])
            pos = 36
        if first_offset != 0:
            raise ValueError("Only supports first_offset == 0")
        pos += 2
        reference_count = str_to_uint16(data[pos:pos+2])
        pos += 2
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
        return  data

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
        if tf_flags & 0x000009:  # default_sample_duration_present
            self.default_sample_duration = str_to_uint32(data[pos:pos+4])
            pos += 4
        if tf_flags & 0x000010:  # default_sample_size_present
            self.default_sample_size = str_to_uint32(data[pos:pos+4])
            pos += 4
        if tf_flags & 0x000020:  # default_sample_flags_present
            self.default_sample_size = str_to_uint32(data[pos:pos+4])
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
        """Adjust time of tfdt if offset set."""
        version_and_flags = str_to_uint32(data[8:12])
        # version = version_and_flags >> 24
        flags = version_and_flags & 0xffffff
        sample_count = str_to_uint32(data[12:16])
        pos = 16
        start = self.base_media_decode_time
        data_offset = self.last_moof_start
        if flags & 0x1:  # data_offset_present
            data_offset += str_to_uint32(data[pos:pos+4])
            pos += 4
        else:
            raise ValueError("Cannot handle case without data_offset")
        if flags & 0x4:  # first_sample_flags
            pos += 4
            raise ValueError("Cannot handle first_sample_flag")
        self.trun_base_size = pos  # How many bytes this far
        if self.trun_sample_flags is None:
            self.trun_sample_flags = flags
        for i in range(sample_count):
            sample_duration = self.default_sample_duration
            sample_size = self.default_sample_size
            sample_flags = self.default_sample_flags
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


class Resegmenter(object):
    "Resegment a CMAF track into a new output track."

    def __init__(self, input_file, duration_ms, output_file,
                 skip_sidx=False, verbose=False):
        self.input_file = input_file
        self.duration_ms = duration_ms
        self.output_file = output_file
        self.verbose = verbose
        self.input_parser = None
        self.skip_sidx = skip_sidx
        self.sidx_range = ""

    def resegment(self):
        "Resegment the track with new duration."
        self.input_parser = SampleMetadataExtraction(self.input_file,
                                                     self.verbose)
        ip = self.input_parser
        ip.filter_top_boxes()
        timescale = ip.track_timescale
        if self.verbose:
            for i, segment in enumerate(ip.input_segments):
                print("Input segment %d: dur=%d" % (i + 1,
                                                    segment['duration']))

        segment_info = self._map_samples_to_new_segments()
        self.track_id = ip.track_id
        output_segments = []
        segment_sizes = []
        for i, seg_info in enumerate(segment_info):
            output_segment = ""
            if ip.styp:
                output_segment += ip.styp
            output_segment += self._generate_moof(i+1, seg_info)
            output_segment += ip.construct_new_mdat(seg_info)
            output_segments.append(output_segment)
            segment_sizes.append(len(output_segment))
        if self.output_file:
            with open(self.output_file, "wb") as ofh:
                input_header_end = self.input_parser.find_header_end()
                ofh.write(ip.data[:input_header_end])
                if not self.skip_sidx:
                    sidx = self._generate_sidx(segment_info, segment_sizes,
                                               timescale)
                    ofh.write(sidx)
                    sidx_start = input_header_end
                    self.sidx_range = "%d-%d" % (sidx_start,
                                                 sidx_start + len(sidx) - 1)
                for output_segment in output_segments:
                    ofh.write(output_segment)

    def _map_samples_to_new_segments(self):
        "Calculate which samples go into which segments."
        new_segment_info = []
        segment_nr = 1
        acc_time = 0
        start_nr = 0
        start_sample = self.input_parser.samples[0]
        timescale = self.input_parser.track_timescale
        nr_samples = len(self.input_parser.samples)
        for i, sample in enumerate(self.input_parser.samples):
            acc_time += sample.dur
            if acc_time * 1000  > segment_nr * self.duration_ms * timescale:
                end_sample = self.input_parser.samples[i-1]
                end_time = end_sample.start + end_sample.dur
                seg_dur = end_time - start_sample.start
                info = SegmentInfo(start_nr, i, start_sample.start, seg_dur)
                new_segment_info.append(info)
                start_nr = i
                start_sample = sample
                segment_nr += 1

        if start_nr != nr_samples - 1:
            end_sample = self.input_parser.samples[-1]
            end_time = end_sample.start + end_sample.dur
            info = SegmentInfo(start_nr, nr_samples, start_sample.start,
                               end_time - start_sample.start)
            new_segment_info.append(info)
        if self.verbose:
            for i, info in enumerate(new_segment_info):
                print("Output segment %d: dur=%d" % (i +1, info.dur))
        print("Generating %d segments from %d" %
              (len(new_segment_info),  len(self.input_parser.input_segments)))
        return new_segment_info

    def _generate_sidx(self, segment_info, segment_sizes, timescale):
        "Generate sidx box."
        earliest_presentation_time = segment_info[0].start_time
        parts = ['sidx',
                 uint32_to_str(0), # version + flags
                 uint32_to_str(1), # reference_ID
                 uint32_to_str(timescale),
                 uint32_to_str(earliest_presentation_time),
                 uint32_to_str(0),  # first_offset
                 uint16_to_str(0),  # reserved
                 uint16_to_str(len(segment_sizes))]  # reference_count
        for info, size in zip(segment_info, segment_sizes):
            parts.append(uint32_to_str(size))  # Setting reference type to 0
            parts.append(uint32_to_str(info.dur))
            parts.append(uint32_to_str(0x90000000)) # SAP info
        output = ''.join(parts)
        size = 4 + len(output)
        output = uint32_to_str(size) + output
        return output

    def _generate_moof(self, sequence_nr, seg_info):
        "Generate a moof box with the correct sample entries"
        mfhd = self._generate_mfhd(sequence_nr)
        offset = 8 + len(mfhd)
        traf = self._generate_traf(seg_info, offset)
        size = 8 + len(mfhd) + len(traf)
        return uint32_to_str(size) + 'moof' + mfhd + traf

    def _generate_mfhd(self, sequence_nr):
        return (uint32_to_str(16) +  # size
                'mfhd' +
                uint32_to_str(0) +  # version_and_flags
                uint32_to_str(sequence_nr))

    def _generate_traf(self, seg_info, offset):
        tfhd = self._generate_tfhd(seg_info, self.track_id)
        tfdt = self._generate_tfdt(seg_info)
        offset += 8 + len(tfhd) + len(tfdt)
        trun = self._generate_trun(seg_info, offset)
        size = 8 + len(tfhd) + len(tfdt) + len(trun)
        return uint32_to_str(size) + 'traf' + tfhd + tfdt + trun

    def _generate_tfhd(self, seg_info, track_id):
        ip = self.input_parser
        first_sample = ip.samples[seg_info.start_nr]
        common_size = first_sample.size
        common_dur = first_sample.dur
        common_flags = first_sample.flags
        common_cto = first_sample.cto
        for sample in ip.samples[seg_info.start_nr + 1:seg_info.end_nr]:
            if sample.dur != common_dur:
                common_dur = None
            if sample.size != common_size:
                common_size = None
            if sample.flags != common_flags:
                common_flags = None
            if sample.cto != common_cto:
                common_cto = None
        flags = 0x020000
        data = ""
        sample_flags = 0  # Which individual sample data is needed
        if common_dur is not None:
            flags |= 0x08
            data += uint32_to_str(common_dur)
        else:
            sample_flags |= 0x100
        if common_size is not None:
            flags |= 0x10
            data += uint32_to_str(common_size)
        else:
            sample_flags |= 0x200
        if common_flags is not None:
            flags |= 0x20
            data += uint32_to_str(common_flags)
        else:
            sample_flags |= 0x400
        if common_cto is None or common_cto != 0:
            sample_flags |= 0x800
        size = 16 + len(data)
        self.sample_flags = sample_flags

        version_and_flags = flags
        return (uint32_to_str(size) + 'tfhd' +
                uint32_to_str(version_and_flags) +
                uint32_to_str(track_id) + data)

    def _generate_tfdt(self, seg_info):
        if seg_info.start_time > 2 ** 30:
            version = 1
            size = 20
        else:
            version = 0
            size = 16
        output = uint32_to_str(size) + 'tfdt'
        if version == 0:
            output += uint32_to_str(0x00000000) + uint32_to_str(
                seg_info.start_time)
        else:
            output += uint32_to_str(0x01000000) + uint64_to_str(
                seg_info.start_time)
        return output

    def _generate_trun(self, seg_info, offset):
        "Generate trun box with correct sample data for segment."

        def nr_sample_bytes(sample_flags):
            nr_bytes = 0
            for pattern in (0x100, 0x200, 0x400, 0x800):
                if sample_flags & pattern != 0:
                    nr_bytes += 4
            return nr_bytes
        version = 0
        ip = self.input_parser
        sample_data_size = nr_sample_bytes(self.sample_flags)
        sample_count = seg_info.end_nr - seg_info.start_nr
        trun_size = 20 + sample_count * sample_data_size
        output = uint32_to_str(trun_size) + 'trun'
        flags = self.sample_flags | 0x01  # offset present
        version_and_flags = (version << 24) | flags
        output += uint32_to_str(version_and_flags)
        output += uint32_to_str(sample_count)
        output += uint32_to_str(offset + trun_size + 8) # 8 bytes into mdat
        for sample in ip.samples[seg_info.start_nr:seg_info.end_nr]:
            if self.sample_flags & 0x100:
                output += uint32_to_str(sample.dur)
            if self.sample_flags & 0x200:
                output += uint32_to_str(sample.size)
            if self.sample_flags & 0x400:
                output += uint32_to_str(sample.flags)
            if self.sample_flags & 0x800:
                output += uint32_to_str(sample.cto)
        return output


def main():
    parser = ArgumentParser(usage="usage: %(prog)s [options]")

    parser.add_argument("-i", "--input-file",
                        action="store",
                        dest="input_file",
                        default="",
                        help="Input CMAF track file",
                        required=True)

    parser.add_argument("-d", "--duration",
                        action="store",
                        dest="duration",
                        type=float,
                        default=2000,
                        help="New average segment duration in milliseconds")

    parser.add_argument("-o", "--output-file",
                        action="store",
                        dest="output_file",
                        default="",
                        help="Output CMAF track file")

    parser.add_argument("-v", "--verbose",
                        action="store_true",
                        dest="verbose",
                        help="Verbose mode")

    parser.add_argument("-s", "--skip_sidx",
                        action="store_true",
                        dest="skip_sidx",
                        help="Do not write sidx box to output")

    args = parser.parse_args()

    resegmenter = Resegmenter(args.input_file, args.duration,
                              args.output_file, args.skip_sidx,
                              args.verbose)
    resegmenter.resegment()

if __name__ == "__main__":
    main()
