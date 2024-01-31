import inspect
import multiprocessing
import os
import sys
import json
# import sqlite3


class FirstRunCheckerSqlite:

    _instance = None
    _lock = multiprocessing.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_file=".task_first_run.db", debug=False):
        if hasattr(self, "initialized"):
            return
        self.initialized = True

        self.db_file = db_file
        self.key = "default"
        self.debug = debug
        self.setup_database()
        # self.debug_print("Initialized")

    def setup_database(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS first_run_flags (key TEXT PRIMARY KEY, flag INTEGER)')
        conn.commit()
        conn.close()

    def is_first_run(self, key=None):
        if key:
            self.key = key
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT flag FROM first_run_flags WHERE key=?', (self.key,))
        result = cursor.fetchone()
        conn.close()
        return not result or not bool(result[0])

    def one_time_run(self, key=None):
        if key:
            self.key = key
        else:
            caller_frame = inspect.currentframe().f_back
            caller_module = inspect.getmodule(caller_frame)
            key = f"{caller_module.__name__}.{caller_frame.f_code.co_name}"  # Add module name to the key
            self.key = key

        with self._lock:
            _is_first_run_result = self.is_first_run(self.key)
            if _is_first_run_result:
                self.mark_first_run(self.key)
                return True
            return False

    def mark_first_run(self, key=None):
        if key:
            self.key = key
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO first_run_flags (key, flag) VALUES (?, 1)', (self.key,))
        conn.commit()
        conn.close()

    def clear_first_run(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM first_run_flags')
        conn.commit()
        conn.close()


class FirstRunChecker:
    """
    A class to check if it's the first run of the program.

    This class uses a file to keep track of whether it's the first run of the program or not.
    The file path can be specified, and by default, it's ".task_first_run.json".

    :param file_path: The file path to keep track of the first run. Default is ".task_first_run.json".
    :param debug: A flag to print debug information. Default is False.

    Example:

        .. code-block:: python

            from pawnlib.config import FirstRunChecker, one_time_run
            checker = FirstRunChecker(file_path=".first_run.json", debug=True)
            if checker.is_first_run():
                print("This is the first run.")
            else:
                print("This is not the first run.")
            # >> This is the first run.

            checker.mark_first_run()
            if checker.is_first_run():
                print("This is the first run.")
            else:
                print("This is not the first run.")
            # >> This is not the first run.

            checker.clear_first_run()
            if checker.is_first_run():
                print("This is the first run.")
            else:
                print("This is not the first run.")
            # >> This is the first run.

            if one_time_run():
                print("one time run")
            #>> one time run

    """
    _instance = None
    _lock = multiprocessing.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, file_path=".task_first_run.json", debug=False):
        if hasattr(self, "initialized"):
            return
        self.initialized = True

        self.file_path = file_path
        self.key = "default"
        self.debug = debug

        self._is_check_python_version = False
        self.data = self.load_data()

    def check_python_version(self):
        if not self._is_check_python_version:
            if sys.version_info.major != 3 or sys.version_info.minor != 7:
                current_version = f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
                print(f"Warning: This function can only be used with Python 3.7. Your current version is {current_version}")
                self._is_check_python_version = True

    def load_data(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    data = {}
        else:
            data = {}
        return data

    def sync_data(self):
        self.data = self.load_data()

    def save_data(self):
        with open(self.file_path, "w") as file:
            json.dump(self.data, file)

    def is_first_run(self, key=None):
        self.sync_data()
        if key:
            self.key = key
        return not self.data.get(self.key, False)

    def one_time_run(self, key=None):
        self.check_python_version()

        if key:
            self.key = key
        else:
            caller_frame = inspect.currentframe().f_back
            caller_module = inspect.getmodule(caller_frame)
            key = f"{caller_module.__name__}.{caller_frame.f_code.co_name}"  # Add module name to the key
            self.key = key

        with self._lock:
            _is_first_run_result = self.is_first_run(self.key)
            if _is_first_run_result:
                self.mark_first_run(self.key)
                return True
            return False

    def mark_first_run(self, key=None):
        if key:
            self.key = key
        self.data[self.key] = True
        self.save_data()

    def clear_first_run(self):
        self.data = {}
        if os.path.exists(self.file_path):
            os.remove(self.file_path)


first_run_checker = FirstRunChecker()
first_run_checker.clear_first_run()
one_time_run = first_run_checker.one_time_run

