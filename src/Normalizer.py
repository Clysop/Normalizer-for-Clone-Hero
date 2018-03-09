import json, time, sys, os, shutil, traceback, datetime

# Add local FFmpeg to path so pydub can use it
os.environ['PATH'] = os.environ['PATH'] + ';{}\\FFmpeg\\bin;'.format(sys.path[0].rpartition('\\')[0])

import pydub

# Volume level below max songs should be adjusted to
GAIN = -16
# Skip recoding if song is HEADROOM dB within GAIN
HEADROOM = 1
# List of files CH uses
USED_AUDIO = ['crowd', 'song', 'guitar', 'drums', 'drums_1', 'drums_2',
              'drums_3', 'drums_4', 'rhythm', 'vocals', 'keys']

INPUT_FOLDER = 'Songs'
OUTPUT_FOLDER = 'Normalized'

used_audio = []
for f in USED_AUDIO:
    used_audio.append(f + '.ogg')
    used_audio.append(f + '.mp3')
USED_AUDIO = used_audio

try:
    start_time = time.time()

    # Initalize cache
    if os.path.isfile('normalizer_cache.json'):
        with open('normalizer_cache.json',) as cache_file:
            cache = json.load(cache_file)
    else:
        cache = {}
        with open('normalizer_cache.json', 'w') as cache_file:
            json.dump(cache, cache_file, indent=2)

    # List of paths to all (subdirectories, files in that dir) that contain songs
    songs = []

    # Find all songs
    for root, dirs, files in os.walk(INPUT_FOLDER):
        # print(root)
        if os.path.isfile('{}\\notes.chart'.format(root)) or os.path.isfile('{}\\notes.mid'.format(root)):
            # print("Found song: ", root)
            songs.append((root, files))

    print("Found {} songs.\n".format(len(songs)))

    # Analyze, apply gain, then export songs
    processed = 0
    copied = 0
    skipped = 0
    cached = 0
    for num, (path, files) in enumerate(songs):
        print("Song {}/{}:".format(num + 1, len(songs)))
        print(path)

        # Skip if no audiofiles in song folder
        for f in files:
            if f in USED_AUDIO: break
        else:
            print("No audio, skipping\n")
            skipped += 1
            continue

        # Scan cache for change
        skip = True
        if path in cache:
            for filename in (f for f in files if f in USED_AUDIO):
                audio_path = path + '\\' + filename
                stat = os.stat(audio_path)
                # Don't skip this song if audiofile not in cache,
                # or has been changed since caching
                if filename not in cache[path] or cache[path][filename] < stat[8]:
                    skip = False
        else:
            skip = False

        if skip:
            print("In cache, skipping\n")
            cached += 1
            continue

        # List of (audiosegment, filename, mediainfo) in current song directory
        audio_files = []
        # List if filenames that couldn't be read, or are zero length
        bad_files = []

        # Fill audio_files with audio in folder, only reads audio CH uses
        for filename in (f for f in files if f in USED_AUDIO):
            print('  Reading:', filename)
            audio_path = path + '\\' + filename

            try:
                audio = pydub.AudioSegment.from_file(audio_path)
            except KeyboardInterrupt:
                raise
            except pydub.exceptions.CouldntDecodeError:
                print("    Error reading")
                bad_files.append(filename)
                continue
            except MemoryError:
                print("    This song is too damn big, can't process.")
                bad_files.append(filename)
                continue

            if len(audio) == 0:
                print("    Zero length, skipping")
                bad_files.append(filename)
                continue

            audio_files.append((audio, filename, pydub.utils.mediainfo(audio_path)))

        if len(audio_files) == 0:
            print()
            skipped += 1
            continue

        # Sort audio_files so that longest audiofile is first
        def sort_audio(element):
            return len(element[0])

        audio_files.sort(key=sort_audio, reverse=True)

        # Create one song from all layers
        song = audio_files[0][0]
        for audio, filename, info in audio_files[1:]:
            song = song.overlay(audio)

        song_gain = song.dBFS
        print("Volume: {:.1f} dB".format(song_gain))

        # Create new dir
        new_path = OUTPUT_FOLDER + '\\' + path.partition('\\')[2]
        if not os.path.isdir(new_path):
            os.makedirs(new_path)

        # Apply gain and export audio files to new dir
        # Skip if song within HEADROOM dB, and copy files instead
        if abs(GAIN - song_gain) > HEADROOM:
            print("Applying {:.1f} dB of gain...".format(GAIN - song_gain))

            for audio, filename, info in audio_files:
                audio = audio.apply_gain(GAIN - song_gain)

                print("  Exporting:", filename)
                try:
                    audio.export(new_path + '\\' + filename,
                                 format=info['format_name'],
                                 bitrate=info['bit_rate'])
                except KeyboardInterrupt:
                    raise
                except pydub.exceptions.CouldntEncodeError:
                    print("    Error exporting")
                    bad_files.append(filename)

            print()
            processed += 1
        else:
            print("Song within {} dB, copying...\n".format(HEADROOM))
            copied += 1

        # Dict of audio_filename: last modified
        cache_data = {}

        # Copy remaining files and get cache_data, skips bad files
        for filename in files:
            # Remove any bad exports
            if filename in bad_files and os.path.isfile(new_path + '\\' + filename):
                os.remove(new_path + '\\' + filename)
            # Copy remaining files
            elif filename not in bad_files and not os.path.isfile(new_path + '\\' + filename):
                shutil.copy(path + '\\' + filename, new_path)

            if filename in USED_AUDIO:
                cache_data[filename] = int(time.time())

        # Update cache
        cache[path] = cache_data
        with open('normalizer_cache.json', 'w') as cache_file:
            json.dump(cache, cache_file, indent=2)

except KeyboardInterrupt:
    print("\nCanceled\n")

except Exception as e:
    print("\nSomething went wrong:\n")
    traceback.print_exc()
    print()

else:
    print("Processing complete!\n")

time_used = datetime.time(second=int(time.time() - start_time))
print("  Processed: {:>5}".format(processed))
print("  Copied:    {:>5}".format(copied))
print("  Skipped:   {:>5}".format(skipped))
print("  Cached:    {:>5}".format(cached))
print("\nTime used:", str(time_used))

print("\nPress enter to exit")
input()
