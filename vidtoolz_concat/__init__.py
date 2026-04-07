import os
import re
import tempfile

import imageio_ffmpeg
import moviepy as mpy
import numpy as np
import vidtoolz
from vidtoolz_rnnn import denoise_audio
import shutil
import subprocess


def add_audio_to_video(input_mp4, input_wav, output_mp4=None):
    """
    Merges a WAV audio file into an MP4 video using ffmpeg.

    If output_mp4 is not provided, the input video will be replaced.

    Args:
        input_mp4 (str): Path to input MP4 file
        input_wav (str): Path to input WAV file
        output_mp4 (str, optional): Path to output MP4 file
    """

    if output_mp4 is None:
        # Create a temporary output file
        temp_dir = tempfile.gettempdir()
        output_mp4 = os.path.join(temp_dir, "temp_output.mp4")
        overwrite_input = True
    else:
        overwrite_input = False

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_mp4,
        "-i",
        input_wav,
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-af",
        "aresample=async=1",
        "-shortest",
        "-movflags",
        "+faststart",
        output_mp4,
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg failed: {e}")

    # If no output was specified, replace the original file
    if overwrite_input:
        shutil.move(output_mp4, input_mp4)

    return output_mp4


def sanitize_string(text: str) -> str:
    text = text.replace(" ", "_").strip()
    return re.sub(r"[^A-Za-z0-9._-]", "", text)


def create_concat_movie(inputfile, output, onlyaudio=False, denoise=False):
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
        audio = audio.with_fps(44100)
        audio.write_audiofile(aoutput_path)
        print("{} mp3 created".format(aoutput_path))

    if denoise and audio:
        output_wav = f"{output}-audio.wav"
        denoise_audio(aoutput_path, output_wav, "lq", 0.9)
        print("{} wav created".format(aoutput_path))

    # write out video
    if not onlyaudio:
        output_path = output
        if os.path.exists(output_path):
            os.remove(output_path)

        clip.write_videofile(
            output_path,
            temp_audiofile="out.m4a",
            audio=audio,
            audio_codec="aac",
            codec="libx264",
            fps=60,
        )

        if denoise:
            output_path = add_audio_to_video(output_path, output_wav)
        print("{} mp4 created".format(output_path))

    # Add the denoise wav to teh created video. using this
    # ffmpeg -y -i file_3_test-um_concat.mp4 -i file_3_test-um_concat.mp4-audio.wav -c:v copy -c:a aac -b:a 128k -af aresample=async=1 -shortest -movflags +faststart final_output.mp4
    #

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
    out_file = os.path.join(tempdir, f"{bname}_mylist.txt")

    with open(out_file, "w") as fout:
        for f in files:
            if os.path.exists(f):
                fout.write(f"file '{f}'\n")

    if encoding:
        cmdline = f"""
{ffmpeg} -y -f concat -safe 0 -i {out_file} \
-fflags +genpts \
-vsync vfr \
-c:v libx264 -preset fast -crf 23 \
-pix_fmt yuv420p \
-c:a aac -b:a 128k \
-af aresample=async=1 \
-movflags +faststart \
-fflags +genpts \
-avoid_negative_ts make_zero \
-af aresample=async=1 \
{fname}
"""
    else:
        # SAFE "copy" mode (fixed timestamps)
        cmdline = f"""
{ffmpeg} -y -f concat -safe 0 -i {out_file} \
-fflags +genpts \
-avoid_negative_ts make_zero \
-c copy \
{fname}
"""

    print(cmdline)
    return os.system(cmdline)


def make_video_old(files, fname, encoding=False):
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
    parser = subparser.add_parser("concat", description="Concat videos using ffmpeg ")
    parser.add_argument(
        "inputfile",
        type=str,
        default=None,
        nargs="?",
        help="Text file having names of files to concat",
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
        help="if Provided, Use moviepy (default: %(default)s)",
    )
    parser.add_argument(
        "-nd",
        "--no-denoise",
        action="store_true",
        help="if Provided, Do not denoise when using moviepy (default: %(default)s)",
    )

    parser.add_argument(
        "-tag",
        "--tag",
        type=str,
        default="notag",
        help="if Provided, Add this tag in filename (default: %(default)s)",
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
        else:
            inputs = args.inputfile
            output = determine_output_path(args.inputfile, args.output, tag)

        if args.use_moviepy:
            fname = create_concat_movie(
                inputs, output, onlyaudio=False, denoise=not args.no_denoise
            )
        else:
            fname = concat(inputs, output, args.section, args.nsec, args.encoding)
        print("{} created".format(fname))

    def hello(self, args):
        # this routine will be called when "vidtoolz "concat is called."
        print("Hello! This is an example ``vidtoolz`` plugin.")


concat_plugin = ViztoolzPlugin()
