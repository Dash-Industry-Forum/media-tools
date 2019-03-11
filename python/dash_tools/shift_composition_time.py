#!/usr/bin/env python
"""Shift composition_times in trun to align presentation and decode time."""

# The copyright in this software is being made available under the BSD License,
# included below. This software may be subject to other third party and contributor
# rights, including patent rights, and no such rights are granted under this license.
#
# Copyright (c) 2019, Dash Industry Forum.
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
import shutil
from argparse import ArgumentParser

from mp4filter import ShiftCompositionTimeOffset
from backup_handler import make_backup, BackupError


def process_files(files):
    for f in files:
        f_backup = f + '_bup'
        if os.path.exists(f_backup):
            print("%s already exists, will not process %s" %
                  (f_backup, f))
            continue
        sto = ShiftCompositionTimeOffset(f)
        output = sto.filter_top_boxes()
        input = open(f, 'rb').read()
        if output != input:
            assert len(output) == len(input)
            print("Change in file %s. Make backup %s" % (f, f_backup))
            try:
                make_backup(f)
            except BackupError:
                print("Cannot make backup for %s. Skipping it" % f)
                return
            with open(f, 'wb') as ofh:
                ofh.write(output)


def main():
    "Shift presentation time to decode time, and make backup of old file."
    parser = ArgumentParser(usage='Shift presentation time to decode time in trun')

    parser.add_argument('files', metavar='N', type=str, nargs='+',
                        help = 'files to be changed')

    args = parser.parse_args()

    if len(args.files) < 1:
        parser.error("Need at least one file")
        sys.exit(1)

    process_files(args.files)


if __name__ == "__main__":
    main()
