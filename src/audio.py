"""Implements the Audio class.

Written by Clysop.
"""

import os
import sys
import json
import subprocess

import ffmpy

# Bit width raw audio should be stored as when loaded.
IMPORT_WIDTH = 16

path = sys.path[0].rpartition('\\')[0]
FFMPEG_PATH = os.path.join(path, 'FFmpeg/ffmpeg.exe')
FFPROBE_PATH = os.path.join(path, 'FFmpeg/ffprobe.exe')


class Audio():
    """Class for loading and exporting audio using FFmpeg.

    Attributes:
        filename (str): name of audiofile, used when filepath is needed.
        data (bytes):   raw audio once loaded, stored as little endian.
        info (dict):    dict of stream info of probed audiofile.
    """

    def __init__(self, filename):
        assert type(filename) is str, "{} is not a string".format(filename)

        self.filename = filename
        self.data = None
        self.info = {}

    def probe(self, path):
        """Reads stream info from self.filename in 'path' using FFprobe.

        Args:
            path (str): directory that self.filename should be searched for

        Returns:
            True if successful, False otherwise.
        """
        probe = ffmpy.FFprobe(executable=FFPROBE_PATH,
                              global_options='-show_streams -of json',
                              inputs={os.path.join(path, self.filename): ''})

        try:
            out, err = probe.run(stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        except ffmpy.FFRuntimeError:
            return False

        self.info = json.loads(out)['streams'][0]
        return True

    def load(self, path, debug=False):
        """Loads audio from self.filename in 'path' using FFmpeg.

        Loads raw audio into self.data. Uses info in self.info,
        so probe should be run before this.

        Args:
            path (str):     directory self.filename should be searched for.
            debug (bool):   whether FFmpeg should output info when loading.

        Return:
            True if successful, False otherwise.
        """
        if debug:
            output = None
        else:
            output = subprocess.PIPE

        ff = ffmpy.FFmpeg(executable=FFMPEG_PATH,
                          global_options='-y -loglevel error -stats',
                          inputs={os.path.join(path, self.filename): ''},
                          outputs={'pipe:1': '-f s{}le'.format(IMPORT_WIDTH)})
        try:
            self.data, err = ff.run(stdout=subprocess.PIPE, stderr=output)
        except ffmpy.FFRuntimeError:
            return False

        return True

    def export(self, path, gain=0, debug=False):
        """Exports audio to self.filename in 'path' using FFmpeg.

        Exports audio stored in self.data, so audio should be loaded
        before exporting.

        Args:
            path (str):     directory self.filename should be placed in.
            gain (float):   gain to be applied when exporting, in decibel.
            debug (bool):   whether FFmpeg should output info when exporting.

        Returns:
            True if successful, False otherwise.
        """
        if debug:
            output = None
        else:
            output = subprocess.PIPE

        sr = self.info.get('sample_rate', '44.1k')
        br = self.info.get('bit_rate', '192k')

        ff = ffmpy.FFmpeg(executable=FFMPEG_PATH,
                          global_options='-y -loglevel error -stats',
                          inputs={'pipe:0': '-f s{}le '
                                  '-ac 2 -ar {}'.format(IMPORT_WIDTH, sr)},
                          outputs={os.path.join(path, self.filename):
                                   '-ar {} -b:a {} -filter:a '
                                   '"volume={}dB"'.format(sr, br, gain)})

        try:
            out, err = ff.run(input_data=self.data,
                              stdout=subprocess.PIPE,
                              stderr=output)
        except ffmpy.FFRuntimeError:
            return False

        return True
