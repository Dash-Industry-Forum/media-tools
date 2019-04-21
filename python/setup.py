"""dash_mediatools setup with console-script starting with dash-.
"""

from setuptools import setup, find_packages
from codecs import open
from os import path

import dash_tools

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

console_scripts = [
    'dash-ondemand-verifier=dash_tools.ondemand_verifier:main',
    'dash-ondemand-creator=dash_tools.ondemand_creator:main',
    'dash-ondemand-add-subtitles=dash_tools.ondemand_add_subs:main',
    'dash-track-resegmenter=dash_tools.track_resegmenter:main',
    'dash-batch-encoder=dash_tools.batch_encoder:main',
    'dash-livedownloader=dash_tools.livedownloader:main'
]


setup(
    name='dash_mediatools',

    version=dash_tools.__version__,

    description='Tools for MPEG-DASH media creation and analysis',
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/Dash-Industry-Forum/media-tools/tree/master/python',

    # Author details
    author='Torbjorn Einarsson',
    author_email='torbjorn.einarsson@edgeware.tv',

    # Choose your license
    license='BSD',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Multimedia :: Video :: Conversion',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: BSD License',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],

    python_requires='== 2.7.*',

    # What does your project relate to?
    keywords='MPEG-DASH mp4 ttml mpeg2-ts',

    package_dir={'dash_tools': 'dash_tools'},
    packages=['dash_tools'],
    entry_points={
        'console_scripts': console_scripts
    }
)
