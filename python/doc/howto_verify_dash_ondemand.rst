DASH OnDemand Verifier.

Verifies that assets defined by a DASH manifest are good on-demand assets.

Checks that

* the manifest uses indexRange and baseURL to specify content.
* sidx durations agree with the actual subsegments
* different representations in the same adaptation set are aligned.
* baseMediaDecodeTime starts at 0
* segment durations are similar in different adaptation sets (warning if not)

Further restrictions are (should be put in a profile):
* Text is either TTML or WebVTT as sideloaded files
* One adaptation set for all video

Return an exit value that is a bitmask combination of

BAD_SIDX = 0x01
BAD_ALIGNMENT = 0x02
BAD_MANIFEST = 0x04
BAD_NONZERO_FIRST_TIME = 0x08
BAD_NON_CONSISTENT_TFDT_TIMELIINE = 0x10
BAD_OTHER = 0x80

A result of 0, means nothing bad found.