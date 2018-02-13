import json, time, sys, os, shutil, glob, traceback

# Add local FFmpeg to path so pydub can use it
os.environ['PATH'] = os.environ['PATH'] + ';{}\\FFmpeg\\bin;'.format(sys.path[0].rpartition('\\')[0])

import pydub

# Volume level below max songs should be adjusted to
GAIN = -16
# Skip recoding if song is HEADROOM dB within GAIN
HEADROOM = 1
# List of files CH uses
USED_AUDIO = ['crowd', 'song', 'guitar', 'drums1', 'drums2',
              'drums3', 'drums4', 'rhythm', 'vocals', 'keys']

INPUT_FOLDER = 'Songs'
OUTPUT_FOLDER = 'Normalized'

used_audio = []
for f in USED_AUDIO:
    used_audio.append(f + '.ogg')
    used_audio.append(f + '.mp3')
USED_AUDIO = used_audio

# Initalize cache
if os.path.isfile('normalizer_cache.json'):
    with open('normalizer_cache.json',) as cache_file:
        cache = json.load(cache_file)
else:
    cache = {}
    with open('normalizer_cache.json', 'w') as cache_file:
        json.dump(cache, cache_file, indent=2)

# Start of main code
try:
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
    for num, (path, files) in enumerate(songs):
        print("Song {}/{}:".format(num + 1, len(songs)))
        print(path)

        # Skip if no audiofiles in song folder
        for f in files:
            if f in USED_AUDIO: break
        else:
            print("No audio, skipping\n")
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
            except KeyboardInterrupt: raise
            except:
                print("    Error reading")
                bad_files.append(filename)
                continue

            if len(audio) == 0:
                print("    Zero length, skipping")
                bad_files.append(filename)
                continue

            audio_files.append((audio, filename, pydub.utils.mediainfo(audio_path)))

        # Sort audio_files so that longest audiofile is first
        def sort_audio(element):
            return len(element[0])

        audio_files.sort(key=sort_audio, reverse=True)

        # Create one song from all layers
        if len(audio_files) > 1:
            sample_rate = int(audio_files[0][2]['sample_rate'].split('.')[0])
            song = pydub.AudioSegment.silent(len(audio_files[0][0]), frame_rate=sample_rate)
            for audio, audio_path, info in audio_files:
                song = song.overlay(audio)
        else:
            song = audio_files[0][0]

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
                except KeyboardInterrupt: raise
                except:
                    print("    Error exporting")

            print()
        else:
            print("Song within {} dB, copying...\n".format(HEADROOM))

        # Dict of audio_filename: last modified
        cache_data = {}

        # Copy remaining files and get cache_data, skips bad files
        for filename in files:
            if filename not in bad_files and not os.path.isfile(new_path + '\\' + filename):
                shutil.copy(path + '\\' + filename, new_path)

            if filename in USED_AUDIO:
                cache_data[filename] = int(time.time())

        # Update cache
        cache[path] = cache_data
        with open('normalizer_cache.json', 'w') as cache_file:
            json.dump(cache, cache_file, indent=2)

except KeyboardInterrupt:
    print("\nCanceled")

except Exception as e:
    print("\nSomething went wrong:\n")
    traceback.print_exc()
    print()

print("Press enter to exit")
input()
