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

```


## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:
```bash
cd vidtoolz-concat
python -m venv venv
source venv/bin/activate
```
Now install the dependencies and test dependencies:
```bash
pip install -e '.[test]'
```
To run the tests:
```bash
python -m pytest
```
