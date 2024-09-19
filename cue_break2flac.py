#!/bin/python3

import subprocess
from sys import argv
from pathlib import Path
import re


ENCODER_PARAMETERS = {
    "file": '-i "{}"',
    "genre": '-metadata genre="{}"',
    "year": '-metadata date="{}"',
    "discid": '-metadata comment="DiscID: {}"',
    "performer": '-metadata artist="{}"',
    "album": '-metadata album="{}"',
    "title": '-metadata title="{}"',
    "tracknumber": '-metadata track="{}"',
    "start": '-ss {}',
    "stop": '-to {}'
}

PRIMARY_COMMAND_LINE = {
    "FLAC": ("ffmpeg", "-c:a flac -compression_level 12", ".flac"),
    "MP3": ("ffmpeg", "-c:a libmp3lame -qscale:a 1", ".mp3")
}

# in case flac instead of ffmpeg:
# ENCODER_PARAMETERS = {
#     "file": '"{}"',
#     "genre": '--tag=genre="{}"',
#     "year": '--tag=date="{}"',
#     "discid": '--tag=comment="DiscID: {}"',
#     "performer": '--tag=artist="{}"',
#     "album": '--tag=album="{}"',
#     "title": '--tag=title="{}"',
#     "start": '--skip={}',
#     "stop": '--until={}',
#     "tracknumber": '--tag=tracknumber="{}"'
# }

# PRIMARY_COMMAND_LINE = {
#     "FLAC": ("flac -8 -V", "-o", ".flac")
# }

TAGS_REGEXS = {
    "GENERAL": {
        "genre": r"(?<=REM GENRE ).+",
        "year": r"(?<=REM DATE ).+",
        "performer": r"(?<=PERFORMER \").+(?=\")",
        "discid": r"(?<=REM DISCID ).+",
        "album": r"(?<=TITLE \").+(?=\")"
    },
    "TRACK": {
        "performer": r"(?<=PERFORMER \").+(?=\")",
        "title": r"(?<=TITLE \").+(?=\")",
        "start": r"(?<=INDEX 01 ).+"
    }
}


def usage():
    print("Run this script as:")
    print(f"{argv[0]} [FLAC | MP3] <filenme>.cue")
    exit(1)


def file_error(file):
    print(f"{argv[0]}: cannot access '{file}': No such file")
    exit(1)


def cue_error():
    print(f"{argv[0]}: cannot parse '{argv[1]}': The file may be in an incompatible format, damaged or corrupted")
    exit(1)


def dir_error(dir):
    print(f"{argv[0]}: cannot create directory '{dir}'")
    exit(1)


def interruption():
    print("Script is interrupted")
    exit(1)


def normalize_time(time):
    return re.sub(r"(?<=\d{2}:\d{2}):", ".", time)


def parse_cue(cue):

    general_tags = {
        "genre": None,
        "year": None,
        "discid": None,
        "performer": None,
        "album": None,
        "title": None,
        "file": None,
        "start": None,
        "stop": None,
        "tracknumber": None
    }

    tracks_tags = {}

    file = re.findall(r"(?<=FILE \").+(?=\")", cue)
    if len(file) != 1: cue_error()

    if not Path(file[0]).is_file():
        file_error(file[0])

    general_tags["file"] = file[0]

    first_part_cue = re.match(r".*(?=FILE)", cue, re.DOTALL | re.IGNORECASE).group()
        
    for tag, regex in TAGS_REGEXS["GENERAL"].items():
        search_tag = re.search(regex, first_part_cue, re.IGNORECASE)
        if search_tag is not None:
            general_tags[tag] = search_tag.group()
    
    tracks = re.findall(r"(?<=TRACK ).+(?= AUDIO)", cue, re.IGNORECASE)
    if len(tracks) == 0: cue_error()

    prev_track_regex = ""
    prev_track_start = None

    for track in reversed(tracks):

        current_track_tags = general_tags.copy()

        track_part_cue = re.search(f"(?<=TRACK {track} AUDIO).+{prev_track_regex}", cue, re.DOTALL | re.IGNORECASE).group()

        for tag, regex in TAGS_REGEXS["TRACK"].items():
            search_tag = re.search(regex, track_part_cue, re.IGNORECASE)
            if search_tag is not None:
                current_track_tags[tag] = search_tag.group()
        
        current_track_tags["start"] = normalize_time(current_track_tags["start"])

        current_track_tags["tracknumber"] = track
        current_track_tags["stop"] = prev_track_start
        
        prev_track_regex = f"(?=TRACK {track} AUDIO)"
        prev_track_start = current_track_tags["start"]
        tracks_tags.update({track: current_track_tags})

    return tracks_tags


def check_dir(dir):
    dir_path = Path(dir)
    dir_path.mkdir() if not dir_path.exists() else dir_error(dir)


def encode(tracks_tags, format = "FLAC"):
    key = list(tracks_tags.keys())[-1]
    album = tracks_tags[key]["album"]
    year = tracks_tags[key]["year"]
      
    if (album is None) or (year is None):
        folder = None
    else:
        folder = f"{year} - {album}"
        check_dir(folder)

    for key, tags in reversed(tracks_tags.items()):
        command_line = PRIMARY_COMMAND_LINE[format][0]
        for param_key, param in ENCODER_PARAMETERS.items():
            if tags[param_key] is not None:
                command_line += " " + param.format(tags[param_key])
        
        command_line += f" {PRIMARY_COMMAND_LINE[format][1]}"
        command_line += f' "{folder}/' if folder is not None else ' "'
        command_line += f"{key} - "
        command_line += tags["title"] if tags["title"] is not None else "Track"
        command_line += f'{PRIMARY_COMMAND_LINE[format][2]}"'
        
        try:
            subprocess.run(command_line, shell=True)
        except KeyboardInterrupt:
            interruption()


def main():
    if 2 > len(argv) < 4:
        usage()
    
    format = "FLAC" if len(argv) == 2 else argv[1]
    if format not in ["FLAC", "MP3"]:
        usage()

    path = argv[1] if len(argv) == 2 else argv[2]
    path = Path(path)
    if not path.is_file():
        file_error(path.name)
    
    with open(path) as fn:
        try:
            cue = fn.read()
        except:
            cue_error()

    if not cue: cue_error()

    tracks_tags = parse_cue(cue)

    encode(tracks_tags, format)


if __name__ == "__main__":
    main()
