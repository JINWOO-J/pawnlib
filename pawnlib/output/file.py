#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import glob
import yaml
import time
import re
from typing import Union, Any, List, Callable
from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.output import color_print
from pawnlib.typing import converter
from rich.prompt import Confirm
import asyncio
import aiofiles
import logging

from pawnlib.config.logging_config import setup_logger


class NullByteRemover:
    def __init__(self, file_paths, chunk_size=1024 * 1024, replace_with=None):
        """
        A class to remove null bytes from files.

        :param file_paths: List of file paths or a single file path.
        :param chunk_size: Size of the chunks to read from the file (default is 1 MB).
        :param replace_with: Bytes to replace null bytes with (default is empty bytes).

        Example:

            .. code-block:: python

                remover = NullByteRemover(["file1.txt", "file2.txt"])
                remover.remove_null_bytes()

                remover = NullByteRemover("single_file.txt", replace_with=b' ')
                remover.remove_null_bytes()

        """
        self.file_paths = file_paths if isinstance(file_paths, list) else [file_paths]
        self.chunk_size = chunk_size
        self.replace_with = replace_with if replace_with is not None else b''
        self.report = []

    def run(self):
        self.remove_null_bytes()
        self.print_report()

    def check_null_bytes(self, file_path):
        """
        Check if the file contains null bytes.

        :param file_path: Path to the file to check.
        :return: True if null bytes are found, otherwise False.

        Example:

            .. code-block:: python

                has_null_bytes = remover.check_null_bytes("file1.txt")
                print(has_null_bytes)  # >> True or False

        """
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                if b'\x00' in chunk:
                    return True
        return False

    def remove_null_bytes(self):
        """
        Remove null bytes from the specified files and create new files without null bytes.

        Example:

            .. code-block:: python

                remover.remove_null_bytes()

        """
        for file_path in self.file_paths:
            # Check for null bytes
            if not self.check_null_bytes(file_path):
                print(f"No null bytes found: {file_path} - Skipping processing.")
                continue

            start_time = time.time()  # Record start time
            original_size = os.path.getsize(file_path)
            new_file_path = f"{file_path}_recovered"
            null_byte_count = 0
            total_bytes_processed = 0

            with open(file_path, 'rb') as f_in, open(new_file_path, 'wb') as f_out:
                while True:
                    data = f_in.read(self.chunk_size)
                    if not data:
                        break
                    clean_data = data.replace(b'\x00', self.replace_with)
                    null_byte_count += data.count(b'\x00')
                    f_out.write(clean_data)
                    total_bytes_processed += len(data)
                    self._show_progress(total_bytes_processed, original_size, file_path)

            # Report details after processing
            self.report.append({
                'File Name': file_path,
                'Original Size': original_size,
                'Recovered Size': os.path.getsize(new_file_path),
                'Null Byte Count': null_byte_count,
                'Execution Time': time.time() - start_time
            })

    @staticmethod
    def _show_progress(processed, total, file_path):
        """
        Display the progress of file processing.

        :param processed: Number of bytes processed so far.
        :param total: Total number of bytes in the original file.
        :param file_path: Path to the current file being processed.
        """
        percent = processed / total * 100
        sys.stdout.write(f"\r{file_path}: {percent:.2f}% completed ({processed}/{total} bytes)")
        sys.stdout.flush()
        if processed >= total:
            print()  # New line after completion

    def print_report(self):
        """
        Print a detailed report of the processing results after completion.

        This includes information about each processed file such as size and null byte count.
        """
        for file_report in self.report:
            print(f"File Name: {file_report['File Name']}")
            print(f"Original Size: {file_report['Original Size']} bytes")
            print(f"Recovered Size: {file_report['Recovered Size']} bytes")
            print(f"Null Byte Count: {file_report['Null Byte Count']} occurrences")
            print(f"Execution Time: {file_report['Execution Time']:.2f} seconds")
            print("-" * 40)


class Tail:
    """
    Tail class for monitoring log files with support for both synchronous and asynchronous modes.

    :param log_file_paths: Paths to the log files to monitor.
    :type log_file_paths: Union[str, List[str]]
    :param filters: List of regex patterns to filter log lines.
    :type filters: List[str]
    :param callback: Function to call with processed log lines.
    :type callback: Callable[[str], Union[None, asyncio.coroutine]]
    :param async_mode: Whether to operate in asynchronous mode.
    :type async_mode: bool
    :param formatter: Function to format log lines before processing.
    :type formatter: Callable[[str], str]

    Example:

        .. code-block:: python

            from pawnlib.output.file import Tail

            # Synchronous mode
            tail = Tail(log_file_paths=["/var/log/app.log"],
                         filters=["ERROR", "CRITICAL"],
                         callback=process_log_line,
                         async_mode=False)

            tail.follow()

            # Asynchronous mode
            async def process_log_line_async(line: str):
                # Your async callback logic
                pass

            tail = Tail(log_file_paths=["/var/log/app.log"],
                         filters=["ERROR", "WARNING"],
                         callback=process_log_line_async,
                         async_mode=True)

            tail.follow()

    """

    def __init__(self,
                 log_file_paths: Union[str, List[str]],
                 filters: List[str],
                 callback: Callable[[str], Any],
                 async_mode: bool = False,
                 formatter: Callable[[str], str] = None,
                 enable_logging: bool = True,
                 logger=None,
                 verbose: int = 0,
                 ):

        self.log_file_paths = [log_file_paths] if isinstance(log_file_paths, str) else log_file_paths
        self.filters = [re.compile(f) for f in filters]
        self.callback = callback
        self.async_mode = async_mode
        self.formatter = formatter
        self.verbose = verbose
        # if enable_logging:
        #     logging.basicConfig(level=logging.INFO)
        # else:
        #     logging.basicConfig(level=logging.CRITICAL)  # Silence all logs
        # from pawnlib.utils.log import ConsoleLoggerAdapter

        self.logger = setup_logger(logger, "Tail", self.verbose)
        self.file_inodes = {}
        # self.logger.info("Start Info")
        self.max_retries = 5

    def _get_inode(self, file_path):
        """Get the inode of the file."""
        return os.stat(file_path).st_ino

    async def _handle_retry(self, file_path, retry_count):
        """
        Handle the retry logic with backoff for when the file is not found.
        :param file_path: The path to the log file.
        :param retry_count: The number of retry attempts.
        """
        retry_count += 1
        backoff_time = min(2 ** retry_count, 60)  # Exponential backoff with a max of 60 seconds
        self.logger.warning(f"File '{file_path}' not found. Retrying in {backoff_time} seconds. Retry count: {retry_count}")
        await asyncio.sleep(backoff_time)
        return retry_count

    async def _follow_async(self, file_path: str):
        retry_count = 0
        self.logger.info(f"Starting async follow on {file_path}")

        while retry_count <= self.max_retries:
            try:
                # Check if the file exists
                # if not os.path.exists(file_path):
                #     self.logger.warning(f"Log file {file_path} not found. Waiting for it to be created... ")
                #     retry_count += 1
                #     backoff_time = min(2 ** retry_count, 60)  # Exponential backoff with a max of 60 seconds
                #     self.logger.warning(f"---- backoff_time -> {backoff_time}")
                #     await asyncio.sleep(backoff_time)
                #     continue
                if not os.path.exists(file_path):
                    retry_count = await self._handle_retry(file_path, retry_count)
                    continue

                async with aiofiles.open(file_path, mode='r') as file:
                    # Move to the end of the file
                    await file.seek(0, os.SEEK_END)
                    self.file_inodes[file_path] = self._get_inode(file_path)
                    self.logger.debug(f"Started async monitoring on file: {file_path}")

                    while True:
                        # Check for file rotation by comparing inode numbers
                        current_inode = self._get_inode(file_path)
                        if self.file_inodes[file_path] != current_inode:
                            self.file_inodes[file_path] = current_inode
                            self.logger.info(f"Log file {file_path} rotated. Reopening new file.")
                            break  # Exit loop to reopen the new file

                        # Read new lines
                        line = await file.readline()
                        if not line:
                            await asyncio.sleep(0.1)
                            continue

                        # Process each line
                        await self._process_line(line, file_path)

                    retry_count = 0  # Reset retry count after successful file access

            except FileNotFoundError:
                retry_count = await self._handle_retry(file_path, retry_count)
            except Exception as e:
                self.logger.error(f"Error occurred while asynchronously monitoring file {file_path}: {e}")
                break


    def _follow_sync(self, file_path: str):
        while True:
            try:
                if not os.path.exists(file_path):
                    self.logger.warning(f"Log file {file_path} not found. Waiting for it to be created...")
                    time.sleep(1)  # Wait for the file to be recreated
                    continue

                with open(file_path, "r") as file:
                    file.seek(0, os.SEEK_END)
                    self.file_inodes[file_path] = self._get_inode(file_path)
                    self.logger.debug(f"Started synchronous monitoring on file: {file_path}")

                    while True:
                        current_inode = self._get_inode(file_path)
                        if self.file_inodes[file_path] != current_inode:
                            self.file_inodes[file_path] = current_inode
                            self.logger.info(f"Log file {file_path} rotated. Reopening new file.")
                            break  # Exit the loop to reopen the file

                        line = file.readline()
                        if not line:
                            time.sleep(0.1)
                            continue

                        self._process_line_sync(line, file_path)

            except FileNotFoundError:
                self.logger.error(f"Error monitoring file {file_path}: File not found. Retrying...")
                time.sleep(1)  # Retry after a delay if the file is not found
            except Exception as e:
                self.logger.error(f"Error occurred while synchronously monitoring file {file_path}: {e}")
                break

    async def _process_line(self, line: str, file_path: str):
        line = line.strip()
        if self._should_process(line):
            try:
                formatted_line = self.formatter(line) if self.formatter else line
                result = self.callback(formatted_line)

                if asyncio.iscoroutine(result):  # Check if the result is awaitable
                    result = await result  # Await only if it is a coroutine
                    if isinstance(result, bool):  # Handle if the awaited result is a boolean
                        if not result:
                            self.logger.warning(f"Callback returned False after awaiting for line from {file_path}: {formatted_line}")
                elif isinstance(result, bool):  # Handle non-awaitable boolean values
                    if not result:
                        self.logger.warning(f"Callback returned False for line from {file_path}: {formatted_line}")
                else:
                    self.logger.debug(f"Callback returned non-awaitable value for line from {file_path}: {result}")

                self.logger.debug(f"Successfully processed a log line from {file_path}: {formatted_line}")
            except Exception as e:
                self.logger.error(f"Error occurred while executing callback on line from {file_path}: {e}")

    def _process_line_sync(self, line: str, file_path: str):
        line = line.strip()
        if self._should_process(line):
            try:
                formatted_line = self.formatter(line) if self.formatter else line
                self.callback(formatted_line)
                self.logger.debug(f"Successfully processed a log line from {file_path}: {formatted_line}")
            except Exception as e:
                self.logger.error(f"Error occurred while executing callback on line from {file_path}: {e}")

    def _should_process(self, line: str) -> bool:
        return any(f.search(line) for f in self.filters)

    async def follow_async(self):
        """ Asynchronous follow method """
        tasks = [self._follow_async(path) for path in self.log_file_paths]
        await asyncio.gather(*tasks)

    def follow(self):
        """ Unified follow method for both async and sync """
        if self.async_mode:
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    # Use an already running loop
                    return asyncio.ensure_future(self.follow_async())
                else:
                    # If no loop is running, start it manually
                    loop.run_until_complete(self.follow_async())
            except RuntimeError:
                # Handle if no loop is running (as in the case with `asyncio.run()`)
                asyncio.run(self.follow_async())
        else:
            # Synchronous mode: directly call the sync methods
            for path in self.log_file_paths:
                self._follow_sync(path)


def check_path(path, detailed=False):
    """
    Check if the provided path is a file, a directory, or neither.
    Optionally return extended details about the path.

    :param path: The path to check.
    :type path: str
    :param detailed: If True, returns a dictionary with additional information about the path.
                     If False, returns only the type as a string.
    :type detailed: bool
    :return: If detailed=True, returns a dictionary with path type, existence, readability, and writability.
             If detailed=False, returns only the type of the path as a string ('file', 'directory', or 'neither').
    :rtype: dict | str

    Example usage:

        >>> check_path("/path/to/file.txt")
        'file'

        >>> check_path("/path/to/file.txt", detailed=True)
        {'type': 'file', 'exists': True, 'readable': True, 'writable': False}

        >>> check_path("/path/to/directory")
        'directory'

        >>> check_path("/path/to/directory", detailed=True)
        {'type': 'directory', 'exists': True, 'readable': True, 'writable': True}

        >>> check_path("/path/to/unknown")
        None

        >>> check_path("/path/to/unknown", detailed=True)
        {'type': None, 'exists': False, 'readable': False, 'writable': False}

    Notes:
        - `detailed=False` by default, returning only the type of the path as a string.
        - If `detailed=True`, additional details (existence, readability, writability) are provided in a dictionary.
    """
    path_info = {
        "type": None,
        "exists": os.path.exists(path),
        "readable": os.access(path, os.R_OK),
        "writable": os.access(path, os.W_OK),
    }

    if path_info["exists"]:
        if os.path.isfile(path):
            path_info["type"] = "file"
        elif os.path.isdir(path):
            path_info["type"] = "directory"

    return path_info if detailed else path_info["type"]


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


# def get_script_path(run_path=__file__):
#     """
#     Returns the script path.

#     :param run_path: (str) Path of the file to get the script path of.
#     :return: (str) Script path of the given file path.

#     Example:

#         .. code-block:: python

#             get_script_path(__file__)
#             # >> '/path/to/script/directory'
#     """
#     return os.path.dirname(run_path)


def get_script_path(run_path=None):
    """
    Returns the script directory.

    :param run_path: (str) Path of the file to get the script directory of.
    :return: (str) Script directory of the given file path.

    Example:

        .. code-block:: python

            get_script_dir(__file__)
            # >> '/path/to/script/directory'

            get_script_dir()
            # >> '/path/to/script/directory'

    """
    
    if run_path:
        return os.path.dirname(run_path)

    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))    
    if sys.argv[0]:
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    
    return os.getcwd()


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
    if not filename:
        return False

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


def is_json_file(json_file: str) -> bool:
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


def open_json(filename: str, encoding="utf-8-sig"):
    """
    Read the JSON file.

    :param filename: str, the name of the JSON file to be read.
    :param encoding: str, the encoding to use when opening the file.
    :return: dict, the contents of the JSON file as a dictionary.

    Example:

        .. code-block:: python

            json_data = open_json("data.json")
            # >> {'name': 'John', 'age': 30, 'city': 'New York'}
    """
    try:
        with open(filename, "r", encoding=encoding) as json_file:
            return json.loads(json_file.read())
    except Exception as e:
        pawn.error_logger.error(f"[ERROR] Can't open the json -> '{filename}' / {e}") if pawn.error_logger else False
        raise ValueError(f"Error: Failed to parse JSON  in file . <'{filename}'>\n{e}")


def open_file(filename: str, encoding=None):
    """
    Read the file.

    :param filename: str, the name of the file to be read.
    :param encoding: str, the encoding to use when opening the file.
    :return: str, the contents of the file as a string.

    Example:

        .. code-block:: python

            file_contents = open_file("example.txt")
            # >> 'This is an example file.\\nIt contains some text.\\n'
    """
    try:
        with open(filename, "r", encoding=encoding) as file_handler:
            return file_handler.read()
    except Exception as e:
        pawn.error_logger.error(f"[ERROR] Can't open the file -> '{filename}' / {e}") if pawn.error_logger else False
        raise ValueError(f"Error: An error occurred while reading the file. <'{filename}'>\n{e}")


def open_yaml_file(filename: str, encoding=None):
    """
    Read the YAML file.

    :param filename: str, the name of the YAML file to be read.
    :param encoding: str, the encoding to use when opening the file.
    :return: dict, the contents of the YAML file as a dictionary.

    Example:

        .. code-block:: python

            yaml_data = open_yaml_file("data.yaml")
            # >> {'name': 'John', 'age': 30, 'city': 'New York'}
    """
    try:
        with open(filename, 'r', encoding=encoding) as file:
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

            # >> "key1: value1\\nkey2: value2\\n"

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


