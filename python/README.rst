Tools for creating, analyzing, modifying, downloading MPEG-DASH content
=======================================================================
DASH Industry Forum collection of various tools. A lot of them are small and
need to be run directly from the source tree.

Major tools
-----------

**dash-batch-encoder** (dash_tools.batch_encoder)
  * Uses *ffmpeg* to create multi-variant mp4 content with fixed
    GoP duration
  * Output is suitable for transforming into DASH ABR content
  * Configured via JSON recipes

**dash-ondemand-creator** (dash_tools.ondemand_creator)
  * Uses *MP4Box* to transform the output of dash-batch-encoder into
    DASH OnDemand content.
  * Postprocesses audio tracks to get segment alignment with video
  * Configured via JSON recipe

**dash-ondemand-verifier**  (dash_tools.ondemand_verifier)
    * Performs checks on (trees of) DASH OnDemand asset and reports issues

**dash-ondemand-add-subtitles** (dash_tools.ondemand_add_subs)
    * Add subtitle adaptation sets for side-loaded files to a DASH MPD

**dash-livedownloader**  (dash_tools.livedownloader)
    * Downloads a live DASH asset and stores on disk. Only supports
      $Number$-template

These above tools are exported as scripts starting with prefix dash-.
There corresponding names in the source code does not have that part.

**dash_tools.ts**
    * This is a competent MPEG-2 TS parser

For more details, see online documentation_.


.. _documentation: https://github.com/Dash-Industry-Forum/media-tools/tree/master/python/doc/dash_tools.rst