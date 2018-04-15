import os
import json
import time
import shutil
import logging
import datetime

import song

INPUT_FOLDER = 'Songs'
OUTPUT_FOLDER = 'Normalized'

TARGET_GAIN = -16
HEADROOM = 1


logging.basicConfig(filename='crash_log.txt', filemode='w')

if os.path.isfile('normalizer_cache.json'):
    with open('normalizer_cache.json',) as cache_file:
        cache = json.load(cache_file)
else:
    cache = {}
    with open('normalizer_cache.json', 'w') as cache_file:
        json.dump(cache, cache_file, indent=2)

try:
    start_time = time.time()

    print("Scanning folders...")
    songs = []
    for root, dirs, files in os.walk(INPUT_FOLDER):
        if os.path.isfile(os.path.join(root, 'notes.chart')) or \
           os.path.isfile(os.path.join(root, 'notes.mid')):
            songs.append(song.Song(root))

    songs.sort(key=lambda s: s.path)
    num_songs = len(songs)

    print("Found {} songs.\n".format(num_songs))

    num_exported = 0
    num_copied = 0
    num_cached = 0
    num_errors = 0

    for (i, s) in enumerate(songs):
        print("Song {}/{}".format(i + 1, num_songs))
        print("Time:", datetime.timedelta(seconds=int(time.time() - start_time)))
        print(s.path)

        s.scan_files()

        if s.path in cache and s.check_cache(cache[s.path]):
            print("  Song in cache, skipping.\n")
            num_cached += 1
            continue

        try:
            s.load_files(indent=2)
        except AssertionError:
            print("  Couldn't load any audio, skipping.\n")
            num_errors += 1
            continue

        volume = s.get_volume()
        print('\n  Volume: {:.1f} dBFS.'.format(volume))

        new_path = os.path.join(OUTPUT_FOLDER, s.path.partition('/')[2])
        if not os.path.isdir(new_path):
            os.makedirs(new_path)

        gain_diff = TARGET_GAIN - volume
        if abs(gain_diff) > HEADROOM:
            print("  Applying {:.2f} dB of gain.\n".format(gain_diff))
            try:
                cache[s.path] = s.export(new_path, gain_diff, indent=2)
            except AssertionError:
                print("  Couldn't export any audio, skipping.\n")
                num_errors += 1
                shutil.rmtree(new_path)
                continue

            num_exported += 1
        else:
            print("  Song within {} dB of target, copying files.".format(HEADROOM))
            cache[s.path] = s.copy(new_path)
            num_copied += 1

        s.copy(new_path, audio=False)
        print()

        with open('normalizer_cache.json', 'w') as cache_file:
            json.dump(cache, cache_file, indent=2)

except KeyboardInterrupt:
    print("\nInterrupted.\n")
except BaseException:
    print("!!! CRASH !!!\nSee crash_log.txt for info.\n")
    logging.exception("\n\nSomething bad happened.\n\
Send this to Clysop. (Discord: Clysop#3650)\n\n")
else:
    print("Done!\n")

time_used = datetime.timedelta(seconds=int(time.time() - start_time))
print("  Exported: {:>5}".format(num_exported))
print("  Copied:   {:>5}".format(num_copied))
print("  Cached:   {:>5}".format(num_cached))
print("  Skipped:  {:>5}".format(num_errors))
print("\nTime used:", str(time_used))

input("\nPress enter to exit")
