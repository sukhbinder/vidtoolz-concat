"""Unit tests for read_orderfile function."""

import pytest
import tempfile
import os
import vidtoolz_concat as w


@pytest.fixture
def temp_orderfile():
    """Create a temporary order file with test data."""
    content = """# Header comment
video1.mp4
video2.mp4
video3.mp4
# Footer comment
"""
    fd, fname = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    yield fname
    os.unlink(fname)


def test_read_orderfile_no_skip(temp_orderfile):
    """Test reading order file without skipping any lines."""
    result = w.read_orderfile(temp_orderfile, skipheader=0, skipfooter=0)
    assert len(result) == 3
    # Get temp dir for expected absolute paths
    tempdir = os.path.dirname(temp_orderfile)
    assert result == [
        os.path.join(tempdir, "video1.mp4"),
        os.path.join(tempdir, "video2.mp4"),
        os.path.join(tempdir, "video3.mp4"),
    ]


def test_read_orderfile_skip_header(temp_orderfile):
    """Test reading order file with skipheader."""
    result = w.read_orderfile(temp_orderfile, skipheader=1, skipfooter=0)
    assert len(result) == 2
    # Get temp dir for expected absolute paths
    tempdir = os.path.dirname(temp_orderfile)
    assert result == [
        os.path.join(tempdir, "video2.mp4"),
        os.path.join(tempdir, "video3.mp4"),
    ]


def test_read_orderfile_skip_footer(temp_orderfile):
    """Test reading order file with skipfooter."""
    result = w.read_orderfile(temp_orderfile, skipheader=0, skipfooter=1)
    assert len(result) == 2
    tempdir = os.path.dirname(temp_orderfile)
    assert result == [
        os.path.join(tempdir, "video1.mp4"),
        os.path.join(tempdir, "video2.mp4"),
    ]


def test_read_orderfile_skip_both(temp_orderfile):
    """Test reading order file with both skipheader and skipfooter."""
    result = w.read_orderfile(temp_orderfile, skipheader=1, skipfooter=1)
    assert len(result) == 1
    tempdir = os.path.dirname(temp_orderfile)
    assert result == [os.path.join(tempdir, "video2.mp4")]


def test_read_orderfile_skip_all(temp_orderfile):
    """Test reading order file where skip removes all files."""
    result = w.read_orderfile(temp_orderfile, skipheader=2, skipfooter=2)
    assert len(result) == 0


def test_read_orderfile_with_comments(temp_orderfile):
    """Test that comment lines are filtered out."""
    content = """# Comment 1
video1.mp4
# Comment 2
video2.mp4
"""
    fd, fname = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    try:
        result = w.read_orderfile(fname, skipheader=0, skipfooter=0)
        assert len(result) == 2
        tempdir = os.path.dirname(fname)
        assert result == [
            os.path.join(tempdir, "video1.mp4"),
            os.path.join(tempdir, "video2.mp4"),
        ]
    finally:
        os.unlink(fname)


def test_read_orderfile_empty_file():
    """Test reading an empty order file."""
    content = ""
    fd, fname = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    try:
        result = w.read_orderfile(fname, skipheader=0, skipfooter=0)
        assert len(result) == 0
    finally:
        os.unlink(fname)


def test_read_orderfile_only_comments():
    """Test reading a file with only comments."""
    content = """# Comment 1
# Comment 2
# Comment 3
"""
    fd, fname = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    try:
        result = w.read_orderfile(fname, skipheader=0, skipfooter=0)
        assert len(result) == 0
    finally:
        os.unlink(fname)


def test_read_orderfile_relative_path():
    """Test that relative paths in order file are resolved correctly."""
    content = """video1.mp4
video2.mp4
"""
    fd, fname = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    try:
        result = w.read_orderfile(fname, skipheader=0, skipfooter=0)
        # Should resolve to absolute paths
        assert len(result) == 2
        assert all(os.path.isabs(f) for f in result)
    finally:
        os.unlink(fname)


def test_read_orderfile_whitespace_handling():
    """Test handling of whitespace in file entries."""
    content = """  video1.mp4
video2.mp4
# Comment
  video3.mp4
"""
    fd, fname = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    try:
        result = w.read_orderfile(fname, skipheader=0, skipfooter=0)
        assert len(result) == 3
        tempdir = os.path.dirname(fname)
        assert result == [
            os.path.join(tempdir, "video1.mp4"),
            os.path.join(tempdir, "video2.mp4"),
            os.path.join(tempdir, "video3.mp4"),
        ]
    finally:
        os.unlink(fname)


def test_read_orderfile_nonexistent_file():
    """Test that reading a nonexistent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        w.read_orderfile("/nonexistent/path/orderfile.txt", skipheader=0, skipfooter=0)


def test_read_orderfile_single_file_no_skip():
    """Test reading an order file with just one file."""
    content = """video1.mp4
"""
    fd, fname = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    try:
        result = w.read_orderfile(fname, skipheader=0, skipfooter=0)
        assert len(result) == 1
        tempdir = os.path.dirname(fname)
        assert result == [os.path.join(tempdir, "video1.mp4")]
    finally:
        os.unlink(fname)


def test_read_orderfile_single_file_skip_header():
    """Test reading an order file with one file and skipheader."""
    content = """# Header comment only
video1.mp4
"""
    fd, fname = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    try:
        result = w.read_orderfile(fname, skipheader=1, skipfooter=0)
        assert len(result) == 0
    finally:
        os.unlink(fname)


def test_read_orderfile_skip_header_without_comments():
    """Test skipping header without comment lines."""
    content = """video1.mp4
video2.mp4
"""
    fd, fname = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    try:
        result = w.read_orderfile(fname, skipheader=1, skipfooter=0)
        assert len(result) == 1
        tempdir = os.path.dirname(fname)
        assert result == [os.path.join(tempdir, "video2.mp4")]
    finally:
        os.unlink(fname)


def test_read_orderfile_multiple_skip_scenarios():
    """Test multiple skip scenarios with different combinations."""
    content = """# Header
# Comment
video1.mp4
video2.mp4
video3.mp4
# Comment
# Footer
# Footer
"""
    fd, fname = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    try:
        # Test: skip 2 headers, skip 2 footers
        result = w.read_orderfile(fname, skipheader=1, skipfooter=1)
        assert len(result) == 1
        tempdir = os.path.dirname(fname)
        assert result == [os.path.join(tempdir, "video2.mp4")]
    finally:
        os.unlink(fname)


def test_read_orderfile_with_num():
    """Test reading order file with num parameter."""
    content = """video1.mp4
video2.mp4
video3.mp4
video4.mp4
video5.mp4
"""
    fd, fname = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    try:
        result = w.read_orderfile(fname, skipheader=0, skipfooter=0, num=2)
        assert len(result) == 2
        tempdir = os.path.dirname(fname)
        assert result == [
            os.path.join(tempdir, "video1.mp4"),
            os.path.join(tempdir, "video2.mp4"),
        ]
    finally:
        os.unlink(fname)


def test_read_orderfile_with_num_and_skip():
    """Test reading order file with num parameter and skip parameters."""
    content = """# Header comment
video1.mp4
video2.mp4
video3.mp4
video4.mp4
# Footer comment
"""
    fd, fname = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    try:
        # Skip header, limit to 2 files
        result = w.read_orderfile(fname, skipheader=1, skipfooter=0, num=2)
        assert len(result) == 2
        tempdir = os.path.dirname(fname)
        assert result == [
            os.path.join(tempdir, "video2.mp4"),
            os.path.join(tempdir, "video3.mp4"),
        ]
    finally:
        os.unlink(fname)


def test_read_orderfile_with_num_and_footer():
    """Test reading order file with num parameter and footer skip."""
    content = """video1.mp4
video2.mp4
video3.mp4
video4.mp4
# Footer comment
"""
    fd, fname = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    try:
        # Skip footer, limit to 2 files
        result = w.read_orderfile(fname, skipheader=0, skipfooter=1, num=2)
        assert len(result) == 2
        tempdir = os.path.dirname(fname)
        assert result == [
            os.path.join(tempdir, "video1.mp4"),
            os.path.join(tempdir, "video2.mp4"),
        ]
    finally:
        os.unlink(fname)


def test_read_orderfile_num_less_than_skip():
    """Test num is smaller than remaining files after skip."""
    content = """# Header
video1.mp4
video2.mp4
video3.mp4
video4.mp4
video5.mp4
"""
    fd, fname = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    try:
        # Skip header, limit to 2 files (only 4 remain after skip)
        result = w.read_orderfile(fname, skipheader=1, skipfooter=0, num=2)
        assert len(result) == 2
        tempdir = os.path.dirname(fname)
        assert result == [
            os.path.join(tempdir, "video2.mp4"),
            os.path.join(tempdir, "video3.mp4"),
        ]
    finally:
        os.unlink(fname)


def test_read_orderfile_num_zero():
    """Test num=0 returns empty list."""
    content = """video1.mp4
video2.mp4
video3.mp4
"""
    fd, fname = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    try:
        result = w.read_orderfile(fname, skipheader=0, skipfooter=0, num=0)
        assert len(result) == 0
    finally:
        os.unlink(fname)


def test_read_orderfile_num_none_same_as_without_num():
    """Test that num=None behaves same as not providing num."""
    content = """video1.mp4
video2.mp4
video3.mp4
"""
    fd, fname = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    try:
        result = w.read_orderfile(fname, skipheader=0, skipfooter=0, num=None)
        result2 = w.read_orderfile(fname, skipheader=0, skipfooter=0)
        assert len(result) == len(result2)
        assert result == result2
    finally:
        os.unlink(fname)
