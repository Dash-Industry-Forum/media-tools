/*
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
*/

$(document).ready(function ()
{
    //console.log("document ready");

    Start();

    document.getElementById('files').addEventListener('change', handleFileSelect, false);
    document.getElementById('url').addEventListener('keydown', handleUrlSelect, false);

    // Setup the dnd listeners.
    var dropZone = document.getElementById('drop_zone');
    dropZone.addEventListener('dragover', handleDragOver, true);
    dropZone.addEventListener('drop', handleFileDrop, true);
});

function Start()
{
	// Check for the various File API support.
    if (window.File && window.FileReader && window.FileList && window.Blob) {
      // Great success! All the File APIs are supported.
    } else {
      alert('The File APIs are not fully supported in this browser.');
    }
}

function handleFile(evt, files)
{
    // files is a FileList of File objects. List some properties.
    var output = [];
    for (var i = 0, f; f = files[i]; i++)
    {
        output.push('<li><strong>', escape(f.name), '</strong> (', f.type || 'n/a', ') - ',
                    f.size, ' bytes, last modified: ',
                    f.lastModifiedDate ? f.lastModifiedDate.toLocaleDateString() : 'n/a',
                    '</li>');
    }

    document.getElementById('list').innerHTML = '<ul>' + output.join('') + '</ul>';
}

function displayError(msg)
{
    var messages = document.getElementById('messages')
    
    var div = document.createElement('div');
    div.style.color='red';
    $(div).append(document.createTextNode(msg));
    $(messages).append(div);
}

function handleFileSelect(evt)
{
    var files = evt.target.files; // FileList object
    //handleFile(evt, files);
    handleFile2(evt, files);
}

function handleUrl(url)
{
    var progress = document.querySelector('.percent');

    // Reset progress indicator on new URL selection.
    progress.style.width = '0%';
    progress.textContent = '0%';
    document.getElementById('progress_bar').className = 'loading';

	$.support.cors = true;
	$.ajax({
        type: 'GET',
        url: url,
        //dataType: 'binary',
        mimeType: 'text/plain; charset=x-user-defined',

        complete: function(data)
        {
            // Ensure that the progress bar displays 100% at the end.
            progress.style.width = '100%';
            progress.textContent = '100%';
            setTimeout("document.getElementById('progress_bar').className='';", 2000);

            handleData(data.responseText);
        },
        xhrFields:
        {
            onprogress: function(e)
            {
                updateProgress(e);
            }
        }
    });
}

function handleUrlSelect(evt)
{
    if (evt.keyCode != 13)
    {
        return;
    }

    var url = evt.target.value;
    // Special rewrite trick needed for URL inserted for our server setup
    var hostname = window.location.hostname;
    var finalurl = 'http://' + hostname +'/rewrite/' + url;
    handleUrl(finalurl);
}

function handleFileDrop(evt)
{
    evt.stopPropagation();
    evt.preventDefault();

    var files = evt.dataTransfer.files; // FileList object.
    handleFile2(evt, files);
}

function handleDragOver(evt)
{
    evt.stopPropagation();
    evt.preventDefault();
    evt.dataTransfer.dropEffect = 'copy'; // Explicitly show this is a copy.
}

var reader;

function abortRead()
{
    if (reader)
    {
        reader.abort();
    }
}

function errorHandler(evt)
{
    switch(evt.target.error.code)
    {
        case evt.target.error.NOT_FOUND_ERR:
            alert('File Not Found!');
            break;
        case evt.target.error.NOT_READABLE_ERR:
            alert('File is not readable');
            break;
        case evt.target.error.ABORT_ERR:
            break; // noop
        default:
            alert('An error occurred reading this file.');
    };
 }

function updateProgress(evt)
{
    var progress = document.querySelector('.percent');

    // evt is an ProgressEvent.
    if (evt.lengthComputable)
    {
        var percentLoaded = Math.round((evt.loaded / evt.total) * 100);
        // Increase the progress bar length.
        if (percentLoaded < 100)
        {
            progress.style.width = percentLoaded + '%';
            progress.textContent = percentLoaded + '%';
        }
    }
}

function getIntAt( arr, offs )
{
    return (arr[offs+0] << 24) +
           (arr[offs+1] << 16) +
           (arr[offs+2] << 8) +
           arr[offs+3];
}

function hex2a(hex)
{
    var str = '';
    for (var i = 0; i < hex.length; i += 2)
        str += String.fromCharCode(parseInt(hex.substr(i, 2), 16));
    return str;
}

var containers = ['moov',
                  'moof',
                  'trak',
                  'traf',
                  'tfad',
                  'mvex',
                  'mdia',
                  'minf',
                  'dinf',
                  'stbl',
                  'stsd',
                  'sinf',
                  'mfra',
                  'udta',
                  'meta',
                  'schi',
                  'avc1',
                  'avc3',
                  'hvc1',
                  'hev1',
                  'mp4a',
                  'encv',
                  'enca',
                  'skip',
                  'edts'];

var containersWithContent = ['stsd', 'avc1', 'avc3', 'hvc1', 'hev1', 'mp4a', 'encv', 'enca'];

function searchStringInArray (str, strArray)
{
    for (var j=0; j<strArray.length; j++)
    {
        //console.log("cmp: " + strArray[j] + " " + str);
        try
        {
            if (strArray[j].match(str))
            {
                return j;
            }
        }
        catch(err)
        {
            return -1;
        }
    }
    return -1;
}

DataView.prototype.getUTF8String = function(offset, length)
{
    var utf16 = new ArrayBuffer(length * 2);
    var utf16View = new Uint16Array(utf16);
    for (var i = 0; i < length; ++i) {
        utf16View[i] = this.getUint8(offset + i);
    }
    return String.fromCharCode.apply(null, utf16View);
};

function trim1(str)
{
    return str.replace(/^\s\s*/, '').replace(/\s\s*$/, '');
}

var boxData;

function getUint64(data, offset){
    var dat = data.getUTF8String(offset, 8);
    var str = '0x' + binStringToHex2(dat);

    // Using BigInteger
    var n1 = BigInteger(str);
    return n1
}

function getUint48(data, offset){
    var dat = data.getUTF8String(offset, 6);
    var str = '0x' + binStringToHex2(dat);

    // Using BigInteger
    var n1 = BigInteger(str);
    return n1
}

function getIntAsHex(data, offset, len) {
    var dat = data.getUTF8String(offset, len);
    var str = '0x' + binStringToHex2(dat);
    return str
}

function parseBoxes(dataView, offset, size, jsonData, indent)
{
    while (offset < size)
    {
        var len = dataView.getUint32(offset);
        var type = dataView.getInt32(offset + 4)
        var typeStr = hex2a(type.toString(16));
        typeStr = trim1(typeStr);

        if (len == 1)
        {
            // Extended size
            len = getUint64(dataView, offset + 8);
        }

        //console.log("Got box: " + typeStr + " of size: " + len);

        if (len > size)
        {
            if (jsonData.length == 0)
            {
                // No box found at the start, probably garbage input.
                return 0;
            }
            
            console.log("Bad box len for " + typeStr + "... The file may be truncated.");
            console.log("Original box len: " + len + "(0x" + len.toString(16) + ")");
            len = size - offset;  // adjusting the len to finish parsing with error message on the console
            console.log("Remaining buffer size: " + len + "(0x" + len.toString(16) + ")");
        }
        else if (len == 0)
        {
            if (jsonData.length == 0)
            {
                // No box found at the start, probably garbage input.
                return 0;
            }
            
            console.log("Zero box len for " + typeStr + ', offset = 0x' + offset.toString(16) + '(' + offset + ')');
        }

        var map = {}
        map["type"] = typeStr;
        map["size"] = len;
        map["offset"] = offset;
        map["children"] = [];
        jsonData.push(map);

        var childOffset = offset + 8;
        var fknName = 'box_' + typeStr;

        try
        {
            if (searchStringInArray(typeStr, containers) < 0 ||
                searchStringInArray(typeStr, containersWithContent) >= 0)
            {
                desc = executeFunctionByName(fknName, window, dataView, childOffset, len - 8);
                childOffset = desc['childOffset'];
                map["desc"] = desc['text'];
                map['boxContent'] = desc['boxContent'];
            }
        }
        catch(err)
        {
            console.log('Can not find function for ' + fknName + ' ' + err);
        }

        if (searchStringInArray(typeStr, containers) >= 0)
        {
            var childEnd = offset + len;
            parseBoxes(dataView, childOffset, childEnd, map["children"], indent + 1);
        }

        offset = offset + len;
    }

    if (offset != size)
    {
        console.log('Parsing ended at: ' + offset + ' but filesize is: ' + size);
    }

    return offset;
}

function box(type, len, offset, data)
{
    this.type = type;
    this.len = len;
    this.offset = offset;
    this.data = data;
}

box.prototype.description = function() {
    return this.type + ' ' + this.len;
};

function binStringToHex2(s) {
    var s2 = new Array(s.length), c;
    for (var i = 0, l = s.length; i < l; ++i) {
        c = s.charCodeAt(i);
        s2[i * 2] = (c >> 4).toString(16);
        s2[i * 2 + 1] = (c & 0xF).toString(16);
    }
    var s3 = String.prototype.concat.apply('', s2);
    return s3;
}

function binStringToHex3(s) {
    var s2 = new Array(s.length), c;
    for (var i = 0; i < s.length; ++i) {
        c = s.charCodeAt(i);

        if (s[i] == '<') {
            s2[i] = '&lt;';
        } else if (s[i] == '>') {
            s2[i] = '&gt;';
        } else if (c < 33 || c > 126) {
            s2[i] = '.';
        }
        else {
            s2[i] = s[i];
        }
    }
    var s3 = String.prototype.concat.apply('', s2);
    return s3;
}

function box_free(data, offset, len) {
    var boxContent = {};
    boxContent = {}
    return {'boxContent': boxContent,
            'childOffset' : offset};
}

function box_typ(data, offset, len) {
    var boxContent = {};
    var x = offset;

    boxContent['Major brand'] = data.getUTF8String(x, 4);
    x += 4;

    var ver = data.getUint32(x); x += 4;
    boxContent['Minor version'] = '0x' + ver.toString(16);

    boxContent['Compatible brands'] = new Array();
    var num_brands = (len - 8) / 4;
    for (var i = 0; i < num_brands; ++i)
    {
        boxContent['Compatible brands'].push(data.getUTF8String(x, 4));
        x += 4;
    }

    return {'boxContent': boxContent,
            'childOffset' : offset + 8};
}

function box_ftyp(data, offset, len) {
    return box_typ(data, offset, len);
}

function box_styp(data, offset, len) {
    return box_typ(data, offset, len);
}

function box_mvhd(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v= data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x+1) << 16) + (data.getUint8(x+2) << 8) + (data.getUint8(x+3) << 0);
    x += 4;

    boxContent['Box flags'] = '0x' + f.toString(16);

    var creation_time = (v == 0) ? data.getUint32(x) : getUint64(data, x);
    x += (v == 0) ? 4 : 8;
    boxContent['Creation time'] = creation_time.toString();

    var mod_time = (v == 0) ? data.getUint32(x) : getUint64(data, x);
    x += (v == 0) ? 4 : 8;
    boxContent['Modification time'] = mod_time.toString();

    var timescale = data.getUint32(x); x += 4;
    boxContent.Timescale = timescale;

    var dur = (v == 0) ? data.getUint32(x) : getUint64(data, x);
    x += (v == 0) ? 4 : 8;

    var dur2 = BigInteger.divide(dur, timescale);
    boxContent.Duration = dur.toString() + ' (' + dur2 + ' sec)';

    return {'boxContent' : boxContent,
            'childOffset' : offset + 8};
}

function box_tkhd(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    var creation_time = (v == 0) ? data.getUint32(x) : getUint64(data, x);
    x += (v == 0) ? 4 : 8;
    boxContent['Creation time'] = creation_time.toString();

    var mod_time = (v == 0) ? data.getUint32(x) : getUint64(data, x);
    x += (v == 0) ? 4 : 8;
    boxContent['Modification time'] = mod_time.toString();

    var track_id = data.getUint32(x); x += 4;
    boxContent['Track id'] = track_id;

    // reserved
    x += 4;

    var dur = (v == 0) ? data.getUint32(x) : getUint64(data, x);
    x += (v == 0) ? 4 : 8;
    boxContent.Duration = dur.toString();

    data.getUint32(x); x+= 4; // reserved
    data.getUint32(x); x+= 4; // reserved

    data.getUint16(x); x+= 2; // layer
    data.getUint16(x); x+= 2; // alternate_group
    data.getUint16(x); x+= 2; // volume
    data.getUint16(x); x+= 2; // reserved

    data.getUint32(x); x+= 4; // matrix
    data.getUint32(x); x+= 4; // matrix
    data.getUint32(x); x+= 4; // matrix
    data.getUint32(x); x+= 4; // matrix
    data.getUint32(x); x+= 4; // matrix
    data.getUint32(x); x+= 4; // matrix
    data.getUint32(x); x+= 4; // matrix
    data.getUint32(x); x+= 4; // matrix
    data.getUint32(x); x+= 4; // matrix

    var width = data.getUint32(x) >> 16; x+= 4; // width
    var height = data.getUint32(x) >> 16; x+= 4; // height

    boxContent['width'] = width.toString();
    boxContent['height'] = height.toString();

    return {'boxContent': boxContent,
            'childOffset' : offset + 8};
}

function box_mdhd(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    var creation_time = (v == 0) ? data.getUint32(x) : getUint64(data, x);
    x += (v == 0) ? 4 : 8;
    boxContent['Creation time'] = creation_time.toString();

    var mod_time = (v == 0) ? data.getUint32(x) : getUint64(data, x);
    x += (v == 0) ? 4 : 8;
    boxContent['Modification time'] = mod_time.toString();

    var timescale = data.getUint32(x); x += 4;
    boxContent['Timescale'] = timescale;

    var dur = (v == 0) ? data.getUint32(x) : getUint64(data, x);
    x += (v == 0) ? 4 : 8;
    var dur2 = BigInteger.divide(dur, timescale);
    boxContent.Duration = dur.toString() + ' (' + dur2.toString() + ' sec)';

    return {'boxContent': boxContent,
            'childOffset' : offset + 8};
}

function box_mdhd(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    var creation_time = (v == 0) ? data.getUint32(x) : getUint64(data, x);
    x += (v == 0) ? 4 : 8;
    boxContent['Creation time'] = creation_time.toString();

    var mod_time = (v == 0) ? data.getUint32(x) : getUint64(data, x);
    x += (v == 0) ? 4 : 8;
    boxContent['Modification time'] = mod_time.toString();

    var timescale = data.getUint32(x); x += 4;
    boxContent['Timescale'] = timescale;

    var dur = (v == 0) ? data.getUint32(x) : getUint64(data, x);
    x += (v == 0) ? 4 : 8;
    var dur2 = BigInteger.divide(dur, timescale);
    boxContent.Duration = dur.toString() + ' (' + dur2.toString() + ' sec)';

    return {'boxContent': boxContent,
            'childOffset' : offset + 8};
}

function box_mehd(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box name'] = "Movie Extends Box";
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;

    if (v == 1) {
        boxContent['fragment_duration'] = getUint64(data, x); x += 8;
    } else  {
        boxContent['fragment_duration'] = data.getUint32(x); x += 4;
    }

    return {'boxContent': boxContent,
            'childOffset' : offset + 8};
}

function box_hdlr(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box name'] = "Handler Box";
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;

    var pre_defined = data.getUint32(x); x += 4;
    boxContent['handler_type'] = data.getUint32(x); x += 4;
    var reserved = data.getUint32(x); x += 4;

    boxContent['name'] = data.getUTF8String(x, len-(x-offset));

    return {'boxContent': boxContent,
            'childOffset' : offset + 8};
}

function box_stsd(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    var entries = data.getUint32(x);
    x += 4;
    boxContent.Entries = entries;

    return {'boxContent': boxContent,
            'childOffset' : offset + 8};
}

function box_sampletable(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    var entries = data.getUint32(x);
    x += 4;
    boxContent.Entries = entries;

    return {'boxContent': boxContent,
            'childOffset' : offset};
}

function box_stss(data, offset, len) {
    return box_sampletable(data, offset, len);
}

function box_ctts(data, offset, len) {
   return box_sampletable(data, offset, len);
}

function box_stts(data, offset, len) {
    return box_sampletable(data, offset, len);
}

function box_stsc(data, offset, len) {
    return box_sampletable(data, offset, len);
}

function box_stsz(data, offset, len) {
    return box_sampletable(data, offset, len);
}

function box_stco(data, offset, len) {
    return box_sampletable(data, offset, len);
}

function box_dref(data, offset, len) {
    var boxContent = {};
    boxContent.dref = data.getUTF8String(offset, len);
    return {'boxContent': boxContent,
            'childOffset' : offset};
}

function box_avcx(data, offset, len) {
    var boxContent = {};
    x = offset + 8; // Sample entry
    x += 16; // Visual sample entry

    boxContent.Width = data.getUint16(x); x += 2;
    boxContent.Height = data.getUint16(x); x += 2;

    return {'boxContent': boxContent,
            'childOffset' : x + 16 + 34};
}

function box_avc1(data, offset, len) {
    return box_avcx(data, offset, len);
}

function box_avc3(data, offset, len) {
    return box_avcx(data, offset, len);
}

function box_encv(data, offset, len) {
    return box_avc1(data, offset, len);
}

function box_hvc1(data, offset, len) {
    return box_avcx(data, offset, len);
}

function box_hev1(data, offset, len) {
    return box_avcx(data, offset, len);
}

function box_avcC(data, offset, len) {
    var boxContent = {};
    x = offset

    boxContent['Version'] = data.getUint8(x); x += 1;
    var profileInd = data.getUint8(x); x += 1;
    var profileCom = data.getUint8(x); x += 1;
    boxContent.Profile = '0x(' + profileInd.toString(16) + ' ' + profileCom.toString(16) + ')';
    var level = data.getUint8(x); x += 1;
    boxContent.Level = '0x' + level.toString(16);
    x++;

    var tmp1 = data.getUint8(x); x += 1;
    var numSps = tmp1 & 0x1f;
    boxContent.SPS = new Array();

    for (var i = 0; i < numSps; ++i)
    {
        var spsSize = data.getUint16(x); x += 2;
        var sps = data.getUTF8String(x, spsSize); x += spsSize;
        boxContent.SPS.push('0x' + binStringToHex2(sps));
        //console.log("SPS=" + sps);
    }

    boxContent.PPS = new Array();
    var numPps = data.getUint8(x); x += 1;
    for (var i = 0; i < numPps; ++i)
    {
        var ppsSize = data.getUint16(x); x += 2;
        var pps = data.getUTF8String(x, ppsSize); x += ppsSize;
        boxContent.PPS.push('0x' + binStringToHex2(pps));
        //console.log("PPS=" + pps);
    }

    return {'boxContent': boxContent,
            'childOffset' : offset};
}

function box_hvcC(data, offset, len) {
    var boxContent = {};
    x = offset
    var tmp;
    boxContent['configurationVersion'] = data.getUint8(x); x += 1;
    boxContent['generalConfigFlags'] = getIntAsHex(data, x, 1); x += 1;
    boxContent['generalProfileCompatibilityFlags'] = getIntAsHex(data, x, 4); x += 4;
    boxContent['generalConstraintIndicatorFlags'] = getIntAsHex(data, x, 6);
    x += 6;
    boxContent['generalLevelIDC'] = data.getUint8(x); x += 1;
    tmp = data.getUint16(x); x += 2;
    boxContent['minSpatialSegmentationIDC'] = tmp & 0xfff;
    tmp =  data.getUint8(x); x += 1;
    boxContent['parallelismType'] = tmp & 0x3;
    tmp =  data.getUint8(x); x += 1;
    boxContent['chromaFormat'] = tmp % 0x3;
    tmp =  data.getUint8(x); x += 1;
    boxContent['bitDepthLumaMinus8'] = tmp & 0x7;
    tmp =  data.getUint8(x); x += 1;
    boxContent['bitDepthChromaMinus8'] = tmp & 0x7;

    boxContent['avgFrameRate'] = data.getUint16(x); x += 2;
    tmp = data.getUint8(x); x += 1;
    var numOfArrays = data.getUint8(x); x += 1;
    boxContent.arrays = new Array();

    for (var j = 0; j < numOfArrays ; j++) {
        var tmp2 = data.getUint8(x); x += 1;
        var array = {}
        array['completeNess'] = (tmp2 >> 7) & 1;
        var nalUnitType = tmp2 & 0x3f;
        if (nalUnitType == 32) {
            array['nalUnitType'] = "VPS_NUT (32)";
        } else if (nalUnitType == 33) {
            array['nalUnitType'] = "SPS_NUT (33)";
        } else if (nalUnitType == 34) {
            array['nalUnitType'] = "PPS_NUT (34)";
        } else if (nalUnitType == 39) {
            array['nalUnitType'] = "PREFIX_SEI_NUT (39)";
        } else {
            array['nalUnitType'] = "NON-ALLOWED TYPE (" + nalUnitType + ")";
        }

        var numNalus = data.getUint16(x); x += 2;
        var nalus = new Array();
        for (var i = 0; i < numNalus ; i++) {
            var nalUnitLength = data.getUint16(x); x += 2;
            var nalUnit = data.getUTF8String(x, nalUnitLength); x += nalUnitLength;
            nalus.push('0x' + binStringToHex2(nalUnit));
        }
        array['NALUs'] = nalus
        boxContent.arrays.push(array);
    }

    return {'boxContent': boxContent,
        'childOffset' : offset};
}

function box_pasp(data, offset, len) {
    var boxContent = {};
    x = offset;
    boxContent['name'] = "Pixel Aspect Ratio Box";
    boxContent['hSpacing'] = data.getUint32(x); x += 4;
    boxContent['vSpacing'] = data.getUint32(x); x += 4;

    return {'boxContent': boxContent,
            'childOffset' : x + 16 + 34};
}

function box_mp4a(data, offset, len) {
    var boxContent = {};
    x = offset + 8; // Sample entry
    x += 8; // Audio sample entry

    boxContent.Channels = data.getUint16(x); x += 2;
    boxContent['Sample size'] = data.getUint16(x); x += 2;
    x += 4;
    boxContent['Sample rate'] = data.getUint32(x) >>> 16; x += 4;

    return {'boxContent': boxContent,
            'childOffset' : x};
}

function box_enca(data, offset, len) {
    return box_mp4a(data, offset, len);
}

/**
 Get length of zero-terminated string (including the zero)
 */
function _get_string_len(data, offset, maxlen) {
    var pos = offset;
    var length = maxlen;
    while (pos < offset + maxlen) {
        if (data.getUint8(pos) == 0) {
            length = pos - offset + 1;
            break;
        }
        pos++;
    }
    return length;
}

function box_stpp(data, offset, len) {
    var boxContent = {};
    boxContent['Box name'] = "XML Subtitle Sample Entry"
    var x = offset + 8; // Sample entry

    var strLength = _get_string_len(data, x, len-(x-offset))
    boxContent['namespace'] = data.getUTF8String(x, strLength-1);
    x += strLength;

    strLength = _get_string_len(data, x, len-(x-offset))
    boxContent['schema_location'] = data.getUTF8String(x, strLength-1);
    x += strLength;

    strLength = _get_string_len(data, x, len-(x-offset))
    boxContent['auxiliary_mime_types'] = data.getUTF8String(x, strLength-1);
    x += strLength;

    return {'boxContent': boxContent,
            'childOffset' : x};
}

function box_emsg(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    var strLength = _get_string_len(data, x, len-(x-offset));
    boxContent['scheme_id_uri'] = data.getUTF8String(x, strLength-1);
    x += strLength;

    strLength = _get_string_len(data, x, len-(x-offset));
    boxContent['value'] = data.getUTF8String(x, strLength-1);
    x += strLength;

    boxContent['timescale'] = data.getUint32(x); x += 4;

    boxContent['presentation_time_delta'] = data.getUint32(x); x += 4;

    boxContent['event_duration'] = data.getUint32(x); x += 4;

    boxContent['id'] = data.getUint32(x); x += 4;

    boxContent['message_data'] = data.getUTF8String(x, len-(x-offset));

    return {'boxContent': boxContent,
            'childOffset' : offset};
}

function box_sidx(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var version = data.getUint8(x);
    boxContent['Box version'] = version;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    //boxContent['Box flags'] = '0x' + f.toString(16);

    boxContent['reference_ID'] = data.getUint32(x); x += 4;
    boxContent['timescale'] = data.getUint32(x); x += 4;

    if (version == 0) {
        boxContent['earliest_presentation_time'] = data.getUint32(x); x += 4;
        boxContent['first_offset'] = data.getUint32(x); x += 4;
    } else {
        boxContent['earliest_presentation_time'] = getUint64(data, x); x += 8;
        boxContent['first_offset'] = getUint64(data, x); x += 8;
    }

    var reserved = data.getUint16(x) ; x += 2;
    var reference_count = data.getUint16(x); x += 2;

    boxContent.Entries = new Array();

    while (reference_count--) {
        var entry = {};
        var fourBytes = data.getUint32(x); x += 4;
        entry['reference_type'] = (fourBytes >> 31) & 1;
        entry['referenced_size'] = (fourBytes & 0x7fffffff);
        entry['subsegment_duration'] = data.getUint32(x); x += 4;
        fourBytes = data.getUint32(x); x += 4;
        entry['starts_with_SAP'] = (fourBytes >> 31) & 1;
        entry['SAP_type'] = (fourBytes >> 29) & 7;
        entry['SAP_delta_time'] = (fourBytes & 0x0fffffff);
        boxContent.Entries.push(entry);
    }

    return {'boxContent': boxContent,
            'childOffset' : offset};
}

function getDescriptorLen(data, offset)
{
    var tmp = data.getUint8(offset); offset++;
    var len = 0;
    while (tmp & 0x80)
    {
        len = ((len << 7) | (tmp & 0x7f));
        tmp = data.getUint8(offset); offset++;
    }

    len = ((len << 7) | (tmp & 0x7f));

    return {x:len, y:offset};
}

function box_esds(data, offset, len) {
    var boxContent = {};
    x = offset;

    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    var tag = data.getUint8(x); x += 1;
    if (tag == 3)
    {
        z = getDescriptorLen(data, x);
        x = z.y;
        x += 3; // Not interested in this now

        var tag = data.getUint8(x); x += 1;
        if (tag == 4)
        {
            z = getDescriptorLen(data, x);
            x = z.y;
            x += 13; // Not interested in this now

            var tag = data.getUint8(x); x += 1;
            if (tag == 5)
            {
                z = getDescriptorLen(data, x);
                x = z.y;
                decoderConfigLen = z.x;

                var decoderConfig = data.getUTF8String(x, decoderConfigLen); x += decoderConfigLen;
                boxContent['Decoder config'] = '0x' + binStringToHex2(decoderConfig);

            }
        }
    }

    return {'boxContent': boxContent,
            'childOffset' : offset};
}

function box_trex(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    boxContent['Track id'] = data.getUint32(x); x += 4;
    boxContent['Sample description index']= data.getUint32(x); x += 4;
    boxContent['Sample duration'] = data.getUint32(x); x += 4;
    boxContent['Sample size'] = data.getUint32(x); x += 4;
    boxContent['Sample flags'] = data.getUint32(x); x += 4;


    return {'boxContent': boxContent,
            'childOffset' : offset};
}

function box_tfra(data, offset, len) {
    var boxContent = {};

    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    boxContent['Track id'] = data.getUint32(x); x += 4;

    var reserved_and_flags = data.getUint32(x); x += 4;
    var length_size_of_traf_num = (reserved_and_flags >> 4) & 3;
    var length_size_of_trun_num = (reserved_and_flags >> 2) & 3;
    var length_size_of_sample_num = reserved_and_flags & 3;

    var entries = data.getUint32(x); x += 4;

    boxContent.Entries = new Array();

    var traf_number, trun_number, sample_number;

    while (entries--) {
        var entry = {};
        var time_value = 0;
        var offset = 0;
        if (v == 0) {
            time_value = data.getUint32(x); x += 4;
            offset     = data.getUint32(x); x += 4;
        } else {
            time_value = getUint64(data, x); x += 8;
            offset     = getUint64(data, x); x += 8;
        }
        entry['Time'] = time_value.toString();
        entry['Offset'] = offset;

        if (length_size_of_traf_num == 0) {
            traf_number = data.getUint8(x); x += 1;
        } else if (length_size_of_traf_num == 1) {
            traf_number = data.getUint16(x); x += 2;
        } else if (length_size_of_traf_num == 3) {
            traf_number = data.getUint32(x); x += 4;
        } else {
            console.log("Cannot handle 24-bit traf_num")
        }

        if (length_size_of_trun_num == 0) {
            trun_number = data.getUint8(x); x += 1;
        } else if (length_size_of_trun_num == 1) {
            trun_number = data.getUint16(x); x += 2;
        } else if (length_size_of_trun_num == 3) {
            trun_number = data.getUint32(x); x += 4;
        } else {
            console.log("Cannot handle 24-bit trun_num")
        }

        if (length_size_of_sample_num == 0) {
            sample_number = data.getUint8(x); x += 1;
        } else if (length_size_of_sample_num == 1) {
            sample_number = data.getUint16(x); x += 2;
        } else if (length_size_of_sample_num == 3) {
            sample_number = data.getUint32(x); x += 4;
        } else {
            console.log("Cannot handle 24-bit sample_num")
        }

        entry['traf#'] = traf_number
        entry['trun#'] = trun_number
        entry['sample#'] = sample_number
        boxContent.Entries.push(entry)
    }

    return {
        'boxContent': boxContent,
        'childOffset': offset
    };
}

function box_mfro(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    var s = data.getUint32(x); x += 4;
    boxContent.Size = '0x' + s.toString(16) + ' (' + s + ')';

    return {'boxContent': boxContent,
            'childOffset': offset
    };
}

function box_vmhd(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    boxContent['graphics mode'] = data.getUint16(x); x += 2;

    return {'boxContent': boxContent,
            'childOffset' : offset};
}

function box_smhd(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    boxContent.Balance = data.getUint16(x); x += 2;

    return {'boxContent': boxContent,
            'childOffset' : offset};
}

function box_sthd(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box name'] = "Subtitle media header"
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;

    return {'boxContent': boxContent,
            'childOffset' : offset};
}


function box_mfhd(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    boxContent['Sequence number'] = data.getUint32(x); x += 4;

    return {'boxContent': boxContent,
            'childOffset' : offset};
}

function box_tfhd(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    boxContent['Track id'] = data.getUint32(x); x += 4;

    var tmp = -1;
    if (f & 0x01)
    {
        tmp = getUint64(data, x); x += 8;
        boxContent['Base data offset'] = tmp.toString();
    }
    if (f & 0x02) {
        tmp = data.getUint32(x); x += 4;
        boxContent['Sample Description Index'] = tmp.toString();
    }
    if (f & 0x08) {
        tmp = data.getUint32(x); x += 4;
        boxContent['Default Sample Duration'] = tmp.toString();
    }
    if (f & 0x10) {
        tmp = data.getUint32(x); x += 4;
        boxContent['Default Sample Size'] = tmp.toString();
    }
    if (f & 0x20) {
        tmp = data.getUint32(x); x += 4;
        boxContent['Default Sample Flags'] = '0x' + tmp.toString(16);
    }
    if (f & 0x10000) {
        boxContent['Duration-is-empty'] = true;
    }
    if (f & 0x20000) {
        boxContent['Default-base-is-moof'] = true;
    }

    return {'boxContent': boxContent,
            'childOffset' : offset};
}

function box_tfdt(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    var decode_time = (v == 0) ? data.getUint32(x) : getUint64(data, x);
    x += (v == 0) ? 4 : 8;

    boxContent['Decode time'] = decode_time.toString();

    return {'boxContent': boxContent,
            'childOffset' : offset};
}

function box_trun(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    var has_data_offset = f & 0x0001;
    var has_first_sample_flags = f & 0x0004;
    var has_sample_duration = f & 0x0100;
    var has_sample_size = f & 0x0200;
    var has_sample_flags = f & 0x0400;
    var has_sample_composition_time_offset = f & 0x0800;

    var sample_count = data.getUint32(x); x+= 4;
    var data_offset = 0
    var first_sample_flags = 0

    if (has_data_offset)
    {
        data_offset = data.getInt32(x); x += 4;
        boxContent.Offset = data_offset;
    }

    if (has_first_sample_flags)
    {
        var first_sample_flags = data.getUint32(x); x += 4;
        boxContent['First sample flags'] = first_sample_flags;
    }

    var sample_row_size = (has_sample_duration && 4) + (has_sample_size && 4) + (has_sample_flags && 4) + (has_sample_composition_time_offset && 4);

    boxContent.Samples = new Array();
    var t_dur = 0;
    for (var k = 0; k < sample_count; ++k)
    {
        var sample = {};

        var sample_duration = -1;
        var sample_size = -1;
        var sample_flags = -1;
        var sample_composition_time_offset = -1;

        if (has_sample_duration) {
            var sample_duration = data.getUint32(x); x += 4;
            sample['Duration'] = sample_duration;
            t_dur += sample_duration;
        }

        if (has_sample_size) {
            sample['Size'] = data.getUint32(x); x += 4;
        }

        if (has_sample_flags) {
            sample['Flags'] = '0x' + data.getUint32(x).toString(16); x += 4;
        }

        if (has_sample_composition_time_offset) {
            sample['Composition time offset'] = data.getInt32(x); x += 4;
        }

        boxContent.Samples.push(sample);
    }

    boxContent['Total duration'] = t_dur;

    return {'boxContent': boxContent,
            'childOffset' : offset};
}

function box_sdtp(data, offset, len) {
    var boxContent = {};
    var x = offset;
    boxContent['Box name'] = "Independent and Disposable Samples Box";
    var version = data.getUint8(x);
    boxContent['Box version'] = version;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    //boxContent['Box flags'] = '0x' + f.toString(16);
    var sample_count = len - (x-offset); // Should be taken from count in stsz or stz2
    //console.log("stdp sample_count = " + sample_count);

    boxContent.Entries = new Array();

    while (sample_count-- > 0) {
        var entry = {};
        var byte = data.getUint8(x); x += 1;
        entry['is_leading'] = (byte >> 6) & 3;
        entry['sample_depends_on'] = (byte >> 4) & 3;
        entry['sample_is_depended_on'] = (byte >> 6) & 3;
        entry['sample_has_redundancy'] = byte & 3;
        boxContent.Entries.push(entry);
    }

    return {'boxContent': boxContent,
            'childOffset' : offset};
}

function box_pssh(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);
    boxContent['System id'] = '0x' + binStringToHex2(data.getUTF8String(x, 16)); x += 16;

    if (v == 1)
    {
        var KID_count = data.getUint32(x); x += 4;
        boxContent['KID_count'] = KID_count;

        boxContent.KID = new Array();
        for (var k = 0; k < KID_count; ++k)
        {
            var kid = '0x' + binStringToHex2(data.getUTF8String(x, 16)); x += 16;
            boxContent.KID.push(kid);
        }
    }

    boxContent['Data size'] = data.getUint32(x); x += 4;

    return {'boxContent': boxContent,
            'childOffset': offset
    };
}

function box_tenc(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    x += 2; // Skip 2 bytes
    boxContent['Is encrypted'] = data.getUint8(x); x += 1;
    boxContent['Default IV size'] = data.getUint8(x); x += 1;
    boxContent['Key identifier'] = '0x' + binStringToHex2(data.getUTF8String(x, 16)); x += 16;

    return {
        'boxContent': boxContent,
        'childOffset': offset
    };
}

function box_saiz(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    if (f & 1) {
        x += 8
    }

    var defSampleSize = data.getUint8(x); x += 1;
    boxContent['Default sample size'] = defSampleSize;
    if (0 == defSampleSize) {
        var entries = data.getUint32(x); x += 4;
        boxContent['Sample sizes'] = new Array();
        while(entries--)
        {
            boxContent['Sample sizes'].push(data.getUint8(x)); x += 1;;
        }
    }

    return {'boxContent': boxContent,
            'childOffset': offset
    };
}

function box_saio(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    if (f & 1)
    {
        boxContent['aux_info_type'] = data.getUint32(x); x += 4;
        boxContent['aux_info_type_parameter'] = data.getUint32(x); x += 4;
    }

    var entries = data.getUint32(x); x += 4;
    boxContent.Offset = new Array();
    while (entries--) {
        var o = data.getUint32(x); x += 4;
        boxContent.Offset.push('0x' + o.toString(16));
    }

    return {'boxContent': boxContent,
            'childOffset': offset
    };
}

function box_sbgp(data, offset, len) {
    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    boxContent['Grouping type'] = data.getUint32(x); x += 4;
    if (v == 1) {
        boxContent['Grouping type parameter'] = data.getUint32(x); x += 4;
    }

    var entries = data.getUint32(x); x += 4;
    boxContent.Entries = new Array();
    while (entries--) {
        var sample = {};
        sample['Sample count'] = data.getUint32(x); x += 4;
        sample['Group description index'] = data.getUint32(x); x += 4;
        boxContent.Entries.push(sample);
    }

    return {'boxContent': boxContent,
            'childOffset': offset
    };
}

function box_sgpd(data, offset, len) {

    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    boxContent['Grouping type'] = data.getUTF8String(x, 4); x += 4;
    if (v == 1) {
        boxContent['Grouping type parameter'] = data.getUint32(x); x += 4;
    }

    var entries = data.getUint32(x); x += 4;
    boxContent.Entries = new Array();
    while (entries--) {
        var sample = {};
        x += 2; // skip 2 bytes
        sample['Is encrypted'] = data.getUint8(x); x += 1;
        sample['IV size'] = data.getUint8(x); x += 1;
        sample['Key identifier'] = '0x' + binStringToHex2(data.getUTF8String(x, 16)); x += 16;
        boxContent.Entries.push(sample);
    }

    return {'boxContent': boxContent,
            'childOffset': offset
    };
}

function box_schm(data, offset, len) {

    var boxContent = {};
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    boxContent['Scheme type'] = data.getUTF8String(x, 4); x += 4;
    boxContent['Scheme version'] = '0x' + data.getUint32(x).toString(16); x += 4;

    return {
        'boxContent': boxContent,
        'childOffset': offset
    };
}

function box_frma(data, offset, len) {

    var boxContent = {};
    var x = offset;

    boxContent['Format'] = data.getUTF8String(x, 4); x += 4;

    return {
        'boxContent': boxContent,
        'childOffset': offset
    };
}

var gTfrfGuid = "d4807ef2ca3946958e5426cb9e46a79f";
var gTfxdGuid = "6d1d9b0542d544e680e2141daff757b2";
var gSampleEncryptionGuid = "a2394f525a9b4f14a2446c427c648df4";
var gTrackEncryptionGuid = "8974dbce7be74c5184f97148f9882554";
var gPsshGuid = "d08a4f1810f34a82b6c832d8aba183d3";

function box_uuid(data, offset, len) {
    var boxContent = {};
    var x = offset;

    var uuid = binStringToHex2(data.getUTF8String(x, 16));
    x += 16;
    boxContent['uuid'] = uuid;

    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    var z = (v == 0) ? 4 : 8;

    // Parsing UUID parameters for some boxes
    if (uuid == gTfrfGuid)
    {
        boxContent['box_type'] = 'PIFF tfrf'
        boxContent.Entries = new Array();

        var numEntries = data.getUint8(x); x+= 1;
        for (var i = 0; i < numEntries; ++i)
        {
            var time = (v == 0) ? data.getUint32(x) : getUint64(data, x);
            x += (v == 0) ? 4 : 8;
            var duration = (v == 0) ? data.getUint32(x) : getUint64(data, x);
            x += (v == 0) ? 4 : 8;

            //var time = binStringToHex2(data.getUTF8String(x, z)); x += z;
            //var duration = binStringToHex2(data.getUTF8String(x, z)); x += z;

            var entry = {};
            entry['time'] = time.toString();
            entry['duration'] = duration.toString();
            boxContent.Entries.push(entry);
        }
    }
    else if (uuid == gTfxdGuid)
    {
        boxContent['box_type'] = 'PIFF tfxd'

        var time = (v == 0) ? data.getUint32(x) : getUint64(data, x);
        x += (v == 0) ? 4 : 8;
        var duration = (v == 0) ? data.getUint32(x) : getUint64(data, x);
        x += (v == 0) ? 4 : 8;

        //var time = binStringToHex2(data.getUTF8String(x, z)); x += z;
        //var duration = binStringToHex2(data.getUTF8String(x, z)); x += z;

        boxContent['time'] = time.toString();
        boxContent['duration'] = duration.toString();
    }
    else if (uuid == gSampleEncryptionGuid)
    {
        boxContent['box_type'] = 'PIFF SampleEncryption'
        var ivSize = 8;
        if (f & 0x01)
        {
            var alg = (data.getUint8(x) << 16) + (data.getUint8(x + 1) << 8) + (data.getUint8(x + 2) << 0);
            boxContent['algorithm'] = alg;
            ivSize = data.getUint8(x + 3);
            boxContent['IV-size'] = ivSize;
            boxContent['key-id'] = binStringToHex2(data.getUTF8String(x + 4, 16));
            x += 20;
        }
        var sampleCount = data.getUint32(x); x+= 4;
        boxContent.Entries = new Array();
        for (var i = 0; i < sampleCount; ++i)
        {
            var iv = binStringToHex2(data.getUTF8String(x, ivSize));
            x += ivSize;
            var entry = {};
            entry['iv'] = iv;
            if (f & 0x02)
            {
                entry.Entries = new Array();
                var stripeCount = data.getUint16(x); x+= 2;
                for (var j = 0; j < stripeCount; ++j)
                {
                    var clearData = data.getUint16(x); x+= 2;
                    var encData = data.getUint32(x); x+= 4;
                    var msg = 'clear_data=' + clearData.toString() + ', encrypted_data=' + encData.toString();
                    entry.Entries.push(msg);
                }
            }
            boxContent.Entries.push(entry);
        }
    }
    else if (uuid == gTrackEncryptionGuid)
    {
        boxContent['box_type'] = 'PIFF TrackEncryption'

        var alg = (data.getUint8(x) << 16) + (data.getUint8(x + 1) << 8) + (data.getUint8(x + 2) << 0);
        boxContent['algorithm'] = alg;
        ivSize = data.getUint8(x + 3);
        boxContent['IV-size'] = ivSize;
        boxContent['key-id'] = binStringToHex2(data.getUTF8String(x + 4, 16));
        x += 20;
    }
    else if (uuid == gPsshGuid)
    {
        boxContent['box_type'] = 'PIFF PSSH'

        boxContent['system_id'] = binStringToHex2(data.getUTF8String(x, 16));
        x += 16

        data_size = data.getUint32(x);
        boxContent['data_size'] = data_size;
        x += 4

        boxContent['data'] = binStringToHex2(data.getUTF8String(x, data_size));
        x += data_size
    }
    else
        boxContent['box_type'] = 'unknown'

    return {'boxContent': boxContent,
            'childOffset' : offset};
}

/**
   EditListBox
*/
function box_elst(data, offset, len) {
    var boxContent = {};
    boxContent['Box name'] = 'Edit List Box'
    var x = offset;
    var v = data.getUint8(x);
    boxContent['Box version'] = v;
    var f = (data.getUint8(x + 1) << 16) + (data.getUint8(x + 2) << 8) + (data.getUint8(x + 3) << 0);
    x += 4;
    boxContent['Box flags'] = '0x' + f.toString(16);

    var entry_count = data.getUint32(x); x += 4;

    boxContent.Entries = new Array();
    if (v == 1) {
        for (var j = 0; j < entry_count; ++j) {
            var entry = {};
            entry['segment duration'] = data.getUint64(x); x+=8;
            entry['media time'] = data.getInt64(x); x+=8;
            boxContent.Entries.push(entry);
        }
    } else { //version == 0
        var entry = {};
        entry['segment duration'] = data.getUint32(x); x+=4;
        entry['media time'] = data.getInt32(x); x+=4;
        boxContent.Entries.push(entry);
    }

    boxContent['Media rate integer'] = data.getInt16(x); x+=2;
    boxContent['Media rate fraction'] = data.getInt16(x); x+=2;

    return {
        'boxContent': boxContent,
        'childOffset': offset
    };
}

function box_mdat(data, offset, len) {

    var boxContent = {};
    var x = offset;

    return {
        'boxContent': boxContent,
        'childOffset': offset
    };
}

function executeFunctionByName(functionName, context /*, args */)
{
    var args = Array.prototype.slice.call(arguments).splice(2);
    var namespaces = functionName.split(".");
    var func = namespaces.pop();
    for(var i = 0; i < namespaces.length; i++)
    {
        context = context[namespaces[i]];
    }
    return context[func].apply(this, args);
}

function printBoxes(boxes, indent)
{
    for (var j = 0; j < boxes.length; ++j)
    {
        box = boxes[j];

        var text = "";
        for (var i = 0; i < indent; ++i)
        {
            text += " - ";
        }
        console.log(text + box["type"] + " (" + box["offset"].toString(16) + ", " + box["size"].toString(16) + ")");

        if (box.children.length > 0)
        {
            printBoxes(box.children, indent + 1);
        }
    }
}

function cString(token, len)
{
    var s = '';
    for (var idx = 0; idx < len; ++idx)
    {
        s += token;
    }
    return s;
}

function fixSize(size)
{
    var h = size.toString(16);
    var rest = 8 - h.length;
    return h + cString(' ', rest);
}

function setupHexData(box)
{
    var boxSize = box.size;
    var boxOffset = box.offset;

    msg = '';
    var numRows = Math.floor(boxSize / 32);
    var rest = boxSize % 32;
    if (rest > 0)
    {
        numRows++;
    }

    for (var i = 0; i < numRows; ++i)
    {
        var bytesToRead = 32;
        if (i + 1 == numRows)
        {
            if (rest > 0)
            {
               bytesToRead = rest;
            }
        }

        var size = (boxOffset + 32 * i);
        var line = fixSize(size) + '  ';

        if (bytesToRead > 16)
        {
            var data1 = boxData.getUTF8String(boxOffset + i * 32, 16);
            var data2 = boxData.getUTF8String(boxOffset + i * 32 + 16, bytesToRead - 16);

            var fill = '';
            if (32 - bytesToRead > 0)
            {
                fill = cString('  ', 32 - bytesToRead);
            }

            line += binStringToHex2(data1)  + '  ';
            line += binStringToHex2(data2)  + fill + '    ';

            line += binStringToHex3(data1);
            line += binStringToHex3(data2);

            //console.log('line1=' + line);
        }
        else
        {
            var data1 = boxData.getUTF8String(boxOffset + i * 32, bytesToRead);
            var fill1 = cString('  ', 16 - bytesToRead);
            var fill2 = cString('  ', 16);

            line += binStringToHex2(data1) + fill1 + '  ';
            line += fill2 + '    ';

            line += binStringToHex3(data1);

            //console.log('line2=' + line);
        }

        msg += '<p>' + line + '</p>';
    }

    $('#hexdata').html(msg);
}

function createKeyValueTable(table, contentObj, rowClass) {
    for (var attributeId in contentObj) {
        var row = document.createElement('tr');
        $(table).append(row);
        var cell = document.createElement('td');
        $(row).append(cell);
        $(cell).text(attributeId);
        var att = contentObj[attributeId];

        if (att instanceof Array) {
            var cell = document.createElement('td');
            if (rowClass.length > 0) $(row).addClass(rowClass + 'Attribute');
            $(row).append(cell);
            $(cell).text(': size = ' + att.length);
            for (var arrayIndex in att) {
                var attrib = att[arrayIndex];
                var row = document.createElement('tr');
                if( rowClass.length > 0 ) $(row).addClass(rowClass + 'Attribute');
                $(table).append(row);
                var cell = document.createElement('td');
                $(row).append(cell);
                $(cell).text(' - ' + /*attributeId +*/ '[' + arrayIndex + ']');
                var cell = document.createElement('td');
                $(row).append(cell);
                if (attrib instanceof Object) {
                    var subTable = document.createElement('table');
                    $(cell).append(subTable);
                    createKeyValueTable(subTable, attrib, '');
                }
                else {
                    $(cell).text(': ' + attrib);
                }
            }
        } else {
            if (rowClass.length > 0) $(row).addClass(rowClass + 'Value');
            var cell = document.createElement('td');
            $(row).append(cell);
            $(cell).text(': ' + att);
        }
    }
}

function setupBoxContent(box) {
    //console.log('setupBoxContent: ' + JSON.stringify(box));

    $('#boxcontent').empty();
    var table = document.createElement('table');
    var row = document.createElement('tr');
    $(table).append(row);
    var cell = document.createElement('td');
    $(row).append(cell);
    $(cell).text('Box type');
    var cell = document.createElement('td');
    $(row).append(cell);
    $(cell).text(': ' + box.type);

    $('#boxcontent').append(table);
    if (box.hasOwnProperty('boxContent')) {
        createKeyValueTable(table, box.boxContent, 'boxContent');
    }
    if (box.hasOwnProperty('children')) {
        if( box.children.length > 0 ) {
            var row = document.createElement('tr');
            $(table).append(row);
            var cell = document.createElement('td');
            $(row).append(cell);
            $(cell).text("Children");
            var cell = document.createElement('td');
            $(row).append(cell);
            $(cell).text(': ' + box.children.length);
        }
    }
}

function padToSize(val, padSize) {
    var padString = new Array(padSize + 1).join(' ') + val;
    var result = padString.substr(padString.length - padSize);
    return result;
}

function createBoxTable(boxes, indent, table, block)
{
    var space = "";
    for (var i = 0; i < indent; ++i)
    {
        space += " - ";
    }

    for (var j = 0; j < boxes.length; ++j)
    {
        var box = boxes[j];
        var boxInfo = padToSize(box["offset"].toString(16), 8) + ' ' + padToSize(box["size"].toString(16), 8) + ' ' + space + box["type"]; //  + " (" + box["offset"].toString(16) + ", " + box["size"].toString(16) + ")";

        div = document.createElement('div');

        if (block)
        {
            div.style.display='none';
        }

        $(table).append(div);
        $(div).append(document.createTextNode(boxInfo));

        //console.log(boxInfo + '(' + JSON.stringify(box) + ')');

        $(div).mouseenter( function(event) {
            if (!event.isPropagationStopped()) event.stopPropagation();
            this.style.backgroundColor = 'green';
        });
        $(div).mouseout( function(event) {
            if (!event.isPropagationStopped()) event.stopPropagation();
            this.style.backgroundColor = '';
        });

        if (box.children.length > 0)
        {
            $(div).addClass('containerBox');

            $(div).dblclick(function (event) {
                if (!event.isPropagationStopped()) event.stopPropagation();

                $(this).toggleClass('openContainer');

                var children = this.childNodes;

                for (var i = 1; i < children.length; ++i) {
                    $(children[i]).toggle();
                }
            });

            $(div).click( { currentBox: box }, function (event) {
                if (!event.isPropagationStopped()) event.stopPropagation();

                setupHexData(event.data.currentBox);
                setupBoxContent(event.data.currentBox);
            });

            createBoxTable(box.children, indent + 1, div, true);
        }
        else
        {
            $(div).addClass('leafBox');
            $(div).dblclick(function (event) {
                if (!event.isPropagationStopped()) event.stopPropagation();

                // nothing
            });

            $(div).click({ currentBox: box }, function(event) {
                if (!event.isPropagationStopped()) event.stopPropagation();

                setupHexData(event.data.currentBox);
                setupBoxContent(event.data.currentBox);
            });
        }
    }

    //if (false == block) {
    //    var width = Math.max.apply(Math, $(table).children().map(function () {
    //        return $(this).width();
    //    }).get());
    //    console.log('width = ' + width);
    //}
}

function rawStringToBuffer( str ) {
    var idx, len = str.length, arr = new Array( len );
    for ( idx = 0 ; idx < len ; ++idx ) {
        arr[ idx ] = str.charCodeAt(idx) & 0xFF;
    }
    // You may create an ArrayBuffer from a standard array (of values) as follows:
    return new Uint8Array( arr ).buffer;
}

function handleData(data)
{
    buffer = rawStringToBuffer(data);

    //console.log(data);
    //console.log('size=' + buffer.byteLength);

    var dataView = new DataView(buffer);
    var jsonData = [];
    var intent = 0;

    boxData = dataView;
    var result = parseBoxes(dataView, 0, buffer.byteLength, jsonData, 0);

    $('#messages').empty();
    $('#boxtree').empty();
    $('#boxcontent').empty();
    $('#hexdata').empty();

    var tableDiv = document.createElement('div');
    $('#boxtree').append(tableDiv);

    if (result == buffer.byteLength)
    {
        createBoxTable(jsonData, 0, tableDiv, false);
    }
    else
    {
        displayError('Failed parsing data, no MP4 boxes found.');
    }
}

function handleFile2(evt, files)
{
    var progress = document.querySelector('.percent');

    // Reset progress indicator on new file selection.
    progress.style.width = '0%';
    progress.textContent = '0%';

    reader = new FileReader();
    reader.onerror = errorHandler;
    reader.onprogress = updateProgress;
    reader.onabort = function(e)
    {
        alert('File read cancelled');
    };
    reader.onloadstart = function(e)
    {
        document.getElementById('progress_bar').className = 'loading';
    };
    reader.onload = function(e)
    {
        // Ensure that the progress bar displays 100% at the end.
        progress.style.width = '100%';
        progress.textContent = '100%';
        setTimeout("document.getElementById('progress_bar').className='';", 2000);

        buffer = e.target.result;

        var dataView = new DataView(buffer);
        var jsonData = [];
        var intent = 0;

        boxData = dataView;
        var result = parseBoxes(dataView, 0, buffer.byteLength, jsonData, 0);

        $('#messages').empty();
        $('#boxtree').empty();
        $('#hexdata').empty();
        $('#boxcontent').empty();

        var tableDiv = document.createElement('div');
        $('#boxtree').append(tableDiv);

        if (result == buffer.byteLength)
        {
            createBoxTable(jsonData, 0, tableDiv, false);
        }
        else
        {
            displayError('Failed parsing data, no MP4 boxes found.');
        }
    }

    // Read in the image file as a binary string.
    reader.readAsArrayBuffer(files[0]);
}
