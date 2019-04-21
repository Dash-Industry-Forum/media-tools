#!/usr/bin/env python
"""Download and parse live DASH MPD and time download corresponding media segments.

Downloads all representations in the manifest. Only works for manifest with $Number$-template.
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
import time
from threading import Thread, Lock
import signal
import urllib2
import urlparse

import mpdparser

CREATE_DIRS = True


class FileWriter(object):
    "File writer that handles standard file system."

    def __init__(self, base_dst, verbose=False):
        self.base_dst = base_dst
        self.verbose = verbose
        self.base_parts = urlparse.urlparse(base_dst)
        self.lock = Lock()

    def write_file(self, rel_path, data):
        "Write file."
        self.lock.acquire()
        try:
            self.write_to_filesystem(rel_path, data)
        finally:
            self.lock.release()

    def write_to_filesystem(self, rel_path, data):
        "Write to file system."
        if self.base_dst == "":
            return
        path = os.path.join(self.base_dst, rel_path)
        print "Writing file %s" % path
        if CREATE_DIRS:
            dir_path, _ = os.path.split(path)
            if dir_path != "" and not os.path.exists(dir_path):
                if self.verbose:
                    print "os.makedirs: %s" % dir_path
                os.makedirs(dir_path)
        with open(path, "wb") as ofh:
            ofh.write(data)


def fetch_file(url):
    "Fetch a specific file via http and return as string."
    try:
        start_time = time.time()
        data = urllib2.urlopen(url).read()
        size = len(data)
        end_time = time.time()
        start_time_tuple = time.gmtime(start_time)
        start_string = time.strftime("%Y-%m-%d-%H:%M:%S", start_time_tuple)
        print "%s  %.3fs for %8dB %s" % (start_string, end_time - start_time, size, url)
    except urllib2.HTTPError, exc:
        print "ERROR %s for %s" % (exc, url)
        data = exc.read()
    return data


class Fetcher(object):
    "Fetching a complete live DASH session. Must be stopped with interrupt."

    def __init__(self, mpd, base_url=None, file_writer=None, verbose=False):
        self.mpd = mpd
        self.base_url = base_url
        self.file_writer = file_writer
        self.verbose = verbose
        self.fetches = None
        self.threads = []
        self.interrupted = False
        self.prepare()
        signal.signal(signal.SIGINT, self.signal_handler)
        if mpd.type != "dynamic":
            print "Can only handle dynamic MPDs (live content)"
            sys.exit(1)

    def prepare(self):
        "Prepare by gathering info for each representation to download."
        availability_start_time = self.mpd.availabilityStartTime
        fetches = []
        period_start = availability_start_time + self.mpd.periods[0].start
        print("Period Start %s" % period_start)
        for adaptation_set in self.mpd.periods[0].adaptation_sets:
            if self.verbose:
                print adaptation_set
            for rep in adaptation_set.representations:
                init = adaptation_set.initialization.replace("$RepresentationID$", rep.id)
                media = adaptation_set.media.replace("$RepresentationID$", rep.id)
                rep_data = {'init' : init, 'media' : media,
                            'duration' : adaptation_set.duration,
                            'timescale' : adaptation_set.timescale,
                            'dur_s' : (adaptation_set.duration * 1.0 /
                                       adaptation_set.timescale),
                            'startNr' : adaptation_set.startNumber,
                            'periodStart' : period_start,
                            'base_url' : self.base_url,
                            'id' : rep.id}
                fetches.append(rep_data)
        self.fetches = fetches

    def signal_handler(self, a_signal, frame):
        "Stop at any signal."
        #pylint: disable=unused-argument
        self.stop()

    def stop(self):
        "Stop this thread."
        print "Stopping..."
        for thread in self.threads:
            thread.interrupt()
            self.interrupted = True

    def start_fetch(self, number_segments=-1):
        "Start a fetch."
        for fetch in self.fetches:
            init_url = os.path.join(fetch['base_url'], fetch['init'])
            data = fetch_file(init_url)
            self.file_writer.write_file(fetch['init'], data)
            thread = FetchThread("SegmentFetcher_%s" % fetch['id'], fetch, self.file_writer, number_segments, self)
            self.threads.append(thread)
            thread.start()
        self.keep_running()

    def keep_running(self):
        "Keep running so that the interrupt signal can be caught."
        while True:
            if self.interrupted:
                break
            time.sleep(0.5)


class FetchThread(Thread):
    "Thread that fetches media segments."

    def __init__(self, name, fetch, file_writer, nr_segments_to_fetch=-1, fetcher=None):
        self.fetch = fetch
        Thread.__init__(self, name=name)
        self.interrupted = False
        self.file_writer = file_writer
        self.nr_segment_to_fetch = nr_segments_to_fetch
        self.parent = fetcher

    def interrupt(self):
        "Interrupt this thread."
        self.interrupted = True

    def current_number(self, now):
        "Calculate the current segment number."
        return int((now - self.fetch['periodStart']) / self.fetch['dur_s'] + self.fetch['startNr'] - 1)

    def time_for_number(self, number):
        "Calculate the time for a specific segment number."
        return (number - self.fetch['startNr'] - 1) * self.fetch['dur_s'] + self.fetch['periodStart']

    def spec_media(self, number):
        "Return specific media path element."
        return self.fetch['media'].replace("$Number$", str(number))

    def make_media_url(self, number):
        "Make media URL"
        return os.path.join(self.fetch['base_url'], self.spec_media(number))

    def fetch_media_segment(self, number):
        "Fetch a media segment given its number."
        media_url = self.make_media_url(number)
        return fetch_file(media_url)

    def store_segment(self, data, number):
        "Store the segment to file."
        self.file_writer.write_file(self.spec_media(number), data)

    def run(self):
        "Run this thread."
        last_number = None # The last fetched number
        nr_fetched = 0
        while True:
            now = time.time()
            number = self.current_number(now)
            if last_number is not None and number - last_number > 1:
                if (now-self.time_for_number(last_number)) < 2*self.fetch['dur_s']:
                    number = last_number + 1
            if number != last_number:
                # Fetch media
                data = self.fetch_media_segment(number)
                self.store_segment(data, number)
                last_number = number
                nr_fetched += 1
            time.sleep(self.fetch['dur_s'] * 0.25)
            if self.nr_segment_to_fetch > 0 and nr_fetched >= self.nr_segment_to_fetch:
                if self.parent:
                    self.parent.stop()
            if self.interrupted:
                break


def download(mpd_url=None, mpd_str=None, base_url=None, base_dst="", number_segments=-1, verbose=False):
    "Download MPD if url specified and then start downloading segments."
    if mpd_url:
        mpd_str = fetch_file(mpd_url)
        base_url, file_name = os.path.split(mpd_url)
        file_writer = FileWriter(base_dst)
        file_writer.write_file(file_name, mpd_str)
    mpd_parser = mpdparser.ManifestParser(mpd_str)
    fetcher = Fetcher(mpd_parser.mpd, base_url, file_writer, verbose)
    if verbose:
        print fetcher.fetches
    fetcher.start_fetch(number_segments)


def main():
    "Parse command line and start the fetching."
    from optparse import OptionParser
    usage = "usage: %prog [options] mpdURL [dstDir]"
    parser = OptionParser(usage)
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose")
    parser.add_option("-b", "--base_url", dest="baseURLForced")
    parser.add_option("-n", "--number", dest="numberSegments", type="int")
    (options, args) = parser.parse_args()
    number_segments = -1
    if options.numberSegments:
        number_segments = options.numberSegments
    if len(args) < 1:
        parser.error("incorrect number of arguments")
    mpd_url = args[0]
    base_dst = ""
    if len(args) >= 2:
        base_dst = args[1]
    download(mpd_url, base_dst=base_dst, number_segments=number_segments, verbose=options.verbose)


if __name__ == "__main__":
    main()
