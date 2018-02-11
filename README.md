# Normalizer-for-Clone-Hero
A small python app that normalizes the volume of a Clone Hero library

How to use:

1. Unpack file
2. Move Songs folder into Normalizer folder
3. Run Normalizer.exe
4. Wait
5. ...
6. Wait

Exit with ctrl+c, or just close the window.

The program will not touch your original songs, so don't worry about them getting messed up. You could back them up if you really worry, but I don't think its possible for them to get broken.

The program caches the work it has done, so you can exit it whenever you want, and it will continue where it stopped next time you start it. This also means it won't scan everything again if you add new songs. If you wan't to rescan, just delete normalizer_cache.json

The program will try to put everything to -16 dB, there's no way to change that. If people want it, I can add an option for it.

I haven't tested it on anything other than my library, but it has worked great so far. The only problem is that it is very slow. It takes about 3 to 5 seconds per song, so I recommend leaving it on over night if you have more than 1000 songs. Since I haven't tested it much, it might crash in some cases, or it might not run at all for some people. I haven't tested it on any other PCs than mine. Please don't hesitate to report any crashes.
