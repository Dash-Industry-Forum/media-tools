 
## How to make DASH OnDemand content following DASH-IF IOP spec.
 
Goal:
 
* Create content in DASH OnDemand profile using SegmentBase. This uses sidx to describe all the segments in the tracks. Follows DASH-IF IOP.
* Audio segments that don't drift with respect to video. E.g. output from MP4Box may need to be adjusted
 
Two tools are needed:

1. `batch_encoder.py` to encode the content into the various video and audio tracks needed.
2. `create_ondemand_dash.py` to generate MPD and CMAF tracks.

To get PYTHON paths to work properly, run the scripts from the directory `batch_ffmpeg`.
 
Normal chain:

Generating MP4 track files.

* Start with mp4 file for content.
* Write JSON config file with correct video settings and audio settings for `batch_encoder.py`
* Run `batch_encoder.py` which will generate one file per video and audio track (e.g. V1200.mp4, V2400.mp4, A96_eng.mp4)
* All the different tracks are in the same directory, which is what the next step takes as input
 
Generate DASH OnDemand content from MP4 track files

* Here we use the tool `create_ondemand_dash.py`
* It takes the parameters: cfg_file.json, directory where the MP4 tracks are
* the cfg_file.json lists the video and audio tracks and tells the duration in milliseconds of the segments
* the tool runs MP4Box to generate DASH media tracks and manifest. It then runs a tool to fix the audio segment durations inplace


### Limitations

* Subtitles are currently not handled. They need to be added by hand by modifying the output MPD. This will be fixed in a later version.

