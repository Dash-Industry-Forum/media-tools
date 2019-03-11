"""Create an OnDemand DASH Asset with multiple bitrates.

Intended to be used as a second step after batch_encoder.py with the
same configuration file.
Uses MP4Box to create the initial DASH OnDemand asset, but improves it
in a second step by resegmenting the audio to correct average segment duration.

Configuration is JSON file input and same as for batch_encoder.py, but only
segmentDurationMs and the variant names are used.
One can therefore make a minimal configuration like:

[
  {
    "contentType" : "video",
    "segmentDurationMs": 4000,
    "variants" : [
      {"name": "o1"}, {"name": "o2"}
    ]
  },
  {
    "contentType" : "audio",
    "variants": [
      {"name": "ae"}, {"name": "al"}
    ]
  }
]

If languages are in the mdhd box they will be extracted automatically.

"""
import os
import sys
import json
import subprocess
from cStringIO import StringIO
from xml import sax
from xml.sax import handler, saxutils, xmlreader
from argparse import ArgumentParser

from track_resegmenter import TrackResegmenter
from backup_handler import make_backup, BackupError

MP4BOX = "MP4Box"  # path to MP4Box of late-enough version.


def check_mp4box_version():
    cmd_line = [MP4BOX, "-version"]
    result = subprocess.check_output(cmd_line, stderr=subprocess.STDOUT)
    parts = result.split()
    for i, part in enumerate(parts):
        if part == "version":
            version = parts[i+1]
            return version.split("-")[0]
    return None


class MPDSidxFilter(saxutils.XMLFilterBase):
    "Filter that changes the indexRange for sidx box in MPD given dict."

    def __init__(self, parser, sidx_for_representations):
        saxutils.XMLFilterBase.__init__(self, parser)
        self.sidx_for_represesentations = sidx_for_representations
        self.curr_rep = None
        self.rdf_stack = []

    def startElementNS(self, (uri, localname), qname, attrs):
        if localname == 'Representation':
            rep_id = attrs.getValueByQName('id')
            if rep_id in self.sidx_for_represesentations:
                self.curr_rep = rep_id
        elif localname == 'SegmentBase' and self.curr_rep:
            mod_attrs = {}
            for key, value in attrs.items():
                uri, local_key = key
                if local_key == 'indexRange':
                    mod_attrs[key] = self.sidx_for_represesentations[
                        self.curr_rep]
                else:
                    mod_attrs[key] = value
            attrs = xmlreader.AttributesNSImpl(mod_attrs, attrs.getQNames())
        saxutils.XMLFilterBase.startElementNS(self, (uri, localname), qname,
                                              attrs)

    def endElementNS(self, (uri, localname), qname):
        if localname == 'Representation':
            self.curr_rep = None
        saxutils.XMLFilterBase.endElementNS(self, (uri, localname), qname)


class DashOnDemandCreator(object):
    """Process output from batch_encoder and package as DASH OnDemand content.

    Also fix audio segment durations to agree with video."""

    def __init__(self, config_file, directory, mpd_file_name):
        self.directory = directory
        self.mpd_name = mpd_file_name
        self.tracks = {'video': [], 'audio': []}
        self.segment_duration_ms = None
        self._parse_config_file(config_file)

    def _parse_config_file(self, config_file):
        "Parse JSON config file and extract segmentDurationMs and tracks."
        txt = open(config_file, "r").read()
        json_data = json.loads(txt)
        for top_level in json_data:
            content_type = top_level['contentType']
            if content_type == 'video':
                seg_dur = top_level["segmentDurationMs"]
                if self.segment_duration_ms is not None:
                    if seg_dur != self.segment_duration_ms:
                        raise ValueError("Multiple segment duration values")
                self.segment_duration_ms = seg_dur
            for variant in top_level['variants']:
                self.tracks[content_type].append(variant['name'])

    def process(self):
        "Process the actual media and create DASH OnDemand content."
        self.segment_media(self.tracks, self.segment_duration_ms)
        sidx_ranges = self.resegment_audio_tracks(self.tracks,
                                                  self.segment_duration_ms)
        print "New sidx ranges %s" % sidx_ranges
        mpd_path = self.file_path(self.mpd_name)
        self.fix_sidx_ranges_in_mpd(mpd_path, sidx_ranges)

    def segment_media(self, tracks, dur_ms):
        "Call MP4Box to segment the media."
        print "MP4Box version is %s" % check_mp4box_version()
        mp4box_cmd = self.create_mp4box_command(tracks, dur_ms)
        print "Running %s" % " ".join(mp4box_cmd)
        result = subprocess.check_output(mp4box_cmd, stderr=subprocess.STDOUT)
        print result

    def create_mp4box_command(self, tracks, dur_ms):
        parts = [MP4BOX, '-dash', str(dur_ms), '-frag',
                 str(dur_ms), '-profile', 'onDemand',
                 '-out', self.file_path(self.mpd_name)]
        for track in tracks['video']:
            parts.append('{0}.mp4:id={1}'.format(self.file_path(track), track))
        for track in tracks['audio']:
            parts.append('{0}.mp4:id={1}'.format(self.file_path(track), track))
        return parts

    def file_path(self, name):
        return os.path.join(self.directory, name)

    def resegment_audio_tracks(self, tracks, dur_ms):
        sidx_ranges = {}
        for track in tracks['audio']:
            file_name = self.file_path('{0}_dashinit.mp4'.format(track))
            # out_name = '{0}_dashout.mp4'.format(track)
            resegmenter = TrackResegmenter(file_name, dur_ms, file_name)
            resegmenter.resegment()
            sidx_ranges[track] = resegmenter.sidx_range
        return sidx_ranges

    def _fix_sidx_ranges(self, input_file, output, sidx_for_representations):
        "Filter input and replace ranges for sidx boxes."

        output_gen = saxutils.XMLGenerator(output, encoding='utf-8')
        parser = sax.make_parser()
        sidx_filter = MPDSidxFilter(parser, sidx_for_representations)
        sidx_filter.setFeature(handler.feature_namespaces, True)
        sidx_filter.setContentHandler(output_gen)
        sidx_filter.setErrorHandler(handler.ErrorHandler())
        sidx_filter.parse(input_file)

    def fix_sidx_ranges_in_mpd(self, mpd_file, sidx_ranges):
        "Fix sidx ranges MPD file."
        output = StringIO()
        with open(mpd_file, 'rb') as ifh:
            self._fix_sidx_ranges(ifh, output, sidx_ranges)
        try:
            make_backup(mpd_file)
        except BackupError:
            print("Backupfile already exists. Will not overwrite %s" %
                  mpd_file)
            return
        with open(mpd_file, 'wb') as ofh:
            ofh.write(output.getvalue())


def main():
    parser = ArgumentParser(usage="usage: %(prog)s [options]")

    parser.add_argument("-c", "--config-file",
                        action="store",
                        dest="config_file",
                        default="",
                        help="Configuration file in JSON format",
                        required=True)

    parser.add_argument("-d", "--directory",
                        action="store",
                        dest="directory",
                        default="",
                        help="Directory where input tracks are avaiable,"
                             "and where output is written.",
                        required=True)

    parser.add_argument("-m", "--manifest-filename",
                        action="store",
                        dest="manifest_filename",
                        default="manifest.mpd",
                        help="DASH Ondemand MPD file name")

    parser.add_argument("-v", "--verbose",
                        action="store_true",
                        dest="verbose",
                        help="Verbose mode")

    args = parser.parse_args()

    dc = DashOnDemandCreator(args.config_file, args.directory,
                             args.manifest_filename)
    dc.process()


if __name__ == "__main__":
    main()

