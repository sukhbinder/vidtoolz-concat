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
