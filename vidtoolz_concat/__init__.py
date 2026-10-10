import vidtoolz
import os
import numpy as np
import tempfile
import moviepy as mpy
import imageio_ffmpeg

import re
import csv
import warnings
from argparse import RawDescriptionHelpFormatter


def sanitize_string(text: str) -> str:
    text = text.replace(" ", "_").strip()
    return re.sub(r"[^A-Za-z0-9._-]", "", text)


def read_orderfile(fname, skipheader=0, skipfooter=0, num=None):
    fname = os.path.abspath(fname)
    fdir = os.path.dirname(fname)

    with open(fname, "r") as fin:
        files = fin.readlines()

    files = [f.strip() for f in files if not f.strip().startswith("#")]

    # Remove header/footer
    if skipfooter == 0:
        files = files[skipheader:]
    else:
        files = files[skipheader:-skipfooter]

    # Keep only the next `num` files
    if num is not None:
        files = files[:num]

    mov = [os.path.join(fdir, f) for f in files]
    return mov


def read_orderfile_entries(fname, skipheader=0, skipfooter=0, num=None):
    """Read plain video rows and optional per-video text instructions."""
    fname = os.path.abspath(fname)
    folder = os.path.dirname(fname)
    with open(fname, "r", newline="") as fin:
        lines = [line.strip() for line in fin if line.strip() and not line.strip().startswith("#")]

    if skipfooter == 0:
        lines = lines[skipheader:]
    else:
        lines = lines[skipheader:-skipfooter]
    if num is not None:
        lines = lines[:num]

    entries = []
    for line in lines:
        try:
            fields = next(csv.reader([line], skipinitialspace=True, strict=True))
        except (csv.Error, StopIteration) as exc:
            raise ValueError(f"Invalid order-file row: {line!r}") from exc

        if len(fields) > 1 and fields[1].strip() == "text":
            if len(fields) != 6:
                raise ValueError(
                    "Text rows must use: videofile,text,\"text to add\",starttime,duration,position"
                )
            entries.append(
                {
                    "file": os.path.join(folder, fields[0].strip()),
                    "text": fields[2],
                    "starttime": fields[3].strip(),
                    "duration": fields[4].strip(),
                    "position": fields[5].strip(),
                }
            )
        else:
            entries.append({"file": os.path.join(folder, line), "text": None})
    return entries


def _to_seconds(value):
    """Convert seconds or MM:SS/HH:MM:SS values to seconds."""
    if isinstance(value, (int, float)):
        return float(value)
    parts = [float(part) for part in str(value).split(":")]
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    raise ValueError(f"Invalid time value: {value!r}")


def _render_text_entries(entries, tempdir, use_moviepy=False):
    """Render annotated entries to temporary clips and return concat inputs."""
    import moviepy
    # vidtoolz-add-text imports this helper from moviepy.tools. MoviePy 2 moved
    # it out of that module, so provide the compatible parser when it is absent.
    import moviepy.tools as moviepy_tools

    if not hasattr(moviepy_tools, "convert_to_seconds"):
        moviepy_tools.convert_to_seconds = _to_seconds

    # The sibling add-text package uses MoviePy's pre-2.0 top-level exports.
    if not hasattr(moviepy, "VideoFileClip"):
        from moviepy.video.io.VideoFileClip import VideoFileClip
        from moviepy.Clip import Clip
        from moviepy.video.VideoClip import TextClip, VideoClip
        from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
        from moviepy.video.compositing.concatenate import concatenate_videoclips
        from moviepy.video import fx

        for modern, legacy in (("with_duration", "set_duration"), ("with_start", "set_start")):
            if not hasattr(Clip, modern):
                setattr(Clip, modern, getattr(Clip, legacy))
        if not hasattr(VideoClip, "with_position"):
            VideoClip.with_position = VideoClip.set_position
        if not hasattr(Clip, "with_effects"):
            def with_effects(clip, effects):
                for effect in effects:
                    clip = effect.apply(clip)
                return clip

            Clip.with_effects = with_effects

        def legacy_text_clip(
            *, font=None, text=None, font_size=None, stroke_width=0,
            stroke_color=None, color="black", margin=None, **kwargs
        ):
            # Adapt the sibling package's MoviePy 2.1 TextClip keywords to the
            # older TextClip signature in MoviePy 2.0.dev2.
            return TextClip(
                txt=text,
                font=font,
                fontsize=font_size,
                stroke_width=stroke_width,
                stroke_color=stroke_color,
                color=color,
                **kwargs,
            )

        moviepy.VideoFileClip = VideoFileClip
        moviepy.TextClip = legacy_text_clip
        moviepy.CompositeVideoClip = CompositeVideoClip
        moviepy.concatenate_videoclips = concatenate_videoclips
        moviepy.vfx = fx

    # CrossFadeIn/Out were removed in the installed MoviePy development build.
    # Keep the sibling renderer usable there; the overlay still renders at full
    # opacity for its requested interval.
    import moviepy.video.fx as moviepy_fx

    class _IdentityEffect:
        def apply(self, clip):
            return clip

    for name in ("CrossFadeIn", "CrossFadeOut"):
        if not hasattr(moviepy_fx, name):
            setattr(moviepy_fx, name, lambda duration: _IdentityEffect())

    from vidtoolz_add_text.add_text import (
        add_text_to_video,
        add_text_to_video_ffmpeg,
    )

    rendered = []
    for index, entry in enumerate(entries):
        source = entry["file"]
        if entry["text"] is None:
            rendered.append(source)
            continue

        start = _to_seconds(entry["starttime"])
        duration = _to_seconds(entry["duration"])
        if start < 0 or duration <= 0:
            raise ValueError("Text start time must be nonnegative and duration must be positive")
        positions = {
            "top-left", "top-right", "bottom-left", "bottom-right", "center", "bottom"
        }
        if entry["position"] not in positions:
            raise ValueError(
                f"Invalid text position {entry['position']!r}; expected one of "
                f"{', '.join(sorted(positions))}."
            )

        probe = mpy.VideoFileClip(source)
        try:
            clip_duration = probe.duration
        finally:
            probe.close()

        if start >= clip_duration:
            warnings.warn(
                f"Text for {source!r} starts at {start:g}s, at or after the clip duration "
                f"({clip_duration:g}s); leaving this clip unchanged.",
                UserWarning,
            )
            rendered.append(source)
            continue

        actual_duration = min(duration, clip_duration - start)
        if actual_duration < duration:
            warnings.warn(
                f"Text duration for {source!r} was shortened from {duration:g}s to "
                f"{actual_duration:g}s to fit the clip duration ({clip_duration:g}s).",
                UserWarning,
            )

        output = os.path.join(tempdir, f"text-{index}.mp4")
        if use_moviepy:
            clip, fps = add_text_to_video(
                source,
                entry["text"],
                start,
                None,
                entry["position"],
                duration=actual_duration,
            )
            try:
                clip.write_videofile(
                    output,
                    codec="libx264",
                    fps=fps,
                    audio_codec="aac",
                    temp_audiofile=os.path.join(tempdir, f"text-audio-{index}.m4a"),
                    remove_temp=True,
                )
            finally:
                clip.close()
        else:
            add_text_to_video_ffmpeg(
                input_video_path=source,
                output_video_path=output,
                text=entry["text"],
                start_time=start,
                position=entry["position"],
                duration=actual_duration,
            )
        rendered.append(output)
    return rendered


def create_concat_movie(inputfile, output, onlyaudio=False):
    if isinstance(inputfile, list):
        files = inputfile
        folder = os.path.dirname(inputfile[0])
    else:
        inputfile = os.path.abspath(inputfile)
        folder = os.path.dirname(inputfile)
        with open(inputfile, "r") as fin:
            files = fin.readlines()

    files = [os.path.join(folder, file.strip()) for file in files]
    clips = [mpy.VideoFileClip(file) for file in files]

    clip = mpy.concatenate_videoclips(clips)

    # Write out only audio file also if there is an audio
    audio = clip.audio
    if audio:
        aoutput_path = f"{output}-audio.mp3"
        if hasattr(audio, "with_fps"):
            audio = audio.with_fps(44100)
        else:
            audio = audio.set_fps(44100)
        audio.write_audiofile(aoutput_path)
        print("{} mp3 created".format(aoutput_path))

    # write out video
    if not onlyaudio:
        output_path = output
        if os.path.exists(output_path):
            os.remove(output_path)

        clip.write_videofile(
            output_path,
            temp_audiofile="out.m4a",
            audio=True,
            audio_codec="aac",
            codec="libx264",
            fps=60,
        )
        print("{} mp4 created".format(output_path))

    _ = [clip.close() for clip in clips]
    return output_path


def determine_output_path(input_file, output_file, tag="notag"):
    input_dir, input_filename = os.path.split(input_file)
    name, _ = os.path.splitext(input_filename)

    if output_file:
        output_dir, output_filename = os.path.split(output_file)
        if not output_dir:  # If no directory is specified, use input file's directory
            return os.path.join(input_dir, output_filename)
        return output_file
    else:
        return os.path.join(input_dir, f"{name}_{tag}_concat.mp4")


def make_video(files, fname, encoding=False):
    if os.path.exists(fname):
        os.remove(fname)
    base_name = os.path.basename(fname)
    bname, ext = os.path.splitext(base_name)
    tempdir = tempfile.gettempdir()

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    out_file = os.path.join(tempdir, "{}_mylist.txt".format(bname))
    with open(out_file, "w") as fout:
        for f in files:
            if os.path.exists(f):
                fout.write("file '{}'\n".format(f))
    if encoding:
        cmdline = "{0} -f concat -safe 0 -i {1} -c:v libx264 -crf 23 -preset fast -c:a aac {2}".format(
            ffmpeg, out_file, fname
        )
    else:
        cmdline = "{0} -f concat -safe 0 -i {1} -c copy {2}".format(
            ffmpeg, out_file, fname
        )

    print(cmdline)
    iret = os.system(cmdline)
    print(cmdline)
    return iret


def division_list(number, step):
    result = []
    current = step
    while current < number:
        result.append(current)
        current += step
    result.append(number)
    return result


def make_stage_video(fname, files, breaks, encoding=False):
    fileprefix, ext = os.path.splitext(fname)
    beg = 0
    for i, b in enumerate(breaks):
        fname = "{0}_{1}_{2}.mp4".format(fileprefix, i, beg)
        iret = make_video(files[beg : b + 1], fname, encoding)
        print("Return code is ", iret)
        beg = b + 1


def concat(
    inputfile, fname: str = None, section: int = None, nsec: int = None, encoding=False
):
    if isinstance(inputfile, list):
        files = inputfile
        folder = os.path.dirname(os.path.abspath(inputfile[0]))
    else:
        inputfile = os.path.abspath(inputfile)
        folder = os.path.dirname(inputfile)
        with open(inputfile, "r") as fin:
            files = fin.readlines()

    if fname is None:
        fname = "combined_{0}.mp4".format(files[0])
        fname = os.path.join(folder, fname)
        # print(files)
    files = [os.path.join(folder, f.strip()) for f in files]

    if nsec is not None:
        # Sections video and breaks them if the creation time is greater than 500 sec nsec
        dd = np.array([os.path.getctime(f) for f in files])
        ddr = np.roll(dd, -1)
        diff = ddr - dd
        breaks = [i for i, d in enumerate(diff) if d > nsec]
        breaks.append(len(dd))
        print(breaks)
        make_stage_video(fname, files, breaks, encoding)

    else:
        if section is None:
            iret = make_video(files, fname, encoding)
        else:
            nlen = len(files)
            breaks = division_list(nlen, section)
            make_stage_video(fname, files, breaks, encoding)
    return fname


def create_parser(subparser):
    parser = subparser.add_parser(
        "concat",
        description="Concatenate videos with FFmpeg or MoviePy.",
        formatter_class=RawDescriptionHelpFormatter,
        epilog=(
            'Order files may contain a video path per line, or a text row in the '
            'format:\n  videofile,text,"text to add",starttime,duration,position\n'
            "\nText timing is relative to that clip. If the text would extend past "
            "the clip end, its duration is shortened and a warning is shown.\n"
            "\nPositions: top-left, top-right, bottom-left, bottom-right, center, bottom.\n"
            'Example: video.mp4,text,"Hello",0,2,top-right'
        ),
    )
    parser.add_argument(
        "inputfile",
        type=str,
        default=None,
        nargs="?",
        help="Order file: video path per line, or a per-clip text CSV row (see below)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Folder where files are (default: %(default)s)",
        default=None,
    )
    parser.add_argument(
        "-s",
        "--section",
        help="If given sections video by this number (default: %(default)s)",
        default=None,
        type=int,
    )
    parser.add_argument(
        "-n",
        "--nsec",
        help="Section Video by using time `nsec` (default: %(default)s)",
        default=None,
    )
    parser.add_argument(
        "-i",
        "--input",
        help="Input files (default: %(default)s)",
        default=None,
        action="append",
    )
    parser.add_argument(
        "-cd",
        "--change-dir",
        type=str,
        default=None,
        help="if Provided, go to this folder, before anything. (default: %(default)s)",
    )
    parser.add_argument(
        "-e",
        "--encoding",
        action="store_true",
        help="if Provided, Use re-encoding (default: %(default)s)",
    )
    parser.add_argument(
        "-um",
        "--use-moviepy",
        action="store_true",
        help="Use MoviePy for text overlays and final concatenation",
    )

    parser.add_argument(
        "-tag",
        "--tag",
        type=str,
        default="notag",
        help="if Provided, Add this tag in filename (default: %(default)s)",
    )

    parser.add_argument(
        "-sh",
        "--skipheader",
        type=int,
        help="Skip headers in filename (default: %(default)s)",
        default=0,
    )
    parser.add_argument(
        "-sf",
        "--skipfooter",
        type=int,
        help="Skip footer in filename (default: %(default)s)",
        default=0,
    )
    parser.add_argument(
        "-num",
        "--num",
        type=int,
        default=None,
        help="Number of files to read after skipheader (default: %(default)s)",
    )
    return parser


def make_concatfile(inputs, output):
    output_txt = f"{output}.txt"
    with open(output_txt, "w") as fin:
        fin.write("\n".join(inputs))


class ViztoolzPlugin:
    """Concat videos using ffmpeg"""

    __name__ = "concat"

    @vidtoolz.hookimpl
    def register_commands(self, subparser):
        self.parser = create_parser(subparser)
        self.parser.set_defaults(func=self.run)

    def run(self, args):
        if args.input is None and args.inputfile is None:
            self.parser.error("Input or `inputfile` not supplied.")

        if args.change_dir is not None:
            os.chdir(args.change_dir)

        tag = sanitize_string(args.tag)

        if args.inputfile is None:
            inputs = args.input
            output = determine_output_path(inputs[0], args.output, tag)
            make_concatfile(inputs, output)
            entries = None
        else:
            output = determine_output_path(args.inputfile, args.output, tag)
            entries = read_orderfile_entries(
                args.inputfile, skipheader=args.skipheader, skipfooter=args.skipfooter, num=args.num
            )
            inputs = [entry["file"] for entry in entries]

        has_text = entries is not None and any(entry["text"] is not None for entry in entries)

        def make_output(files, encoding):
            if args.use_moviepy:
                return create_concat_movie(files, output, onlyaudio=False)
            return concat(files, output, args.section, args.nsec, encoding)

        if has_text:
            with tempfile.TemporaryDirectory(prefix="vidtoolz-concat-") as tempdir:
                inputs = _render_text_entries(entries, tempdir, args.use_moviepy)
                # Text-rendered clips are re-encoded, so re-encode the final FFmpeg
                # concat to ensure all inputs have matching codecs and parameters.
                fname = make_output(inputs, args.encoding or not args.use_moviepy)
        else:
            fname = make_output(inputs, args.encoding)
        print("{} created".format(fname))

    def hello(self, args):
        # this routine will be called when "vidtoolz "concat is called."
        print("Hello! This is an example ``vidtoolz`` plugin.")


concat_plugin = ViztoolzPlugin()
