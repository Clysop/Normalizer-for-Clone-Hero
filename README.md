# Normalizer for Clone Hero
A small python app that normalizes the volume of a Clone Hero library

# How to use:

1. Unpack file
2. Move Normalizer.exe to Clone Hero folder (where Songs folder is)
3. Run Normalizer.exe
4. Wait
5. ...
6. Wait
7. After it is done, rename Songs folder to something else (e.g. Original Songs)
8. Rename Normalized to Songs. These are now your new, normalized songs.

Exit with ctrl+c, or just close the window.

You should rescan your songs in clone hero. This should be fast, but it might say "updating charts" for a while, this is normal.

The program will not touch your original songs, so don't worry about them getting messed up. It also caches the work it has done, so you can exit it whenever you want, and it will continue where it stopped next time you start it. This also means it won't scan everything again if you add new songs. If you want to rescan everything, just delete normalizer_cache.json

# Changelog:

3.0:
- Complete rewrite. Huge performance increase.
- Now integrates more directly with FFmpeg, which increases efficiency.
- Multithreading has been added, which will make the program process a song for each core your CPU has. If you have a 4-core CPU, the program will be 4 times faster.
- A config file will be generated the first time you run the program. Here you can set the target volume, the headroom for copying instead of recoding the audio, enabling debug info when loading and/or exporting, and set multithreading. Warning: debug only works when multithreading is set to False, as multithreading disables much of the output when processing.
- A crash log will be saved if the program crashes, making it easier to report it to me so I can fix it.

2.1: Fixed a cache bug. Program should be more robust now and handle songs that are broken in various ways.

2.0:
- Packaged all files into the exe, the program is now one file only. Run it directly from your CH folder where your original songs folder is. You can still use your normalizer_cache, so don't delete that.
- Fixed a bug where very big songs would crash the program, they are now skipped.
- Fixed a bug where songs with drum stems (individual audio files for drums) weren't processed properly, leaving the drum files untouched.
- IMPORTANT: rerun the normalizer on your original library, but use your old normalizer_cache, the program will redo all songs with drum stems.

1.3: Prints statistics (songs processed, time used, etc.) when program is stopped or when it is done.

1.2: Significantly changed the song scanning method. Should avoid making some mistakes on multifile songs. Also made it more secure against crashes. IMPORTANT: Everyone should rerun their original library with this new update. It might fix some songs that weren't processed properly.

1.1: Fixed some bugs. It will now skip recoding songs that are within 1 dB of the set volume, and copy them instead. This will save some time.
