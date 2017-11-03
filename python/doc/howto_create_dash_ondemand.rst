How to create DASH OnDemand content following DASH-IF IOP spec.
===============================================================
 
Goal:
 
* Create content in DASH OnDemand profile using SegmentBase. This uses sidx
  to describe all the segments in the tracks. Follows DASH-IF IOP.
* Audio segments that don't drift with respect to video.
  E.g. output from MP4Box may need to be adjusted
 
Two tools in dash_tools are needed to achieve this:

1. *dash-batch-encoder* encodes the content into the various video and
    audio tracks needed
2. *dash-create-ondemand* to generate MPD and tracks and finally
resegment.

For this to work, *ffmpeg* and *MP4Box* must be in the path. ffmpeg should
be compiled with relevant codecs support (--enable-libx264,
--enable-libx265, --enable-libfdk-aac).

 
Normal chain:
-------------

Generating MP4 track files.

* Start with mp4 file for content.
* Write JSON config file with correct video settings and audio settings for
  *dash-batch-encoder*. There are online example configurations_.
* Run *dash-batch-encocer* which will generate one file per video and
  audio track (e.g. V1200.mp4, V2400.mp4, A96_eng.mp4)
* All the different tracks are in the same directory, which is what the next
  step takes as input
 
Generate DASH OnDemand content from MP4 track files

* Here we use the tool *dash-create-ondemand*
* It takes the parameters: cfg_file.json, directory where the MP4 tracks are
* the cfg_file.json lists the video and audio tracks and tells the duration
  in milliseconds of the segments
* the tool runs MP4Box to generate DASH media tracks and manifest.
  It then runs a *dash_tools.track_resegmenter' to fix the audio segment
  durations inplace and update the manifest


Limitations
-------------
* Subtitles are currently not handled. They need to be added by hand by
  modifying the output MPD. This will be fixed in a later version.

.. _configurations: ../example_configs

