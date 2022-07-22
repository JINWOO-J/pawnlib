#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import glob
from termcolor import cprint
import yaml
from pawnlib.output import *
from pawnlib.typing import converter
from pawnlib.config.globalconfig import pawnlib_config as pawn


def check_file_overwrite(filename, answer=None):
    exist_file = False
    if filename and is_file(filename):
        cprint(f"File already exists => {filename}", "green")
        exist_file = True

    if exist_file:
        if answer is None:
            answer = colored_input(f"Overwrite already existing '{filename}' file? (y/n)")
        if answer == "y":
            cprint(f"Remove the existing keystore file => {filename}", "green")
            os.remove(filename)
        else:
            cprint("Stopped", "red")
            sys.exit(127)


def get_file_path(filename):
    dirname, file = os.path.split(filename)
    extension = os.path.splitext(filename)[1]
    fullpath = get_abs_path(filename)
    return {
        "dirname": dirname,
        "file": file,
        "extension": extension,
        "filename": filename,
        "full_path": fullpath
    }


def get_parent_path(run_path=__file__):
    path = os.path.dirname(os.path.abspath(run_path))
    parent_path = os.path.abspath(os.path.join(path, ".."))
    return parent_path


def get_real_path(run_path=__file__):
    path = os.path.dirname(os.path.abspath(run_path))
    return path


def get_abs_path(filename):
    return os.path.abspath(filename)


def is_binary_file(filename) -> bool:
    text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7f})
    fh = open(filename, 'rb').read(100)
    return bool(fh.translate(None, text_chars))


def is_file(filename):
    if "*" in filename:
        if len(glob.glob(filename)) > 0:
            return True
        else:
            return False
    else:
        return os.path.exists(os.path.expanduser(filename))


def is_json(json_file):
    try:
        with open(json_file, 'r', encoding="utf-8-sig") as j:
            json.loads(j.read())
    except ValueError as e:
        return False
    return True


def open_json(filename):
    try:
        with open(filename, "r") as json_file:
            return json.loads(json_file.read())
    except Exception as e:
        pawn.error_logger.error(f"[ERROR] Can't open the json -> '{filename}' / {e}") if pawn.error_logger else False
        raise


def open_file(filename):
    try:
        with open(filename, "r") as file:
            return file.read()
    except Exception as e:
        pawn.error_logger.error(f"[ERROR] Can't open the file -> '{filename}' / {e}") if pawn.error_logger else False
        raise


def open_yaml_file(filename):
    read_yaml = open_file(filename)
    return yaml.load(read_yaml, Loader=yaml.FullLoader)


def write_file(filename, data, option='w', permit='664'):
    with open(filename, option) as outfile:
        outfile.write(data)
    os.chmod(filename, int(permit, base=8))
    if os.path.exists(filename):
        return "Write file -> %s, %s" % (filename, converter.get_size(filename))  # if __main__.args.verbose > 0 else False
    else:
        return "write_file() can not write to file"


def write_json(filename, data, option='w', permit='664'):
    with open(filename, option) as outfile:
        json.dump(data, outfile)
    os.chmod(filename, int(permit, base=8))
    if os.path.exists(filename):
        return "Write json file -> %s, %s" % (filename, converter.get_size(filename))  # if __main__.args.verbose > 0 else False
    else:
        return "write_json() can not write to json"


def write_yaml(filename, data, option='w', permit='664'):
    with open(filename, option) as outfile:
        yaml.dump(data, outfile)
    os.chmod(filename, int(permit, base=8))
    if os.path.exists(filename):
        return "Write json file -> %s, %s" % (filename, converter.get_size(filename))  # if __main__.args.verbose > 0 else False
    else:
        return "write_json() can not write to json"

