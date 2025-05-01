import pytest
import vidtoolz_concat as w
import pytest
from unittest.mock import patch, mock_open

from argparse import ArgumentParser


def test_create_parser():
    subparser = ArgumentParser().add_subparsers()
    parser = w.create_parser(subparser)

    assert parser is not None

    result = parser.parse_args(["hello.txt"])
    assert result.inputfile == "hello.txt"
    assert result.output is None
    assert result.section is None
    assert result.nsec is None
    assert result.use_moviepy is False

    result = parser.parse_args(["-i", "1.mov", "-i", "2.mov"])
    assert result.inputfile is None
    assert result.input == ["1.mov", "2.mov"]


def test_plugin(capsys):
    w.concat_plugin.hello(None)
    captured = capsys.readouterr()
    assert "Hello! This is an example ``vidtoolz`` plugin." in captured.out


@pytest.fixture
def mock_filesystem(tmpdir):
    """Set up a temporary file system with some dummy files."""
    files = []
    for i in range(5):
        f = tmpdir.join(f"file_{i}.mp4")
        f.write("")  # Create an empty file
        files.append(str(f))
    return files


@patch("os.remove", return_value=0)
@patch("os.system", return_value=0)  # Mock os.system to prevent actual system calls
@patch("os.path.exists", return_value=True)  # Mock os.path.exists to always return True
def test_make_video(mock_exists, mock_system, mock_filesystem):
    files = mock_filesystem
    fname = "output.mp4"

    # Call the function
    result = w.make_video(files, fname)

    # Assertions
    assert result == 0  # Ensure the command returned successfully
    mock_system.assert_called_once()  # Verify os.system was called
    # Verify the command structure
    cmd = mock_system.call_args[0][0]
    assert "ffmpeg" in cmd
    assert fname in cmd
    assert "mylist.txt" in cmd


@patch("os.remove", return_value=0)
@patch("os.system", return_value=0)
@patch("os.path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open)  # Mock file opening
@patch(
    "os.path.getctime", side_effect=lambda x: int(x.split("_")[-1].split(".")[0])
)  # Mock file creation times
def test_concat(mock_getctime, mock_open_file, mock_exists, mock_system, tmpdir):
    # Create a mock input file with paths to mock video files
    input_file = tmpdir.join("input.txt")
    video_files = [tmpdir.join(f"file_{i}.mp4") for i in range(5)]
    for f in video_files:
        f.write("")  # Create empty files
    input_file.write("\n".join(str(f) for f in video_files))

    # Call concat without sections
    output = w.concat(str(input_file), "output.mp4", section=False)

    # Assertions for non-section mode
    assert "output.mp4" in output
    mock_system.assert_called()  # os.system should be called
    assert mock_open_file.called  # Ensure the file was opened

    # Call concat with sections
    output = w.concat(str(input_file), "output.mp4", nsec=40)

    # Assertions for section mode
    assert "output.mp4" in output  # Check the generated file name
