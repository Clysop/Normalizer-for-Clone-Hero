import os
import sys
import json
import subprocess

import ffmpy

IMPORT_WIDTH = 16

path = sys.path[0].rpartition('\\')[0]
FFMPEG_PATH = os.path.join(path, 'FFmpeg/ffmpeg.exe')
FFPROBE_PATH = os.path.join(path, 'FFmpeg/ffprobe.exe')


class Audio():
    def __init__(self, filename):
        assert type(filename) is str, "{} is not a string".format(filename)

        self.filename = filename
        self.data = None
        self.info = {}

    def probe(self, path):
        probe = ffmpy.FFprobe(executable=FFPROBE_PATH,
                              global_options='-show_streams -of json',
                              inputs={os.path.join(path, self.filename): ''})

        out, err = probe.run(stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.info = json.loads(out)['streams'][0]

    def load(self, path, debug=False):
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
        if debug:
            output = None
        else:
            output = subprocess.PIPE

        sr = self.info['sample_rate']
        br = self.info['bit_rate']

        ff = ffmpy.FFmpeg(executable=FFMPEG_PATH,
                          global_options='-y -loglevel error -stats',
                          inputs={'pipe:0': '-f s{}le \
                                  -ac 2 -ar {}'.format(IMPORT_WIDTH, sr)},
                          outputs={os.path.join(path, self.filename):
                                   '-ar {} -b:a {} -filter:a \
                                   "volume={}dB"'.format(sr, br, gain)})

        try:
            out, err = ff.run(input_data=self.data,
                              stdout=subprocess.PIPE,
                              stderr=output)
        except ffmpy.FFRuntimeError:
            return False

        return True
