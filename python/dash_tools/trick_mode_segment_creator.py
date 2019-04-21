"""Create trick mode segments by removing all other frames than the first."""

import os
import shutil
from argparse import ArgumentParser

from mp4filter import MP4Filter
from structops import str_to_uint32, uint32_to_str, str_to_uint64, uint64_to_str


class TrickFilter(MP4Filter):
    """Process a segment, and write new with only first sample."""

    def __init__(self, file_name, offset=None):
        MP4Filter.__init__(self, file_name)
        self.offset = offset
        self.relevant_boxes = ["moof", "mdat"]
        self.moof_data = None
        self.traf_data = None
        self.trun_data = None

    def filterbox(self, box_type, data, file_pos, path=""):
        "Filter box or tree of boxes recursively."
        if path == "":
            path = box_type
        else:
            path = "%s.%s" % (path, box_type)
        output = ""
        if path in ("moof", "moof.traf"):
            size, b_type = self.check_box(data)
            if path == "moof":
                assert b_type == "moof"
                self.moof_data = {'pos': file_pos, 'size': size}
            elif path == "moof.traf":
                assert b_type == "traf"
                self.traf_data = {'pos': file_pos, 'size': size}
            output += data[:8]
            pos = 8
            file_pos += 8
            while pos < len(data):
                data_len = len(data)
                sub_data = data[pos:]
                size, box_type = self.check_box(sub_data)
                output += self.filterbox(box_type, sub_data[:size], file_pos,
                                         path)
                pos += size
                file_pos += size
        elif path == "moof.traf.trun": # Our target box
            output = self.process_trun(data)
        elif path == "mdat":
            output = self.process_mdat(data)
        else:
            output = data
        return output

    def process_trun(self, data):
        """Remove all samples but one, and change offset and report size."""
        size, b_type = self.check_box(data)
        assert b_type == "trun"
        self.trun_data = {'size' : size}
        # version = ord(data[8])

        flags = str_to_uint32(data[8:12]) & 0xffffff
        has_data_offset = flags & 0x0001
        if not has_data_offset:
            raise ValueError("Cannot shorten segment without data_offset")
        has_first_sample_flags = flags & 0x0004
        has_sample_duration = flags & 0x0100
        if not has_sample_duration:
            raise ValueError("Cannot shorten segment without sample duration")
        has_sample_size = flags & 0x0200
        if not has_sample_size:
            raise ValueError("Cannot shorten segment without sample_size")
        has_sample_flags = flags & 0x0400
        has_sample_composition_time_offset = flags & 0x0800

        sample_count = str_to_uint32(data[12:16])

        entry_offset = 16

        data_offset = str_to_uint32(data[entry_offset:entry_offset + 4])
        entry_offset += 4


        if has_first_sample_flags:
            entry_offset += 4

        sample_row_size = ((has_sample_duration and 4) +
                           (has_sample_size and 4) +
                           (has_sample_flags and 4) +
                           (has_sample_composition_time_offset and 4))

        # Iterate over all samples and add up duration.
        # Set the duration of the I-frame to the total duration

        total_duration = 0

        pos = entry_offset
        for i in range(sample_count):
            total_duration += str_to_uint32(data[pos:pos + 4])
            pos += 4
            if i == 0:
                sample_size = str_to_uint32(data[pos:pos + 4])
                self.trun_data['first_sample_size'] = sample_size
            pos += 4
            if has_sample_flags:
                pos += 4
            if has_sample_composition_time_offset:
                pos += 4

        new_size = size - (sample_count - 1) * sample_row_size
        self.trun_data['new_size'] = new_size

        new_data_offset = data_offset - (size - new_size)

        # Here starts the trun output
        output = uint32_to_str(new_size) + data[4:12]
        output += uint32_to_str(1) # 1 sample
        output += uint32_to_str(new_data_offset)
        pos = entry_offset
        if has_first_sample_flags:
            output += data[pos:pos + 4]
            pos += 4
        output += uint32_to_str(total_duration)
        pos += 4
        output += data[pos:pos + sample_row_size - 4]

        return output

    def process_mdat(self, data):
        """Remove all samples but one, and change offset and report size."""
        size, b_type = self.check_box(data)
        assert b_type == "mdat"
        data_size = self.trun_data['first_sample_size']
        return uint32_to_str(data_size + 8) + "mdat" + data[8: 8 + data_size]

    def finalize(self):
        "Rewrite the size fields which have changed"
        op = self.output
        op_parts = []

        size_reduction = self.trun_data['size'] - self.trun_data['new_size']
        op_parts.append(op[:self.moof_data['pos']])

        # Write new moof size
        new_moof_size = self.moof_data['size'] - size_reduction
        op_parts.append(uint32_to_str(new_moof_size))
        pos = self.moof_data['pos'] + 4
        op_parts.append(op[pos:self.traf_data['pos']])

        # Write new traf size
        new_traf_size = self.traf_data['size'] - size_reduction
        op_parts.append(uint32_to_str(new_traf_size))
        pos = self.traf_data['pos'] + 4

        op_parts.append(op[pos:])

        self.output = "".join(op_parts)


def convert_directory(input_dir, output_dir):
    file_names = os.listdir(input_dir)
    for f in file_names:
        base, ext = os.path.splitext(f)
        in_path = os.path.join(input_dir, f)
        out_path = os.path.join(output_dir, f)
        if base == 'init':
            print "Copying %s -> %s" % (in_path, out_path)
            shutil.copyfile(in_path, out_path)
        elif ext == '.m4s':
            print "Converting %s -> %s" % (in_path, out_path)
            trick_filter = TrickFilter(in_path)
            output = trick_filter.filter_top_boxes()
            with open(out_path, 'wb') as ofh:
                ofh.write(output)


if __name__ == "__main__":
    parser = ArgumentParser(usage="usage: %(prog)s [options]")

    parser.add_argument("-i", "--input-dir", action="store",
                        dest="input_dir", help="Input directory",
                        required=True)

    parser.add_argument("-o", "--output-door", action="store",
                        dest="output_dir", help="Output dir",
                        required=True)
    args = parser.parse_args()
    convert_directory(args.input_dir, args.output_dir)
