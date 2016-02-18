"""
Test parsing of HLS Segments
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

import os
import sys
import unittest

import test_utils
import ts

class TestHLSSegments(unittest.TestCase):

    def setUp(self):
        pass

    def test_muxed_segment(self):

        seg_path = os.path.join(test_utils.TEST_PATH, 'data/H1.ts')

        options = {}
        options['video'] = False
        options['audio'] = False
        options['text'] = False
        options['verbose'] = 0

        obs = ts.parser_observer(options)
        importer = ts.ts_importer(obs, options, False)

        ts.handle_file(seg_path, 0, importer)
        #importer.report()

        self.assertEquals(importer.num_packets, 580)
        self.assertEquals(importer.num_bytes, 109040)

    def test_audio_segment(self):

        seg_path = os.path.join(test_utils.TEST_PATH, 'data/A1.ts')

        options = {}
        options['video'] = False
        options['audio'] = False
        options['text'] = False
        options['verbose'] = 0

        obs = ts.parser_observer(options)
        importer = ts.ts_importer(obs, options, False)

        ts.handle_file(seg_path, 0, importer)

        self.assertEquals(importer.num_packets, 284)
        self.assertEquals(importer.num_bytes, 53392)
    
    def test_video_segment(self):

        seg_path = os.path.join(test_utils.TEST_PATH, 'data/V1.ts')

        options = {}
        options['video'] = False
        options['audio'] = False
        options['text'] = False
        options['verbose'] = 0

        obs = ts.parser_observer(options)
        importer = ts.ts_importer(obs, options, False)

        ts.handle_file(seg_path, 0, importer)

        self.assertEquals(importer.num_packets, 298)
        self.assertEquals(importer.num_bytes, 56024)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestHLSSegments)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(len(result.failures) + len(result.errors))
