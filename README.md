# Normalizer for Clone Hero
A small python app that normalizes the volume of a Clone Hero library

# How to use:

1. Unpack file
2. Move Songs folder into Normalizer folder
3. Run Normalizer.exe
4. Wait
5. ...
6. Wait
7. After it is done, move Normalized folder back to Clone Hero folder and rename it Songs

Exit with ctrl+c, or just close the window.

The program will not touch your original songs, so don't worry about them getting messed up. It also caches the work it has done, so you can exit it whenever you want, and it will continue where it stopped next time you start it. This also means it won't scan everything again if you add new songs. If you want to rescan everything, just delete normalizer_cache.json

The program will try to put everything to -16 dB, there's no way to change that. If people want it, I can add an option for it.

The executable is generated with pyinstaller, to use the one in this repository, FFmpeg must be added to the root folder.

# Changelog:

1.3: Prints statistics (songs processed, time used, etc.) when program is stopped or when it is done.

1.2: Significantly changed the song scanning method. Should avoid making some mistakes on multifile songs. Also made it more secure against crashes. IMPORTANT: Everyone should rerun their original library with this new update. It might fix some songs that weren't processed properly.

1.1: Fixed some bugs. It will now skip recoding songs that are within 1 dB of the set volume, and copy them instead. This will save some time.
