import os
import math
import time
import shutil
import audioop

from audio import Audio, IMPORT_WIDTH

USED_AUDIO = ['crowd', 'song', 'guitar', 'drums', 'drums_1', 'drums_2',
              'drums_3', 'drums_4', 'rhythm', 'vocals', 'keys']

used_audio = []
for f in USED_AUDIO:
    used_audio.append(f + '.ogg')
    used_audio.append(f + '.mp3')
USED_AUDIO = used_audio


def list_files(path, used=True):
    for filename in os.listdir(path):
        file_exists = os.path.isfile(os.path.join(path, filename))
        if file_exists and (filename in USED_AUDIO) == used:
            yield filename


class Song():
    def __init__(self, path):
        assert type(path) is str, "{} is not a string".format(path)
        assert os.path.isdir(path), "{} is not a directory".format(path)

        assert os.path.isfile('{}/notes.mid'.format(path)) or \
            os.path.isfile('{}/notes.chart'.format(path)), \
            "Chart file not found in {}".format(path)

        self.path = path
        self.files = []
        self.cache_data = {}

    def check_cache(self, data):
        for filename in self.cache_data:
            if filename not in data or \
               self.cache_data[filename] > data[filename]:
                return False

        return True

    def scan_files(self):
        for filename in list_files(self.path):
            a = Audio(filename)
            self.files.append(a)

            self.cache_data[filename] = int(os.path.getmtime(
                os.path.join(self.path, filename)))

    def load_files(self, indent=0, debug=False):
        for a in self.files.copy():
            print(' ' * indent + "Loading {}...".format(a.filename))
            a.probe(self.path)
            if not a.load(self.path, debug=debug):
                print(' ' * indent * 2 + 'Error, skipping')
                self.files.remove(a)

        if len(self.files) > 0:
            return True
        else:
            return False

    def _combine_audio(self):
        longest = 0
        for file in self.files:
            if len(file.data) > longest:
                longest = len(file.data)

        if len(self.files) > 1:
            combined = bytes(longest)
            for file in self.files:
                new_data = file.data + bytes(longest - len(file.data))
                combined = audioop.add(combined, new_data,
                                       int(IMPORT_WIDTH/8))

            return combined
        else:
            return self.files[0].data

    def get_volume(self):
        data = self._combine_audio()
        return 20 * math.log(audioop.rms(data, int(
             IMPORT_WIDTH/8))/2**(IMPORT_WIDTH-1), 10)

    def copy(self, path, audio=True):
        cache_data = {}

        for filename in list_files(self.path, audio):
            if not os.path.isfile(os.path.join(path, filename)):
                shutil.copy2(os.path.join(self.path, filename), path)

            cache_data[filename] = int(time.time())

        if audio:
            self.cache_data = cache_data

    def export(self, path, gain, indent=0, debug=False):
        cache_data = {}

        for a in self.files.copy():
            print(' ' * indent + "Exporting {}...".format(a.filename))
            if not a.export(path, gain, debug=debug):
                print(' ' * indent * 2 + "Error, skipping")
                self.files.remove(a)

            cache_data[a.filename] = int(time.time())

        self.cache_data = cache_data

        if len(self.files) > 0:
            return True
        else:
            return False

    def export_combined(self):
        print("Exporting combined.")
        data = self._combine_audio()

        a = Audio('combined.ogg')
        a.info = self.files[0].info
        a.data = data
        a.export(self.path, -10)
