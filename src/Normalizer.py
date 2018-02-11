import json, time, sys, os, shutil, glob

# Add local FFmpeg to path so pydub can use it
os.environ['PATH'] = os.environ['PATH'] + ';{}\\FFmpeg\\bin;'.format(sys.path[0].rpartition('\\')[0])

import pydub

# Volume level below max songs should be adjusted to
GAIN = -16
# Skip recoding if song is HEADROOM dB within GAIN
HEADROOM = 1

INPUT_FOLDER = 'Songs'
OUTPUT_FOLDER = 'Normalized'

# Initalize cache
if os.path.isfile('normalizer_cache.json'):
    with open('normalizer_cache.json',) as cache_file:
        cache = json.load(cache_file)
else:
    cache = {}
    with open('normalizer_cache.json', 'w') as cache_file:
        json.dump(cache, cache_file, indent=2)


def get_audio_list(path):
    """
    Returns list of path names to the audiofiles that are used
    by clone hero in the given path
    """
    used_audio = ['crowd', 'song', 'guitar', 'drums1', 'drums2',
                  'drums3', 'drums4', 'rhythm', 'vocals', 'keys']
    audio_list = []
    for ext in ('{}\\*.mp3'.format(path), '{}\\*.ogg'.format(path)):
        for audio_path in glob.glob(ext):
            if audio_path.rpartition('\\')[2].partition('.')[0] in used_audio:
                audio_list.append(audio_path)

    return audio_list

try:
    # List of paths to all (subdirectories, files in that dir) that contain songs
    songs = []

    # Find all songs
    for root, dirs, files in os.walk(INPUT_FOLDER):
        # print(root)
        if os.path.isfile('{}\\notes.chart'.format(root)) or
           os.path.isfile('{}\\notes.mid'.format(root)):
            # print("Found song: ", root)
            songs.append((root, files))

    print("\nFound {} songs.".format(len(songs)))
    print()

    # Analyze, apply gain, then export songs
    for num, (path, files) in enumerate(songs):
        print("Song {}/{}".format(num + 1, len(songs)))

        # Scan cache for change
        skip = True
        if path in cache:
            for audio_path in get_audio_list(path):
                stat = os.stat(audio_path)
                audio_name = audio_path.rpartition('\\')[2]
                # Don't skip this song if audiofile not in cache,
                # or has been changed since caching
                if audio_name not in cache[path] or
                   cache[path][audio_name] != stat[8]:
                    skip = False
        else:
            skip = False

        if skip:
            print(path)
            print("In cache, skipping\n")
            continue

        # List of (audiosegment, filename, mediainfo) in current song directory
        audio_files = []
        # Dict of audio_filename: last modified
        cache_data = {}

        song = False
        error = False

        # Create one song from all audio files in dir
        for audio_path in get_audio_list(path):
            if not song:
                print("Scanning song:", audio_path)
                song = pydub.AudioSegment.from_file(audio_path)
                audio_files.append((song, audio_path.rpartition('\\')[2], pydub.utils.mediainfo(audio_path)))
            else:
                print(" Adding layer:", audio_path)
                layer = pydub.AudioSegment.from_file(audio_path)
                audio_files.append((layer, audio_path.rpartition('\\')[2], pydub.utils.mediainfo(audio_path)))
                song = song.overlay(layer)

            if not song:
                print("Bad audiofile, skipping\n")
                error = True
                break

            stat = os.stat(audio_path)
            cache_data[audio_path.rpartition('\\')[2]] = stat[8]

        if error: continue

        if not song:
            print(path)
            print("No audio, skipping\n")
            continue

        song_gain = song.dBFS

        print("Volume: {:.1f} dB".format(song_gain))

        # Create new dir
        new_path = '{}\\{}'.format(OUTPUT_FOLDER, path.partition('\\')[2])
        if not os.path.isdir(new_path):
            os.makedirs(new_path)

        # Apply gain and export audio files to new dir
        # Skip if song within HEADROOM dB, and copy files instead
        if abs(GAIN - song_gain) > HEADROOM:
            print("Applying {:.1f} dB of gain...".format(GAIN - song_gain))

            for audio, file_name, info in audio_files:
                audio = audio.apply_gain(GAIN - song_gain)

                print("Exporting ", file_name)
                try:
                    audio.export('{}/{}'.format(new_path, file_name),
                                 format=info['format_name'],
                                 bitrate=info['bit_rate'])
                except KeyboardInterrupt: raise
                except:
                    print("Error exporting ", file_name)

            print()
        else:
            print("Song within {} dB, copying...\n".format(HEADROOM))

        # Copy remaining files
        for f in files:
            if not os.path.isfile('{}\\{}'.format(new_path, f)):
                # print("Copy", f)
                shutil.copy('{}\\{}'.format(path, f), new_path)

        # Update cache
        cache[path] = cache_data
        with open('normalizer_cache.json', 'w') as cache_file:
            json.dump(cache, cache_file, indent=2)

except KeyboardInterrupt:
    print("\nCanceled")

except Exception as e:
    print("Something went wrong:\n")
    print(e)
    print()

print("Press enter to exit")
input()
