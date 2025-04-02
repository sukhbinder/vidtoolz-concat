import vidtoolz
import os
import numpy as np
import tempfile
import moviepy as mpy


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

    # Write out only audio file also
    audio = clip.audio
    aoutput_path = f"{output}-audio.mp3"
    audio = audio.with_fps(44100)
    audio.write_audiofile(aoutput_path)
    print("{} mp3 created".format(aoutput_path))

    # write out video
    if not onlyaudio:
        output_path = output
        if not os.path.exists(output_path):
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


def determine_output_path(input_file, output_file):
    input_dir, input_filename = os.path.split(input_file)
    name, _ = os.path.splitext(input_filename)

    if output_file:
        output_dir, output_filename = os.path.split(output_file)
        if not output_dir:  # If no directory is specified, use input file's directory
            return os.path.join(input_dir, output_filename)
        return output_file
    else:
        return os.path.join(input_dir, f"{name}_concat.mp4")


def make_video(files, fname, encoding=False):
    if os.path.exists(fname):
        os.remove(fname)
    base_name = os.path.basename(fname)
    bname, ext = os.path.splitext(base_name)
    tempdir = tempfile.gettempdir()
    out_file = os.path.join(tempdir, "{}_mylist.txt".format(bname))
    with open(out_file, "w") as fout:
        for f in files:
            if os.path.exists(f):
                fout.write("file '{}'\n".format(f))
    if encoding:
        cmdline = "ffmpeg -f concat -safe 0 -i {0} -c:v libx264 -crf 23 -preset fast -c:a aac -b:a 192k {1}".format(
            out_file, fname
        )
    else:
        cmdline = "ffmpeg -f concat -safe 0 -i {0} -c copy {1}".format(out_file, fname)

    print(cmdline)
    iret = os.system(cmdline)
    print(cmdline)
    return iret


def concat(
    inputfile, fname: str = None, section: bool = False, nsec: int = 500, encoding=False
):
    if isinstance(inputfile, list):
        files = inputfile
        folder = os.path.dirname(inputfile[0])
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
    if not section:
        iret = make_video(files, fname, encoding)
    else:
        # Sections video and breaks them if the creation time is greater than 500 sec nsec
        dd = np.array([os.path.getctime(f) for f in files])
        ddr = np.roll(dd, -1)
        diff = ddr - dd
        breaks = [i for i, d in enumerate(diff) if d > nsec]
        beg = 0
        breaks.append(len(dd))
        print(breaks)
        fileprefix, ext = os.path.splitext(fname)
        for i, b in enumerate(breaks):
            fname = "{0}_{1}_{2}.mp4".format(fileprefix, i, beg)
            iret = make_video(files[beg : b + 1], fname, encoding)
            print("Return code is ", iret)
            beg = b + 1

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
        help="If given sections Video by `nsec` (default: %(default)s)",
        action="store_true",
    )
    parser.add_argument(
        "-n",
        "--nsec",
        help="Section Video by `nsec` (default: %(default)s)",
        default=500,
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
        help="if Provided, go to this folder, before anything.",
    )
    parser.add_argument(
        "-e",
        "--encoding",
        action="store_true",
        help="if Provided, Use re-encoding",
    )
    parser.add_argument(
        "-um",
        "--use-moviepy",
        action="store_true",
        help="if Provided, Use moviepy",
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

        if args.inputfile is None:
            inputs = args.input
            output = determine_output_path(inputs[0], args.output)
            make_concatfile(inputs, output)
        else:
            inputs = args.inputfile
            output = determine_output_path(args.inputfile, args.output)

        if args.use_moviepy:
            fname = create_concat_movie(inputs, output, onlyaudio=False)
        else:
            fname = concat(inputs, output, args.section, args.nsec, args.encoding)
        print("{} created".format(fname))

    def hello(self, args):
        # this routine will be called when "vidtoolz "concat is called."
        print("Hello! This is an example ``vidtoolz`` plugin.")


concat_plugin = ViztoolzPlugin()
