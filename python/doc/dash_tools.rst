dash_tools
-----------
DASH Industry Forum collection of various tools. A lot of them are small and
need to be run directly from the source tree.

Use cases
=========

A lot of analysis can be done, but there are two major use-cases which are
more described:

1. create DASH ondemand content (howto_create_)
2. verify DASH ondemand content (howto_verify_)

Major Tools
===========

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

**dash-livedownloader**  (dash_tools.livedownloader)
    * Downloads a live DASH asset and stores on disk. Only supports
      $Number$-template

These above tools are exported as scripts starting with prefix dash-.
There corresponding names in the source code does not have that part.

**dash_tools.ts**
    * This is a competent MPEG-2 TS parser

Minor tools
===========
A lot of the files in *dash_tools* are runnable scripts for modifying MP4
files or segments. Look at the source code for more information.

.. _howto_create: howto_create_dash_ondemand.rst
.. _howto_verify: howto_verify_dash_ondemand.rst