#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import glob
import yaml
from typing import Union, Any
from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.output import color_print
from pawnlib.typing import converter
from rich.prompt import Confirm


def check_file_overwrite(filename, answer=None) -> bool:
    """
    Checks the existence of a file.

    :param filename:
    :param answer:
    :return:

    Example:

        .. code-block:: python

            # touch sdsd

            from pawnlib.output import file
            file.check_file_overwrite(filename="sdsd")
            # >>   File already exists => sdsd
            # >>  Overwrite already existing 'sdsd' file? (y/n)


    """
    if not filename:
        return False

    if is_file(filename):
        color_print.cprint(f"File already exists => {filename}", "green")
        if answer is None:
            answer = Confirm.ask(prompt=f"Overwrite already existing '{filename}' file?", default=False)

        if answer:
            color_print.cprint(f"Removing the existing file => {filename}", "green")
            os.remove(filename)
        else:
            color_print.cprint("Operation stopped.", "red")
            sys.exit(1)
    return True


def get_file_path(filename) -> dict:
    """

     This function is intended to return the file information

    :param filename:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.output import file
            file.get_file_path("sample_file.txt")

            # >>
               {
                  dirname:
                  file: sample_file.txt
                  extension: txt
                  filename: sample_file.txt
                  full_path: /examples/sample_file.txt
               }



    """
    _dirname, _file = os.path.split(filename)
    _extension = os.path.splitext(filename)[1]
    _fullpath = get_abs_path(filename)
    return {
        "dirname": _dirname,
        "file": _file,
        "extension": _extension,
        "filename": filename,
        "full_path": _fullpath
    }


def get_file_extension(file_path):
    """
    Get the file extension from a file path.

    :param file_path: The path of the file.
    :return: The extension of the file.

    Example:

        .. code-block:: python

            utils.get_file_extension("/home/user/document.txt")
            # >> 'txt'

            utils.get_file_extension("/home/user/.hiddenfile")
            # >> ''

            utils.get_file_extension("/home/user/.hiddenfile.txt")
            # >> 'txt'
    """
    _, file_extension = os.path.splitext(file_path)
    return file_extension[1:]  # Remove the leading "."


def get_file_list(path="./", pattern="*", recursive=False):
    """
    Get the list of files in the specified directory that match the given pattern.

    :param path: The path of the directory to search. Default is current directory.
    :param pattern: The pattern to match. Default is "*", which matches all files.
    :param recursive: Whether to search subdirectories recursively. Default is False.

    :return: A list of file paths that match the pattern.

    Example:

        .. code-block:: python

            get_file_list(directory_path="./", pattern="*.py", recursive=True)
            # >> ['./main.py', './utils/helper.py']

            get_file_list(directory_path="./", pattern="*.txt", recursive=False)
            # >> ['./README.txt']

    """
    try:
        if recursive:
            search_pattern = os.path.join(path, '**', pattern)
        else:
            search_pattern = os.path.join(path, pattern)
        files = glob.glob(search_pattern, recursive=recursive)
        return files

    except OSError:
        print("Error reading directory '{}'.".format(path))
        return None


def get_parent_path(run_path=__file__) -> str:
    """
    Returns the parent path

    :param run_path: (str) Path of the file to get the parent path of.
    :return: (str) Parent path of the given file path.

    Example:

        .. code-block:: python

            get_parent_path(__file__)
            # >> '/path/to/parent/directory'
    """
    path = os.path.dirname(os.path.abspath(run_path))
    parent_path = os.path.abspath(os.path.join(path, ".."))
    return parent_path


def get_script_path(run_path=__file__):
    """
    Returns the script path.

    :param run_path: (str) Path of the file to get the script path of.
    :return: (str) Script path of the given file path.

    Example:

        .. code-block:: python

            get_script_path(__file__)
            # >> '/path/to/script/directory'
    """
    return os.path.dirname(run_path)


def get_real_path(run_path=__file__):
    """
    Returns the real path.

    :param run_path: (str) Path of the file to get the real path of.
    :return: (str) Real path of the given file path.

    Example:

        .. code-block:: python

            get_real_path(__file__)
            # >> '/path/to/real/directory'
    """
    path = os.path.dirname(get_abs_path(run_path))
    return path


def get_abs_path(filename) -> str:
    """
    Returns the absolute path.

    :param filename: (str) Name of the file to get the absolute path of.
    :return: (str) Absolute path of the given file name.

    Example:

        .. code-block:: python

            get_abs_path('example.txt')
            # >> '/path/to/example.txt'
    """
    return os.path.abspath(filename)


def is_binary_file(filename) -> bool:
    """
    Check if the file is binary.

    :param filename: (str) Name of the file to check.
    :return: (bool) True if the file is binary, False otherwise.

    Example:

        .. code-block:: python

            is_binary_file('example.txt')
            # >> False
    """
    text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7f})
    fh = open(filename, 'rb').read(100)
    return bool(fh.translate(None, text_chars))


def is_file(filename: str) -> bool:
    """
    Check if the file exists.

    :param filename: (str) Name of the file to check.
    :return: (bool) True if the file exists, False otherwise.

    Example:

        .. code-block:: python

            is_file('example.txt')
            # >> True
    """

    if "*" in filename:
        if len(glob.glob(filename)) > 0:
            return True
        else:
            return False
    else:
        return os.path.exists(os.path.expanduser(filename))


def is_directory(path):
    """
    Check if the given path is a directory.

    :param path: The path to check.
    :return: True if the path is a directory, False otherwise.

    Example:

        .. code-block:: python

            check.is_directory("/home/user")
            # >> True

            check.is_directory("/home/user/myfile.txt")
            # >> False

    """
    return os.path.isdir(path)


def is_json(json_file: str) -> bool:
    """
    Validate the JSON.

    :param json_file: (str) Name of the JSON file to validate.
    :return: (bool) True if the JSON is valid, False otherwise.

    Example:

        .. code-block:: python

            is_json('example.json')
            # >> True
    """
    try:
        with open(json_file, 'r', encoding="utf-8-sig") as j:
            json.loads(j.read())
    except ValueError:
        return False
    return True


def open_json(filename: str):
    """
    Read the JSON file.

    :param filename: str, the name of the JSON file to be read.
    :return: dict, the contents of the JSON file as a dictionary.

    Example:

        .. code-block:: python

            json_data = open_json("data.json")
            # >> {'name': 'John', 'age': 30, 'city': 'New York'}
    """
    try:
        with open(filename, "r") as json_file:
            return json.loads(json_file.read())
    except Exception as e:
        pawn.error_logger.error(f"[ERROR] Can't open the json -> '{filename}' / {e}") if pawn.error_logger else False
        raise ValueError(f"Error: Failed to parse JSON  in file . <'{filename}'>\n{e}")


def open_file(filename: str):
    """
    Read the file.

    :param filename: str, the name of the file to be read.
    :return: str, the contents of the file as a string.

    Example:

        .. code-block:: python

            file_contents = open_file("example.txt")
            # >> 'This is an example file.\nIt contains some text.\n'
    """
    try:
        with open(filename, "r") as file_handler:
            return file_handler.read()
    except Exception as e:
        pawn.error_logger.error(f"[ERROR] Can't open the file -> '{filename}' / {e}") if pawn.error_logger else False
        raise ValueError(f"Error: An error occurred while reading the file. <'{filename}'>\n{e}")


def open_yaml_file(filename: str):
    """
    Read the YAML file.

    :param filename: str, the name of the YAML file to be read.
    :return: dict, the contents of the YAML file as a dictionary.

    Example:

        .. code-block:: python

            yaml_data = open_yaml_file("data.yaml")
            # >> {'name': 'John', 'age': 30, 'city': 'New York'}
    """
    try:
        with open(filename, 'r') as file:
            yaml_data = yaml.load(file, Loader=yaml.FullLoader)
            return yaml_data
    except FileNotFoundError:
        raise FileNotFoundError(f"Error: The file '{filename}' was not found.")
    except yaml.YAMLError as e:
        raise ValueError(f"Error: Failed to parse YAML in file '{filename}'. {e}")


def write_file(filename: str, data: Any, option: str = 'w', permit: str = '664'):
    """
    Write data to a file.

    :param filename: The name of the file to write.
    :param data: The data to write to the file.
    :param option: The write mode. Default is 'w'.
    :param permit: The permission of the file. Default is '664'.

    Example:
        .. code-block:: python

            write_file('test.txt', 'Hello, World!')
            # >> 'Write file -> test.txt, 13'

    :return: A string indicating the success or failure of the write operation.
    """

    with open(filename, option) as outfile:
        outfile.write(data)
    os.chmod(filename, int(permit, base=8))
    if os.path.exists(filename):
        return "Write file -> %s, %s" % (filename, converter.get_size(filename))
    else:
        return "write_file() can not write to file"


def write_json(filename: str, data: Union[dict, list], option: str = 'w', permit: str = '664', force_write: bool = True, json_default=None):
    """
    Write JSON data to a file.

    :param filename: The name of the file to write.
    :param data: The JSON data to write to the file.
    :param option: The write mode. Default is 'w'.
    :param permit: The permission of the file. Default is '664'.
    :param force_write: Whether to force the write operation. Default is True.
    :param json_default: A function to convert non-serializable objects to a serializable format. Default is None.

    Example:
        .. code-block:: python

            data = {'name': 'John', 'age': 30}
            write_json('test.json', data)
            # >> 'Write json file -> test.json, 23'

    :return: A string indicating the success or failure of the write operation.
    """

    def _json_default(obj):
        if hasattr(obj, 'to_json'):
            return obj.to_json()
        else:
            return str(obj)

    if not force_write:
        _json_default = None

    if json_default:
        _json_default = json_default

    with open(filename, option) as outfile:
        json.dump(data, outfile, default=_json_default)

    os.chmod(filename, int(permit, base=8))
    if os.path.exists(filename):
        return "Write json file -> %s, %s" % (filename, converter.get_size(filename))
    else:
        return "write_json() can not write to json"


def represent_ordereddict(dumper, data):
    """
    Represents an OrderedDict for YAML.

    :param dumper: A YAML dumper instance.
    :param data: An OrderedDict instance.

    Example:

        .. code-block:: python

            import yaml
            from collections import OrderedDict

            data = OrderedDict()
            data['key1'] = 'value1'
            data['key2'] = 'value2'

            yaml.add_representer(OrderedDict, represent_ordereddict)
            print(yaml.dump(data))

            # >> "key1: value1\nkey2: value2\n"

    """
    value = []
    node = yaml.nodes.MappingNode("tag:yaml.org,2002:map", value)
    for key, val in data.items():
        node_key = dumper.represent_data(key)
        node_val = dumper.represent_data(val)
        value.append((node_key, node_val))
    return node


def write_yaml(filename: str, data: Union[dict, list], option: str = 'w', permit: str = '664'):
    """
    Write YAML data to a file.

    :param filename: The name of the file to write.
    :param data: The YAML data to write to the file.
    :param option: The write mode. Default is 'w'.
    :param permit: The permission of the file. Default is '664'.

    Example:
        .. code-block:: python

            data = {'name': 'John', 'age': 30}
            write_yaml('test.yaml', data)
            # >> 'Write json file -> test.yaml, 23'

    :return: A string indicating the success or failure of the write operation.
    """
    yaml.add_representer(dict, represent_ordereddict)

    with open(filename, option) as outfile:
        yaml.dump(data, outfile)
    os.chmod(filename, int(permit, base=8))
    if os.path.exists(filename):
        return "Write json file -> %s, %s" % (filename, converter.get_size(filename))
    else:
        return "write_json() can not write to json"


