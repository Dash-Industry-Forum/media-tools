#!/usr/bin/env python
"""Batch encoder of mp4 files into many different variants using ffmpeg.

Supports H.264/AVC and H.265/HEVC + AAC.
Config files shall be in JSON format, see examples provided at
https://github.com/Dash-Industry-Forum/media-tools/tree/restructure-for-distribution-packaging/python/example_configs
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
from os.path import normpath, splitext
from os.path import join as pathjoin
from os.path import split as pathsplit
import sys
import subprocess
import time
import json

FFMPEG = 'ffmpeg'
MAX_NR_PROCESSES = 4

INPUT = "-i %(inFile)s"
OUTPUT = "-y %(outFile)s"

# Audio filters are used as with the -af option. Can be concatenated with a ,
AUDIO_FILTERS = {'monops' : "pan=stereo:c0<c0+c1:c1<c0+c1"}

# Video filters are used as with the -vf option. Can be concatenated with a ,
VIDEO_FILTERS = {'deinterlace' : "yadif=0:-1:0",
                 'width' : "scale=%(width)d:-1",
                 'resolution' : "scale=%(resolution)s"}

def make_x264_options(video_values):
    """Make x264 options string from dictionary values (frameRate, vrate, gopLength, segmentDurationMs).

    From these some extra values are calculated."""
    values = video_values.copy()
    values['vbv-maxrate'] = int(values['vrate']*1.15)
    values['vbv-bufsize'] = int(values['vrate']*values['segmentDurationMs']
                                * 0.001)
    values['gopLength2'] = 2 * values['gopLength']
    options = ['-c:v libx264 -profile:v high -flags +cgop -r %(frameRate).2f']
    # Note that bitrates are in kbps (with k = 1000)
    options.append(' -force_key_frames "expr:eq(mod(n,%(gopLength)d),0)"')
    options.append(' -x264opts bitrate=%(vrate)d:vbv-maxrate=%(vbv-maxrate)d:vbv-bufsize=%(vbv-bufsize)d')
    # options.append(':scenecut=-1:keyint=%(gopLength)d:min-keyint=%(gopLength)d')
    options.append(':rc-lookahead=%(gopLength)d:keyint=%(gopLength2)d:min-keyint=%(gopLength)d')
    options.append(':force-cfr')
    out_string = "".join(options)
    return out_string % values


def make_x265_options(video_values):
    """Make x265 options string from dictionary values (frameRate, vrate, gopLength, segmentDurationMs).

    From these some extra values are calculated."""
    values = video_values.copy()
    values['vbv-maxrate'] = int(values['vrate']*1.15)
    values['vbv-bufsize'] = int(values['vrate']*values['segmentDurationMs']
                                * 0.001)
    values['gopLength2'] = 2 * values['gopLength']
    options = ['-c:v libx265 -preset medium -r %(frameRate).2f']
    # Note that bitrates are in kbps (with k = 1000)
    options.append(' -force_key_frames "expr:eq(mod(n,%(gopLength)d),0)"')
    options.append(' -x265-params bitrate=%(vrate)d:vbv-maxrate=%(vbv-maxrate)d:vbv-bufsize=%(vbv-bufsize)d')
    # options.append(':no-open-gop=1:no-scenecut=1:keyint=%(gopLength)d:min-keyint=%(gopLength)d')
    options.append(':rc-lookahead=%(gopLength)d:keyint=%(gopLength2)d:min-keyint=%(gopLength)d')
    # options.append(' -t 65')
    out_string = "".join(options)
    return out_string % values

def make_video_filter(job):
    "Create a video filter_top_boxes string."
    media_filter = ""
    filters = []
    #print job
    for k in ("deinterlace", "resolution", "width"):
        if job.has_key(k):
            filters.append(VIDEO_FILTERS[k] % job)
    if len(filters) > 0:
        media_filter = "-vf '%s'" % ",".join(filters)
    return media_filter

def make_audio_filter(job):
    "Create an audio filter_top_boxes string."
    media_filter = ""
    filters = []
    for k in AUDIO_FILTERS.keys():
        if job.has_key(k):
            filters.append(AUDIO_FILTERS[k] % job)
    if len(filters) > 0:
        media_filter = "-af '%s'" % ",".join(filters)
    return media_filter

# The audio options are Fraunhofer encoder, HE-AAC v2, 48kHz sampling, stereo
# The bitrate can be varied though

# Currently using AAC_LC since we do not fully have HE-AAC v2 support yet
AUDIO_OPTIONS = " -metadata:s:a:0 language=%(language)s -b:a %(arate)dk -ar " \
                "48000 -ac 2 -acodec libfdk_aac"
#AUDIO_OPTIONS = "-b:a %(arate)dk -ar 48000 -ac 2 -acodec libfdk_aac -profile:a aac_he"
#AUDIO_OPTIONS = "-b:a %(arate)dk -ar 48000 -ac 2 -acodec libfdk_aac -profile:a aac_he_v2"
#AUDIO_OPTIONS = "-strict -2 -c:a aac -b:a %(arate)dk -ar 48000 -ac 2"

class BatchEncoder(object):
    "Encode a batch of files."
    #pylint: disable=too-many-instance-attributes

    def __init__(self, config, infiles, outdir, max_procs, max_jobs):
        self.config = config
        self.infiles = infiles
        self.outdir = outdir
        self.max_procs = max_procs
        self.max_jobs = max_jobs
        self.jobs = []
        self.processes = []
        self.nr_jobs_started = 0
        self.nr_jobs_done = 0

    def make_joblist(self):
        """Make a list of jobs with all variants for all infiles and create outfile directories.

        The in/out mapping is file.* > outdir/variant_name/provider/file.mp4."""

        def get_task_lock_file(out_filename):
            "Get task-lock filename."
            return "%s.X" % splitext(out_filename)[0]

        def get_logfile(out_filename):
            "Get logfile name"
            return "%s.log" % splitext(out_filename)[0]

        for infile in self.infiles:
            if not os.path.exists(infile):
                print "Warning: infile %s does not exist. Skipping it" % infile
                continue
            infile_base = splitext(pathsplit(infile)[1])[0]
            for variant in self.config:
                outdir = normpath(pathjoin(self.outdir, infile_base))
                if not os.path.exists(outdir):
                    os.makedirs(outdir)
                outfile = pathjoin(outdir, variant['name'] + '.mp4')
                taskfile = get_task_lock_file(outfile)
                logfile = get_logfile(outfile)
                if os.path.exists(taskfile) or (not os.path.exists(outfile)):
                    job = {'inFile' : infile, 'outFile' : outfile, 'lockFile' : taskfile,
                           'get_logfile' : logfile}
                    job.update(variant)
                    self.jobs.append(job)
                    if len(self.jobs) == self.max_jobs:
                        break

    def start_next_job(self):
        "Start a new job as a process."
        if self.nr_jobs_started >= len(self.jobs):
            return
        job = self.jobs[self.nr_jobs_started]
        cmd_line = self.create_cmd(job)
        file_handle = open(job['get_logfile'], "w")
        file_handle.write("CMD: %s\n\n" % cmd_line)
        try:
            os.unlink(job['lockFile'])
        except OSError:
            pass
        open(job['lockFile'], "wb").write("running")
        proc = subprocess.Popen(cmd_line, shell=True, stdout=file_handle, stderr=file_handle)
        print ''
        print "> %s" % cmd_line
        self.nr_jobs_started += 1
        self.processes.append((proc, job, self.nr_jobs_started))
        print "Started job %d for %s with pid=%d" % (self.nr_jobs_started, job['outFile'], proc.pid)

    def create_cmd(self, job):
        "Create command line from dictionary of parameters."
        #pylint: disable=no-self-use
        make_video_options = (job.get('codec', "") in ("hevc", "h265")) and make_x265_options or make_x264_options
        if job['contentType'] == "video":
            spec_options = "-an %s %s" % (make_video_filter(job), make_video_options(job))
        elif job['contentType'] == "audio":
            spec_options = "-vn %s %s" %(make_audio_filter(job), AUDIO_OPTIONS)
        elif job['contentType'] == "mux":
            spec_options = "%s %s %s %s" %(make_video_filter(job), make_video_options(job),
                                           make_audio_filter(job), AUDIO_OPTIONS)
        all_options = "%s %s %s" % (INPUT, spec_options, OUTPUT)
        options = all_options % job
        cmd_line = "%s %s" % (FFMPEG, options)
        return cmd_line

    def run_jobs(self):
        "Run and monitor the jobs."
        while True:
            finished = []
            running_now = 00
            for (proc, job, nr) in self.processes:
                proc.poll()
                if proc.returncode is not None:
                    finished.append((proc, job, nr))
                    if proc.returncode != 0:
                        sys.stderr.write("Job %d with output file %s failed (%d)\n"
                                         % (nr, job['outFile'], proc.returncode))
                    else:
                        print("Job %d with output file %s succeeded" %
                              (nr, job['outFile']))
                else:
                    running_now += 1
            if len(finished) > 0:
                self.nr_jobs_done += 1
                print "%d jobs done" % self.nr_jobs_done
                for finished_job in finished:
                    proc, job, nr = finished_job
                    os.unlink(job['lockFile'])
                    self.processes.remove(finished_job)
            if running_now < self.max_procs:
                self.start_next_job()
            if len(self.processes) == 0:
                break
            time.sleep(1)
        print "All done!"

    def get_nr_jobs(self):
        "Get the number of jobs."
        return len(self.jobs)


def validate_framerate_gop_segment_duration(json_data):
    """Validate that we can get exactly the segment duration that is asked for.

    For 29.97 and 59.94, we only support gop_durations which are multiples
    of 30 (60) frames, which result in segment_durations being a multiple
    of 1001 ms."""

    def is_close(a, b):
        return abs(a - b) < 1e-8

    frame_rate = json_data['frameRate']
    gop_length = json_data['gopLength']
    seg_dur_ms = json_data['segmentDurationMs']
    if is_close(frame_rate, 29.97):
        mul30, remainder = divmod(gop_length, 30)
        if remainder != 0:
            raise ValueError("For 29.97Hz video, only GoP durations nx30 are allowed")
        if seg_dur_ms != mul30 * 1001:
            raise ValueError("Segment duration %d is not a multiple of 1001" % seg_dur_ms)
        return
    if is_close(frame_rate, 59.94):
        mul60, remainder = divmod(gop_length, 60)
        if remainder != 0:
            raise ValueError(
                "For 59.94Hz video, only GoP durations nx60 are allowed")
        if seg_dur_ms != mul60 * 1001:
            raise ValueError("Segment duration %d is not a multiple of 1001" % seg_dur_ms)
        return
    if frame_rate not in (24, 25, 30, 48, 50, 60):
        raise ValueError("Framerate %s not supported" % frame_rate)

    gop_dur_ms, remainder = divmod(gop_length * 1000, frame_rate)
    if remainder != 0:
        raise ValueError("framerate %s and gop_length %s cannot be expressed in ms" % frame_rate, gop_length)
    nr_gops_seg, remainder = divmod(seg_dur_ms, gop_dur_ms)
    if remainder != 0:
        raise ValueError("Segment duration %dms is not a multiple of gop "
                         "duration %dms" % (seg_dur_ms, gop_dur_ms))


def validate_audio_language(json_data):
    """Validate that language is present and consists of 3-letter string."""
    language = json_data.get("language", "").lower()
    if len(language) != 3:
        raise ValueError("language must be set to 3-letter code for audio.")
    for c in language:
        if not ord('a') <= ord(c) <= ord('z'):
            raise ValueError("language must be set to 3-letter code for audio.")


def parse_config(config_file):
    "Parse a json config file and make a list of all variants to produce with their options."
    txt = open(config_file, "r").read()
    json_data = json.loads(txt)
    variants = []
    for top_level in json_data:
        data = top_level.copy()
        if top_level['contentType'] == 'video':
            validate_framerate_gop_segment_duration(top_level)
        elif top_level['contentType'] == 'audio':
            validate_audio_language(top_level)
        del data['variants']
        for variant_specific in top_level['variants']:
            variant = data.copy()
            variant.update(variant_specific)
            variants.append(variant)
    return variants

def main():
    "Main function to run the script."
    import optparse
    import sys
    parser = optparse.OptionParser(usage='%prog [options] configfile infile1 [infile2 ....] outdir')
    parser.add_option('-j', action="store", dest="max_jobs", default=0, type="int")
    parser.add_option('-p', action="store", dest="max_procs", default=MAX_NR_PROCESSES, type="int",
                      help='default is [%default]')
    options, args = parser.parse_args()
    if len(args) < 3:
        print parser.print_help()
        sys.exit(1)
    config_file = args[0]
    config = parse_config(config_file)
    infiles = args[1:-1]
    print "infiles = %s" % infiles
    outdir = args[-1]
    encoder = BatchEncoder(config, infiles, outdir, options.max_procs, options.max_jobs)
    encoder.make_joblist()
    nr_jobs = encoder.get_nr_jobs()
    if nr_jobs > 0:
        print "Created %d jobs" % nr_jobs
        encoder.run_jobs()
    else:
        print "No jobs created"

if __name__ == "__main__":
    main()
