usage: linker.py [-h] [--with-debug] [-f] [-d [data.txt]]

links z-app data between them.
(see data.sample.txt for data format)
separators:
----- https://github.com/clement-gouin/z-app
===== https://github.com/clement-gouin/z-treasure-finder
+++++ https://github.com/clement-gouin/z-on-the-quizz
##### https://github.com/clement-gouin/z-cross-roads
@@@@@ https://github.com/clement-gouin/z-dice-roller

options:
  -h, --help            show this help message and exit
  --with-debug          create debug Cross-Roads link with all links within
  -f, --fast            resolve links in dependency order (faster)
  -d [data.txt], --data [data.txt]
                        data file path (default: data.txt)
