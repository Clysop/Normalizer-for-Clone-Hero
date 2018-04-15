import os
import ffmpy
import json
import subprocess

IMPORT_WIDTH = 16


class Audio():
    def __init__(self, filename):
        self.filename = filename
        self.data = None
        self.info = {}

    def probe(self, path):
        probe = ffmpy.FFprobe(global_options='-show_streams -of json',
                              inputs={os.path.join(path, self.filename): ''})

        out, err = probe.run(stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.info = json.loads(out)['streams'][0]

    def load(self, path):
        ff = ffmpy.FFmpeg(global_options='-y',
                          inputs={os.path.join(path, self.filename): ''},
                          outputs={'pipe:1': '-f s{}le'.format(IMPORT_WIDTH)})
        try:
            self.data, err = ff.run(stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        except ffmpy.FFRuntimeError:
            return False

        return True

    def export(self, path, gain):
        sr = self.info['sample_rate']
        br = self.info['bit_rate']

        ff = ffmpy.FFmpeg(global_options='-y',
                          inputs={'pipe:0': '-f s{}le \
                                  -ac 2 -ar {}'.format(IMPORT_WIDTH, sr)},
                          outputs={os.path.join(path, self.filename):
                                   '-ar {} -b:a {} -filter:a \
                                   "volume={}dB"'.format(sr, br, gain)})

        try:
            out, err = ff.run(input_data=self.data,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        except ffmpy.FFRuntimeError:
            return False

        return True
