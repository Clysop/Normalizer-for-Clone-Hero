"""Implements the Song class.

Written by Clysop.
"""

import os
import math
import time
import shutil
import audioop

from audio import Audio, IMPORT_WIDTH

# List of filenames used as audio by Clone Hero.
USED_AUDIO = ['crowd', 'song', 'guitar', 'drums', 'drums_1', 'drums_2',
              'drums_3', 'drums_4', 'rhythm', 'vocals', 'keys']

# Add .ogg and .mp3 extensions to the USED_AUDIO list.
used_audio = []
for f in USED_AUDIO:
    used_audio.append(f + '.ogg')
    used_audio.append(f + '.mp3')
USED_AUDIO = used_audio


def list_files(path, used=True):
    """List files in path the are in USED_AUDIO

    Args:
        path (str):     path to search in.
        used (bool):    True to list files in USED_AUDIO,
                        False to list other files.

    Yields:
        str: filename
    """
    for filename in os.listdir(path):
        file_exists = os.path.isfile(os.path.join(path, filename))
        if file_exists and (filename in USED_AUDIO) == used:
            yield filename


class Song():
    """Class for handling a song folder. Loads, handles, and exports audio.

    Attributes:
        path (str):         song folders path.
        files (list):       list of Audio objects that contain loaded audio.
        cache_data (dict):  stores timestamps for loaded audiofiles.
                            Gets rewritten when copying or exporting audio.
    """

    def __init__(self, path):
        assert type(path) is str, "{} is not a string".format(path)
        assert os.path.isdir(path), "{} is not a directory".format(path)

        assert os.path.isfile('{}/notes.mid'.format(path)) \
            or os.path.isfile('{}/notes.chart'.format(path)), \
            "Chart file not found in {}".format(path)

        self.path = path
        self.files = []
        self.cache_data = {}

    def check_cache(self, data):
        """Checks if given cache data is newer than self's data.

        Args:
            data (dict): timestamp data for files in self.path

        Returns:
            bool: True if data is newer than self.cache_data, False otherwise.
        """
        for filename in self.cache_data:
            if filename not in data or \
                    self.cache_data[filename] > data[filename]:
                return False

        return True

    def scan_files(self):
        """Finds all audiofiles in USED_AUDIO in self.path.

        Fills self.files with Audio objects representing each audiofile in
        self.path.
        Also fills self.cache_data with time of creation for each file.
        """
        for filename in list_files(self.path):
            a = Audio(filename)
            self.files.append(a)

            self.cache_data[filename] = int(os.path.getmtime(
                os.path.join(self.path, filename)))

    def load_files(self, indent=0, debug=False):
        """Loads audio in Audio objects in self.files.

        Args:
            indent (int):   indentation used when printing info
            debug (bool):   whether FFmpeg should output info when loading.

        Returns:
            bool: True if any audio was loaded, False otherwise.
        """
        for a in self.files.copy():
            print(' ' * indent + "Loading {}...".format(a.filename))
            probe = a.probe(self.path)
            if not (probe and a.load(self.path, debug=debug)):
                print(' ' * indent * 2 + 'Error, skipping')
                self.files.remove(a)

        # Check if any audio got loaded successfully.
        if len(self.files) > 0:
            return True
        else:
            return False

    def _combine_audio(self):
        """Combines all audio in self.files into one song of raw audio."""
        if len(self.files) == 0:
            return None
        elif len(self.files) == 1:
            return self.files[0].data

        # Find length of longest audiofile.
        longest = 0
        for file in self.files:
            length = len(file.data)
            if file.info.get('channels', 2) == 1:
                # Mono segments will be doubled when converted to stereo.
                length *= 2

            if length > longest:
                longest = length

        combined = bytes(longest)
        for file in self.files:
            data = file.data

            # Convert to stereo if mono.
            if file.info.get('channels', 2) == 1:
                data = audioop.tostereo(data, int(IMPORT_WIDTH/8), 1, 1)

            data += bytes(longest - len(data))
            combined = audioop.add(combined, data, int(IMPORT_WIDTH/8))

        return combined

    def get_volume(self):
        """Returns volume of song in dBFS.

        Returns:
            float: volume in dBFS.
        """
        data = self._combine_audio()
        rms = audioop.rms(data, int(IMPORT_WIDTH / 8))

        if rms == 0:
            return -math.inf
        else:
            rms_float = rms / (2 ** (IMPORT_WIDTH - 1) - 1)
            return 20 * math.log(rms_float, 10)

    def copy(self, path, audio=True):
        """Copies files from self.path to 'path'.

        If 'audio' is True, only copies files in USED_AUDIO, otherwise
        only copies audio not in USED_AUDIO. If copying audio, fills
        self.cache_data with time of copying.

        Args:
            path (str):     path files should be copied to.
            audio (bool):   whether to copy files in USED_AUDIO or not.
        """
        cache_data = {}

        for filename in list_files(self.path, audio):
            if not os.path.isfile(os.path.join(path, filename)):
                shutil.copy2(os.path.join(self.path, filename), path)

            cache_data[filename] = int(time.time())

        if audio:
            self.cache_data = cache_data

    def export(self, path, gain, indent=0, debug=False):
        """Exports audio to 'path'.

        Exports audio in self.files. Fills self.cache_data with
        time of exporting.

        Args:
            path (str):     path files should be exported to.
            gain (float):   amount of gain in dB to be applied when exporting.
            indent (int):   indentation used when printing info.
            debug (bool):   whether FFmpeg should output info when exporting.

        Returns:
            bool: True if successful, False otherwise.
        """
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

    def export_combined(self, path):
        """Exports an audiofile that is all the imported audio combined.

        Args:
            path (str): path where file should be exported to.
        """
        print("Exporting combined.")
        data = self._combine_audio()

        a = Audio('combined.ogg')
        a.info = self.files[0].info
        a.data = data
        a.export(path)
