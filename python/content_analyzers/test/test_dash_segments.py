"""
Test parsing of MPEG-DASH Segments
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
import mp4

class TestDASHSegments(unittest.TestCase):

    def setUp(self):
        pass

    def test_parse_audio_init_segment(self):

        with open(os.path.join(test_utils.TEST_PATH, 'data/audio_init.mp4'), 'rb') as f:
            data = f.read()

        root = mp4.mp4(data, len(data))
        
        # mvhd
        mvhd = root.find('moov.mvhd')
        self.assertTrue(mvhd)
        self.assertEquals(mvhd.timescale, 90000)
        self.assertEquals(mvhd.duration, 9630720)
        
        # tkhd
        tkhd = root.find('moov.trak.tkhd')
        self.assertTrue(tkhd)
        self.assertEquals(tkhd.track_id, 1)
        self.assertEquals(tkhd.duration, 9630720)
        
        # mdhd
        mdhd = root.find('moov.trak.mdia.mdhd')
        self.assertTrue(mdhd)
        self.assertEquals(mdhd.timescale, 48000)
        self.assertEquals(mdhd.duration, 5136384)
        
        # mp4a
        mp4a = root.find('moov.trak.mdia.minf.stbl.stsd.mp4a')
        self.assertTrue(mp4a)
        self.assertEquals(mp4a.channels, 2)
        self.assertEquals(mp4a.sample_size, 16)
        self.assertEquals(mp4a.sample_rate, 48000)
        
        # esds
        esds = root.find('moov.trak.mdia.minf.stbl.stsd.mp4a.esds')
        self.assertTrue(esds)

    def test_parse_audio_media_segment(self):

        with open(os.path.join(test_utils.TEST_PATH, 'data/audio_segment.m4s'), 'rb') as f:
            data = f.read()

        root = mp4.mp4(data, len(data))
        
        # mfhd
        mfhd = root.find('moof.mfhd')
        self.assertTrue(mfhd)
        self.assertEquals(mfhd.seqno, 1)
        
        # tfhd
        tfhd = root.find('moof.traf.tfhd')
        self.assertTrue(tfhd)
        self.assertEquals(tfhd.track_id, 1)
        
        # tfdt
        tfdt = root.find('moof.traf.tfdt')
        self.assertTrue(tfdt)
        self.assertEquals(tfdt.decode_time, 0)
        
        # trun
        trun = root.find('moof.traf.trun')
        self.assertTrue(trun)
        self.assertEquals(trun.sample_count, 282)

    def test_parse_video_init_segment(self):

        with open(os.path.join(test_utils.TEST_PATH, 'data/video_init.mp4'), 'rb') as f:
            data = f.read()

        root = mp4.mp4(data, len(data))
        
        # mvhd
        mvhd = root.find('moov.mvhd')
        self.assertTrue(mvhd)
        self.assertEquals(mvhd.timescale, 90000)
        self.assertEquals(mvhd.duration, 9623970)
        
        # tkhd
        tkhd = root.find('moov.trak.tkhd')
        self.assertTrue(tkhd)
        self.assertEquals(tkhd.track_id, 5)
        self.assertEquals(tkhd.duration, 9623970)
        
        # mdhd
        mdhd = root.find('moov.trak.mdia.mdhd')
        self.assertTrue(mdhd)
        self.assertEquals(mdhd.timescale, 90000)
        self.assertEquals(mdhd.duration, 9623970)
        
        # avc1
        avc1 = root.find('moov.trak.mdia.minf.stbl.stsd.avc1')
        self.assertTrue(avc1)
        self.assertEquals(avc1.width, 320)
        self.assertEquals(avc1.height, 180)
        
        # avcC
        avcC = root.find('moov.trak.mdia.minf.stbl.stsd.avc1.avcC')
        self.assertTrue(avcC)
        self.assertEquals(avcC.profile_ind, 100)
        self.assertEquals(avcC.level, 13)

    def test_parse_video_media_segment(self):

        with open(os.path.join(test_utils.TEST_PATH, 'data/video_segment.m4s'), 'rb') as f:
            data = f.read()

        root = mp4.mp4(data, len(data))
        
        # mfhd
        mfhd = root.find('moof.mfhd')
        self.assertTrue(mfhd)
        self.assertEquals(mfhd.seqno, 1)
        
        # tfhd
        tfhd = root.find('moof.traf.tfhd')
        self.assertTrue(tfhd)
        self.assertEquals(tfhd.track_id, 5)
        
        # tfdt
        tfdt = root.find('moof.traf.tfdt')
        self.assertTrue(tfdt)
        self.assertEquals(tfdt.decode_time, 0)
        
        # trun
        trun = root.find('moof.traf.trun')
        self.assertTrue(trun)
        self.assertEquals(trun.sample_count, 180)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDASHSegments)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(len(result.failures) + len(result.errors))
