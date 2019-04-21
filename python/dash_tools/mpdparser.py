"""MPD parser, especially for live content (type==dynamic).
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

from xml.etree import ElementTree
import datetime
import calendar
import re

PERIOD = re.compile(r"PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)(?:.(?P<fraction>\d+))?S)?")


class MpdError(Exception):
    pass

class MpdObject(object):
    "The mother of all MPD parts. Takes an ElementTree.Node as starting point."

    def __init__(self, node, parent=None):
        self.node = node
        self.parent = parent
        self.attribs = []
        self.parse()

    def get_text_attribute(self, name):
        "Get text attribute to __dict__."
        self.attribs.append(name)
        value = self.node.attrib.get(name, None)
        self.__dict__[name] = value

    def get_int_attribute(self, name, default_value=None):
        "Get int attribute to __dict__."
        self.attribs.append(name)
        value = self.node.attrib.get(name, None)
        if value is not None:
            value = int(value)
        else:
            value = default_value
        self.__dict__[name] = value

    def get_date_attribute(self, name):
        "Get date attribute to __dict__."
        self.attribs.append(name)
        value = self.node.attrib.get(name, None)
        if value is not None:
            if value.endswith("Z"):
                value = value[:-1]
            date = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
            value = float(calendar.timegm(date.timetuple()))
        self.__dict__[name] = value

    def get_period_attribute(self, name):
        "Get period attribute to __dict__ and store as seconds."
        self.attribs.append(name)
        value = self.node.attrib.get(name, None)
        if value is not None:
            mobj = PERIOD.match(value)
            if mobj:
                dur = 0
                g_dict = mobj.groupdict()
                if g_dict['hours'] is not None:
                    dur += 3600*int(g_dict['hours'])
                if g_dict['minutes'] is not None:
                    dur += 60*int(g_dict['minutes'])
                if g_dict['seconds'] is not None:
                    dur += int(g_dict['seconds'])
                if g_dict['fraction'] is not None:
                    dur += float("0."+g_dict['fraction'])
                value = dur
            else:
                raise Exception("Cannot interpret period %s" % value)
        self.__dict__[name] = value

    def parse(self):
        "Parse the node of the subclass (abstract)."
        #pylint: disable=no-self-use
        raise MpdError("Not implemented")

    def __str__(self):
        fmt = ", ".join(["%s=%%(%s)s" % (v, v) for v in self.attribs])
        return "[%s]: %s" % (self.__class__.__name__, fmt % self.__dict__)



class Mpd(MpdObject):
    "MPD toplevel"

    def parse(self):
        self.periods = []
        self.get_text_attribute('type')
        self.get_date_attribute('availabilityStartTime')
        for child in self.node:
            if child.tag.endswith("Period"):
                self.periods.append(Period(child, self))


class Period(MpdObject):
    "MPD Period"

    def parse(self):
        "Parse the Period node."
        self.adaptation_sets = []
        self.get_period_attribute('start')
        for child in self.node:
            if child.tag.endswith("AdaptationSet"):
                self.adaptation_sets.append(AdaptationSet(child, self))


class AdaptationSet(MpdObject):
    "MPD AdaptationSet"

    def parse(self):
        self.get_text_attribute('mimeType')
        self.get_text_attribute('contentType')
        self.representations = []
        for child in self.node:
            if child.tag.endswith("SegmentTemplate"):
                self.segment_template = SegmentTemplate(child, self)
                for attr in self.segment_template.attribs:
                    self.__dict__[attr] = getattr(self.segment_template, attr)
                self.attribs.extend(self.segment_template.attribs)
            if child.tag.endswith("Representation"):
                self.representations.append(Representation(child, self))

class SegmentTemplate(MpdObject):
    "MPD SegmentTemplate"

    def parse(self):
        self.get_int_attribute('duration')
        self.get_int_attribute('timescale', 1)
        self.get_int_attribute('startNumber', 1)
        self.get_text_attribute('media')
        self.get_text_attribute('initialization')

class Representation(MpdObject):
    "MPD Representation"

    def parse(self):
        "Parse the Representation and get relevant attributes."
        self.get_text_attribute('id')


class ManifestParser(object):
    "Top-level Manifest Parser."
    #pylint: disable=too-few-public-methods

    def __init__(self, manifest_str):
        "Takes a manifest as string and parse it."
        self.manifest_str = manifest_str
        self.root = ElementTree.fromstring(self.manifest_str)
        self.mpd = Mpd(self.root)
