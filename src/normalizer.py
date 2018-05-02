"""Implements Normalizer class, which is the main program.

Written be Clysop.
"""

import os
import sys
import json
import time
import shutil
import logging
import datetime
import configparser
import multiprocessing

from song import Song

# Allows passing exceptions between processes.
import tblib.pickling_support
tblib.pickling_support.install()

# Name of folder that contains songs.
INPUT_FOLDER = 'Songs'
# Name of folder to output to. Will be created if it doesn't exist.
OUTPUT_FOLDER = 'Normalized'

# Default settings.
TARGET_GAIN = -16       # Target volume in dBFS.
HEADROOM = 1            # If song within this dB, copy instead of process.
DEBUG_LOAD = False      # Print FFmpeg info when loading.
DEBUG_EXPORT = False    # Print FFmpeg ingo when exporting.
MULTITHREADING = True   # Process a song on each logical core the CPU has.

CACHE_FILENAME = 'normalizer_cache.json'
CONFIG_FILENAME = 'normalizer_config.ini'


class ExceptionWrapper(object):
    """Wrapper for exception to pass between processes."""

    def __init__(self, ee):
        self.ee = ee
        _,  _, self.tb = sys.exc_info()

    def re_raise(self):
        """Raises stored exception."""
        raise self.ee.with_traceback(self.tb)


class Normalizer():
    """Class for running a Normalizer instance.

    Can be started be running the 'run' method.
    """

    def __init__(self):
        self.songs = []
        self.cache = None

        self.num_songs = 0
        self.num_export = 0
        self.num_copied = 0
        self.num_cached = 0
        self.num_errors = 0

    def _load_config(self, filename):
        """Loads a config file. Creates one if none are found."""
        global TARGET_GAIN, HEADROOM, DEBUG_LOAD, DEBUG_EXPORT, MULTITHREADING

        default_config = configparser.ConfigParser()
        default_config['DEFAULT'] = {
            'target volume': TARGET_GAIN,
            'headroom': HEADROOM,
            'load debug': DEBUG_LOAD,
            'export debug': DEBUG_EXPORT,
            'multithreading': MULTITHREADING,
        }

        if os.path.isfile(filename):
            # Try to read existing config file.
            try:
                config = configparser.ConfigParser()
                config.read(filename)

                assert 'DEFAULT' in config
                for key in default_config['DEFAULT']:
                    assert key in config['DEFAULT']

                assert int(config['DEFAULT']['target volume']) < 0
                assert int(config['DEFAULT']['headroom']) >= 0
            except Exception:
                # Remake if bad config file.
                print("Bad config, remaking.\n")
                config = default_config
                with open(filename, 'w') as cf:
                    config.write(cf)

            TARGET_GAIN = int(config['DEFAULT']['target volume'])
            HEADROOM = int(config['DEFAULT']['headroom'])
            DEBUG_LOAD = config['DEFAULT']['load debug'] == 'True'
            DEBUG_EXPORT = config['DEFAULT']['export debug'] == 'True'
            MULTITHREADING = config['DEFAULT']['multithreading'] == 'True'
        else:
            # Create new config file if none is found.
            with open(filename, 'w') as cf:
                default_config.write(cf)

    def _load_cache(self, filename):
        """Loads a cache file. Creates one if none are found."""
        if os.path.isfile(filename):
            with open(filename) as cache_file:
                return json.load(cache_file)
        else:
            cache = {}
            with open(filename, 'w') as cache_file:
                json.dump(cache, cache_file, indent=2)

            return cache

    def _write_cache(self, filename, path, data):
        """Writes new info to cache and cachefile."""
        self.cache[path] = data
        with open(filename, 'w') as cache_file:
            json.dump(self.cache, cache_file, indent=2)

    def _find_songs(self, folder):
        """Finds all folders that contain a notes file, i.e. all songs."""
        songs = []

        for root, dirs, files in os.walk(folder):
            chart_exists = os.path.isfile(os.path.join(root, 'notes.chart'))
            mid_exists = os.path.isfile(os.path.join(root, 'notes.mid'))
            if chart_exists or mid_exists:
                songs.append(Song(root))

        # Sort songs by filename, not needed on Windows.
        # songs.sort(key=lambda s: s.path)
        return songs

    def _process_song(self, song):
        """processes the Song object passed as argument.

        Loads audio, analyzes volume, then exports audiofiles with gain
        so that the song has the correct volume.
        Copies song if within HEADROOM of TARGET_GAIN.
        """
        song.scan_files()

        # Check if song is in cache and is not changed.
        if song.path in self.cache and song.check_cache(self.cache[song.path]):
            print("  Song in cache, skipping.")
            return 2

        # Load audiofiles, error if no audio was loaded.
        if not song.load_files(indent=2, debug=DEBUG_LOAD):
            print("\n  Couldn't load any audio, skipping.")
            return -1

        # Create new song folder if it doesn't exist.
        new_path = os.path.join(OUTPUT_FOLDER, song.path.partition('\\')[2])
        if not os.path.isdir(new_path):
            os.makedirs(new_path)

        volume = song.get_volume()
        print('\n  Volume: {:.1f} dBFS.'.format(volume))

        # Export if gain difference is bigger than HEADROOM.
        exported = True
        gain_diff = TARGET_GAIN - volume
        if abs(gain_diff) > HEADROOM:
            print("  Applying {:.1f} dB of gain.\n".format(gain_diff))
            # Export audiofiles, error if no was exported.
            if not song.export(new_path, gain_diff,
                               indent=2, debug=DEBUG_EXPORT):
                print("\n  Couldn't export any audio, skipping.")
                shutil.rmtree(new_path)
                return -2
        else:
            # Copy if within HEADROOM dB.
            print("  Song within {} dB of target, copying files.".format(
                HEADROOM))
            song.copy(new_path)
            exported = False

        # Copy remaining files.
        song.copy(new_path, audio=False)

        # Remove loaded audiofiles to clean up memory.
        song.files = []
        if exported:
            return 0
        else:
            return 1

    def _process_song_mp(self, song):
        """Wrapper method for processing song whit multiprocessing.

        Disables output from processing method. Passes result to main
        process with a queue.
        Passes ExceptionWrapper if exception is encountered.
        """
        try:
            print("Processing", song.path)

            # Disable console output.
            original_stdout, original_stderr = sys.stdout, sys.stderr
            new_stdout = open(os.devnull, 'w')
            sys.stdout = sys.stderr = new_stdout

            result = self._process_song(song)
            queue.put((result, song.path, song.cache_data))

            # Enable console output.
            sys.stdout, sys.stderr = original_stdout, original_stderr
            new_stdout.close()
        except Exception as e:
            queue.put(ExceptionWrapper(e))

    def _init_mp(self, q):
        """Initializes the queue for child processes."""
        global queue
        queue = q

    def _update_num(self, result):
        """Updates num attributes based on result passed as argument."""
        num = {
            0: 'num_export',
            1: 'num_copied',
            2: 'num_cached',
            -1: 'num_errors',
            -2: 'num_errors',
        }

        setattr(self, num[result], getattr(self, num[result]) + 1)

    def _run(self, start_time):
        """processes all songs found with find_songs method.

        For use when multithreading is disabled.
        """
        for i, s in enumerate(self.songs):
            time_used = int(time.time() - start_time)
            print("Song {}/{}".format(i + 1, self.num_songs))
            print("Time:", datetime.timedelta(seconds=time_used))
            print(s.path)

            result = self._process_song(s)

            self._update_num(result)
            if result != 2:
                self._write_cache(CACHE_FILENAME, s.path, s.cache_data)

            print()

    def _run_mp(self):
        """Same as _run, but uses multithreading."""
        # Skip all songs that are found in cache until uncached song is found.
        start = 0
        for i, s in enumerate(self.songs):
            if s.path in self.cache and s.check_cache(self.cache[s.path]):
                print("In cache:", s.path)
                self.num_cached += 1
            else:
                start = i
                break

        queue = multiprocessing.Queue()
        with multiprocessing.Pool(initializer=self._init_mp,
                                  initargs=(queue,)) as pool:
            pool.map_async(self._process_song_mp, self.songs[start:], 1)

            num_processed = self.num_cached
            while num_processed < self.num_songs:
                data = queue.get()

                if isinstance(data, ExceptionWrapper):
                    data.re_raise()

                r, path, cache_data = data
                self._update_num(r)

                if r == -1:
                    print("\n{}\n  "
                          "Error, couldn't load audio\n".format(path))
                elif r == -2:
                    print("\n{}\n  "
                          "Error, couldn't export audio\n".format(path))

                # Don't update cache when song was skipped because of cache.
                if r != 2:
                    self._write_cache(CACHE_FILENAME, path, cache_data)

                num_processed = self.num_cached + self.num_copied \
                    + self.num_errors + self.num_export

    def run(self):
        """Runs Normalizer program."""
        try:
            start_time = time.time()

            self._load_config(CONFIG_FILENAME)
            self.cache = self._load_cache(CACHE_FILENAME)

            if MULTITHREADING:
                print("Multithreading enabled.")
                print("Running {} processes.\n".format(os.cpu_count()))

            print("Finding songs...")
            self.songs = self._find_songs(INPUT_FOLDER)
            self.num_songs = len(self.songs)
            print("Found {} songs.\n".format(self.num_songs))

            if MULTITHREADING:
                self._run_mp()
            else:
                self._run(start_time)

        except KeyboardInterrupt:
            # Sleep incase debug is on, which can couse strange output
            # when printing immediately.
            time.sleep(0.1)
            print("\nInterrupted.\n")
        except Exception:
            time.sleep(0.1)
            print("\n!!! CRASH !!!\nSee crash_log.txt for info.\n")
            logging.basicConfig(filename='crash_log.txt', filemode='w')
            logging.exception(
                "\n\nSomething bad happened.\n"
                "Send this to Clysop. (Discord: Clysop#3650)\n\n"
                )
        else:
            print("Done!\n")

        time_used = datetime.timedelta(seconds=int(time.time() - start_time))
        print("  Exported: {:>5}".format(self.num_export))
        print("  Copied:   {:>5}".format(self.num_copied))
        print("  Cached:   {:>5}".format(self.num_cached))
        print("  Errors:   {:>5}".format(self.num_errors))
        print("\nTime used:", str(time_used))

        input("\nPress enter to exit\n")


if __name__ == '__main__':
    multiprocessing.freeze_support()
    Normalizer().run()
