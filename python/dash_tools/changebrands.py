#!/usr/bin/env python
"""Change tfdt with the offset given."""

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

import sys
from structops import uint32_to_str, str_to_uint32

def change_brands(indata, major_brand, compatibility_brands, minor_version=0):
    "Change brands in input string indata and return new string."
    size = str_to_uint32(indata)
    ftyp = indata[4:8]
    assert ftyp == "ftyp"
    in_major_brand = indata[8:12]
    print "Changing major brand %s - > %s" % (in_major_brand, major_brand)
    in_minor_version = str_to_uint32(indata[12:16])
    print "minorVersion: %s -> %s" % (in_minor_version, minor_version)
    pos = 16
    in_compatibility_brands = []
    while pos < size:
        in_compatibility_brands.append(indata[pos:pos+4])
        pos += 4
    print "Compatibility brands: %s -> %s" % (in_compatibility_brands, compatibility_brands)

    out_size = 16 + 4*len(compatibility_brands)
    outdata = uint32_to_str(out_size) + "ftyp" + major_brand + uint32_to_str(minor_version)
    for brand in compatibility_brands:
        outdata += brand
    outdata += indata[size:]
    return outdata


def main():
    "Parse command line and call change_brands."
    in_filename = sys.argv[1]
    out_filename = sys.argv[2]
    major_brand = sys.argv[3]
    compatibility_brands = sys.argv[4:]
    indata = open(in_filename, "rb").read()
    outdata = change_brands(indata, major_brand, compatibility_brands)
    ofh = open(out_filename, "wb")
    ofh.write(outdata)


if __name__ == "__main__":
    main()
