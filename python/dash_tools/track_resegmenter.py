"""Resegment a DASH OnDemand/CMAF track to new exact average duration.

Useful to get audio segments with a specified average duration."""


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
from argparse import ArgumentParser
from collections import namedtuple

from structops import str_to_uint16, uint16_to_str, uint32_to_str, sint32_to_str
from structops import str_to_uint32, str_to_uint64, uint64_to_str
from track_data_extractor import TrackDataExtractor
from backup_handler import make_backup, BackupError

SegmentData = namedtuple("SegmentData", "nr start dur size data")
SegmentInfo = namedtuple("SegmentInfo", "start_nr end_nr start_time dur")


class TrackResegmenter(object):
    "Resegment an OnDemand/CMAF track into a new output track."

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

        self.input_parser = TrackDataExtractor(self.input_file,
                                               self.verbose)
        ip = self.input_parser
        ip.filter_top_boxes()
        if len(ip.input_segments) == 0:
            raise ValueError("No fragments found in input file. Progressive "
                             "file?")
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
            if self.output_file == self.input_file:
                try:
                    make_backup(self.input_file)
                except BackupError:
                    print("Backup file for %s already exists" %
                          self.input_file)
                    return
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
        version = 1  # Allow for signed cto
        ip = self.input_parser
        sample_data_size = nr_sample_bytes(self.sample_flags)
        sample_count = seg_info.end_nr - seg_info.start_nr
        trun_size = 20 + sample_count * sample_data_size
        output = uint32_to_str(trun_size) + 'trun'
        flags = self.sample_flags | 0x01  # offset present
        version_and_flags = (version << 24) | flags
        output += uint32_to_str(version_and_flags)
        output += uint32_to_str(sample_count)
        output += uint32_to_str(offset + trun_size + 8)  # 8 bytes into mdat
        for sample in ip.samples[seg_info.start_nr:seg_info.end_nr]:
            if self.sample_flags & 0x100:
                output += uint32_to_str(sample.dur)
            if self.sample_flags & 0x200:
                output += uint32_to_str(sample.size)
            if self.sample_flags & 0x400:
                output += uint32_to_str(sample.flags)
            if self.sample_flags & 0x800:
                output += sint32_to_str(sample.cto)
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

    resegmenter = TrackResegmenter(args.input_file, args.duration,
                                   args.output_file, args.skip_sidx,
                                   args.verbose)
    resegmenter.resegment()


if __name__ == "__main__":
    main()
