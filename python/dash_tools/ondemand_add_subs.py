"""Add subtitles to a DASH OnDemand MPD."""

import os
import re
import sys
from collections import namedtuple
from argparse import ArgumentParser

from backup_handler import make_backup, BackupError


Format = namedtuple('Format', 'name mime_type extension')


FORMATS = {
    'ttml': Format('ttml', 'application/ttml+xml', '.ttml'),
    'webvtt': Format('webvtt', 'text/wvtt', '.vtt'),
    'srt': Format('srt', 'text/srt', '.srt')}


AS_TEMPLATE = '''\
    <AdaptationSet contentType="text" mimeType="%(mime_type)s" lang="%(lang)s">
      <Role schemeIdUri="urn:mpeg:dash:role:2011" value="subtitle"/>
      <Representation id="%(rep_id)s" bandwidth="10000">
         <BaseURL>%(filename)s</BaseURL>
      </Representation>
    </AdaptationSet>
'''


class SubtitleFile():

    def __init__(self, filename, lang=None, format=None):
        self.filename = filename
        if lang is None:
            lang = 'und'
        self.lang = lang
        base, ext = os.path.splitext(filename)
        self.base = base
        if format is None:
            if ext == '':
                raise ValueError("No file extension and no format specified")
            ext = ext.lower()
            for fmt in FORMATS.values():
                if fmt.extension == ext:
                    format = fmt.name
                    break
            else:
                raise ValueError('File extension %s not in supported '
                                 'extensions: %s' % (ext, [f.extension for f in FORMATS.values()]))
        self.format = FORMATS[format]

    @property
    def adaptation_set(self):
        return AS_TEMPLATE % ({
            'mime_type': self.format.mime_type,
            'lang': self.lang,
            'filename': self.filename,
            'rep_id': self.base
        })


def add_subtitles(mpd_file, subtitle_files):
    "Add subtitles to a DASH manifest file."

    with open(mpd_file, 'r') as ifh:
        mpd_content = ifh.read()

    as_end = r"\</AdaptationSet\>[\r\n]*"
    # Open file, parse manifest, find proper place to add Adaptaiton set
    sub_xml = ''.join(sub_file.adaptation_set for sub_file in subtitle_files)
    as_end_mobj = re.search(as_end, mpd_content)
    if as_end_mobj is None:
        raise ValueError('Cound not find AdaptationSet in %s' % mpd_file)

    end_pos = as_end_mobj.end()
    output_mpd = mpd_content[:end_pos] + sub_xml + mpd_content[end_pos:]

    try:
        make_backup(mpd_file)
    except BackupError:
        print("Backup-file already exists. Skipping file %s" % mpd_file)

    with open(mpd_file, 'w') as ofh:
        ofh.write(output_mpd)


def main():
    parser = ArgumentParser()
    parser.add_argument('mpd')
    parser.add_argument('files_and_langs', nargs='+', help='List of file language pairs')

    args = parser.parse_args()
    if len(args.files_and_langs) % 2 != 0:
        print("You must list pairs of files and languages")
        parser.usage()
        sys.exit(1)

    subfiles = []
    for i in range(len(args.files_and_langs) // 2):
        subfile = args.files_and_langs[2 * i]
        lang = args.files_and_langs[2 * i + 1]
        subfiles.append(SubtitleFile(subfile, lang))

    add_subtitles(args.mpd, subfiles)


if __name__ == "__main__":
    main()
