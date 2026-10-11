# vidtoolz-concat

[![PyPI](https://img.shields.io/pypi/v/vidtoolz-concat.svg)](https://pypi.org/project/vidtoolz-concat/)
[![Changelog](https://img.shields.io/github/v/release/sukhbinder/vidtoolz-concat?include_prereleases&label=changelog)](https://github.com/sukhbinder/vidtoolz-concat/releases)
[![Tests](https://github.com/sukhbinder/vidtoolz-concat/workflows/Test/badge.svg)](https://github.com/sukhbinder/vidtoolz-concat/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/sukhbinder/vidtoolz-concat/blob/main/LICENSE)

Concat videos using ffmpeg 


## Installation

First install [vidtoolz](https://github.com/sukhbinder/vidtoolz).

```bash
pip install vidtoolz
```

Then install this plugin in the same environment as your vidtoolz application.

```bash
vidtoolz install vidtoolz-concat
```
## Platform Compatibility

This tool is fully tested and compatible with:
- **macOS**
- **Windows** (tested on Windows 10/11 with Python 3.8+)

> **Note:** On Windows, ensure `ffmpeg` and `moviepy` are installed via the respective package managers (e.g., `pip install moviepy` and download `ffmpeg.exe` from the official releases if not bundled by vidtoolz).

## Usage

type ``vidtoolz-concat --help`` to get help

```
usage: vid concat [-h] [-o OUTPUT] [-s] [-n NSEC] [-i INPUT] [-cd CHANGE_DIR]
                  [-e] [-um]
                  [inputfile]

Concat videos using ffmpeg

positional arguments:
  inputfile             Text file having names of files to concat

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Folder where files are (default: None)
  -s, --section         If given sections Video by `nsec` (default: False)
  -n NSEC, --nsec NSEC  Section Video by `nsec` (default: 500)
  -i INPUT, --input INPUT
                        Input files (default: None)
  -cd CHANGE_DIR, --change-dir CHANGE_DIR
                        if Provided, go to this folder, before anything.
  -e, --encoding        if Provided, Use re-encoding
  -um, --use-moviepy    if Provided, Use moviepy
  -sh, --skipheader     Skip header lines in the input file (default: 0)
  -sf, --skipfooter     Skip footer lines in the input file (default: 0)
  -num, --num NUM       Number of files to read from the input file (default: None, reads all)

```

### Add text to selected clips

An order file can mix plain video paths with CSV rows that add text to a
specific clip before concatenation. Plain rows are concatenated unchanged. A
text row has six fields:

```text
videofile,text,"the actual text to add",starttime,duration,position
```

For example, this adds “Hello” to `video.mp4` starting at 3 seconds, for 5
seconds, near the upper right corner:

```text
video.mp4,text,"Hello",3,5,top-right
```

`starttime` and `duration` are measured within that clip. Times can be given in
seconds or `MM:SS` / `HH:MM:SS` form. If the requested text interval runs past
the end of the clip, concat warns and shortens the text duration to fit. If the
start time is at or past the clip end, it warns and leaves that clip unchanged.

Supported positions:

- `top-left`: near the upper left corner
- `top-right`: near the upper right corner
- `bottom-left`: near the lower left corner
- `bottom-right`: near the lower right corner
- `center`: centered in the frame
- `bottom`: centered along the lower edge

FFmpeg renders text by default. Pass `--use-moviepy` to use MoviePy for both
text rendering and the final concatenation. The sample `tests/orderfilewithtext.txt`
demonstrates mixing plain video rows with text rows.


## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:

```bash
cd vidtoolz-concat
python -m venv venv
source venv/bin/activate
```
To set up this plugin locally , in windows, checkout the code.

```bash
cd vidtoolz-concat
python -m venv venv
venv\Scripts\activate
pip install -e '.[test]'
```
  
Now install the dependencies and test dependencies:
```bash
pip install -e '.[test]'
```
To run the tests:
```bash
python -m pytest
```
