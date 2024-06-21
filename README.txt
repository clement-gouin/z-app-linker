usage: linker.py [-h] [--with-debug] [--fast] [-d [data.txt]]

links [Treasure Finder/On The Quizz/Cross-Roads] data between them.
(see data.sample.txt for data format)

documentations:
* Treasure Finder -> https://github.com/clement-gouin/treasure-finder
* On The Quizz -> https://github.com/clement-gouin/on-the-quizz
* Cross-Roads -> https://github.com/clement-gouin/cross-roads

options:
  -h, --help            show this help message and exit
  --with-debug          create debug Cross-Roads link with all links within
  --fast                resolve links in dependency order (faster)
  -d [data.txt], --data [data.txt]
                        data file path (default: data.txt)
