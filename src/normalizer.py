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

import tblib.pickling_support
tblib.pickling_support.install()

INPUT_FOLDER = 'Songs'
OUTPUT_FOLDER = 'Normalized'

TARGET_GAIN = -16
HEADROOM = 1
DEBUG_LOAD = False
DEBUG_EXPORT = False
MULTITHREADING = True

CACHE_FILENAME = 'normalizer_cache.json'
CONFIG_FILENAME = 'normalizer_config.ini'


class ExceptionWrapper(object):
    def __init__(self, ee):
        self.ee = ee
        __,  __, self.tb = sys.exc_info()

    def re_raise(self):
        raise self.ee.with_traceback(self.tb)


class Normalizer():
    def __init__(self):
        self.songs = []
        self.cache = None

        self.num_songs = 0
        self.num_export = 0
        self.num_copied = 0
        self.num_cached = 0
        self.num_errors = 0

    def _load_config(self, filename):
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
            try:
                config = configparser.ConfigParser()
                config.read(filename)

                assert 'DEFAULT' in config
                for key in default_config['DEFAULT']:
                    assert key in config['DEFAULT']

                assert int(config['DEFAULT']['target volume']) < 0
                assert int(config['DEFAULT']['headroom']) >= 0
            except Exception:
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
            with open(filename, 'w') as cf:
                default_config.write(cf)

    def _load_cache(self, filename):
        if os.path.isfile(filename):
            with open(filename) as cache_file:
                return json.load(cache_file)
        else:
            cache = {}
            with open(filename, 'w') as cache_file:
                json.dump(cache, cache_file, indent=2)

            return cache

    def _write_cache(self, filename, path, data):
        self.cache[path] = data
        with open(filename, 'w') as cache_file:
            json.dump(self.cache, cache_file, indent=2)

    def _find_songs(self, folder):
        songs = []

        for root, dirs, files in os.walk(folder):
            chart_exists = os.path.isfile(os.path.join(root, 'notes.chart'))
            mid_exists = os.path.isfile(os.path.join(root, 'notes.mid'))
            if chart_exists or mid_exists:
                songs.append(Song(root))

        songs.sort(key=lambda s: s.path)
        return songs

    def _process_song(self, song):
        song.scan_files()

        if song.path in self.cache and song.check_cache(self.cache[song.path]):
            print("  Song in cache, skipping.")
            return 2

        if not song.load_files(indent=2, debug=DEBUG_LOAD):
            print("  Couldn't load any audio, skipping.")
            return -1

        volume = song.get_volume()
        print('\n  Volume: {:.1f} dBFS.'.format(volume))

        new_path = os.path.join(OUTPUT_FOLDER, song.path.partition('/')[2])
        if not os.path.isdir(new_path):
            os.makedirs(new_path)

        exported = True

        gain_diff = TARGET_GAIN - volume
        if abs(gain_diff) > HEADROOM:
            print("  Applying {:.1f} dB of gain.\n".format(gain_diff))
            if not song.export(new_path, gain_diff,
                               indent=2, debug=DEBUG_EXPORT):
                print("  Couldn't export any audio, skipping.")
                shutil.rmtree(new_path)
                return -2

            exported = True
        else:
            print("  Song within {} dB of target, copying files.".format(
                HEADROOM))
            song.copy(new_path)
            exported = False

        song.copy(new_path, audio=False)

        song.files = []
        if exported:
            return 0
        else:
            return 1

    def _process_song_mp(self, song):
        try:
            print("Processing", song.path)

            original_stdout, original_stderr = sys.stdout, sys.stderr
            new_stdout = open(os.devnull, 'w')
            sys.stdout = sys.stderr = new_stdout

            result = self._process_song(song)

            queue.put((result, song.path, song.cache_data))

            sys.stdout, sys.stderr = original_stdout, original_stderr
            new_stdout.close()
        except Exception as e:
            queue.put(ExceptionWrapper(e))

    def _init_mp(self, q):
        global queue
        queue = q

    def _update_num(self, result):
        num = {
            0: 'num_export',
            1: 'num_copied',
            2: 'num_cached',
            -1: 'num_errors',
            -2: 'num_errors',
        }

        setattr(self, num[result], getattr(self, num[result]) + 1)

    def _run(self, start_time):
        for i, s in enumerate(self.songs):
            time_used = int(time.time() - start_time)
            print("Song {}/{}".format(i, self.num_songs))
            print("Time:", datetime.timedelta(seconds=time_used))
            print(s.path)

            result = self._process_song(s)

            self._update_num(result)
            if result != 2:
                self._write_cache(CACHE_FILENAME, s.path, s.cache_data)

            print()

    def _run_mp(self):
        queue = multiprocessing.Queue()
        with multiprocessing.Pool(initializer=self._init_mp,
                                  initargs=(queue,)) as pool:
            pool.map_async(self._process_song_mp, self.songs, 1)

            num_processed = 0
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

                if r != 2:
                    self._write_cache(CACHE_FILENAME, path, cache_data)

                num_processed = self.num_cached + self.num_copied \
                    + self.num_errors + self.num_export

    def run(self):
        try:
            start_time = time.time()

            self._load_config(CONFIG_FILENAME)
            self.cache = self._load_cache(CACHE_FILENAME)
            self.songs = self._find_songs(INPUT_FOLDER)
            self.num_songs = len(self.songs)

            print("Found {} songs.\n".format(self.num_songs))

            if MULTITHREADING:
                self._run_mp()
            else:
                self._run(start_time)

        except KeyboardInterrupt:
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
    Normalizer().run()
