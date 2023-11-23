from io import BytesIO
from os import path, walk
from zipfile import ZipFile, ZIP_DEFLATED
import json
from pawnlib.config import pawn

def gen_deploy_data_content(_path: str) -> bytes:
    """Generate bytes of zip data of SCORE.

    :param _path: Path of the directory to be zipped.
    """
    if path.isdir(_path) is False and path.isfile(_path) is False:
        raise ValueError(f"Invalid path {_path}")
    try:
        memory_zip = InMemoryZip()
        memory_zip.zip_in_memory(_path)
    except Exception as e:
        raise ValueError(f"Can't zip SCORE contents - {e}")
    else:
        return memory_zip.data


def read_file_from_zip(zip_file_name, target_file_name):
    with open(zip_file_name, 'rb') as file:
        zip_data = file.read()

    zip_buffer = BytesIO(zip_data)
    with ZipFile(zip_buffer, 'r') as zip_ref:
        pawn.console.debug("Contents of", zip_file_name + ":", zip_ref.namelist())
        if target_file_name in zip_ref.namelist():
            with zip_ref.open(target_file_name) as target_file:
                file_contents = target_file.read()
                pawn.console.debug(f"Contents of {target_file_name}:", file_contents.decode('utf-8'))
                return file_contents.decode('utf-8')
        else:
            pawn.console.debug(f"{target_file_name} not found in the zip file.")
        return ""

def read_genesis_dict_from_zip(zip_file_name: str = "") -> dict:
    genesis_dict = json.loads(read_file_from_zip(zip_file_name, "genesis.json"))
    return genesis_dict


class InMemoryZip:
    """Class for compressing data in memory using zip and BytesIO."""

    def __init__(self):
        self._in_memory = BytesIO()

    @property
    def data(self) -> bytes:
        """Returns zip data

        :return: zip data
        """
        self._in_memory.seek(0)
        return self._in_memory.read()

    def zip_in_memory(self, _path: str):
        """Compress zip data (bytes) in memory.

        :param _path: The path of the directory to be zipped.
        """
        try:
            # when it is a zip file
            if path.isfile(_path):
                zf = ZipFile(_path, 'r', ZIP_DEFLATED, False)
                zf.testzip()
                with open(_path, mode='rb') as fp:
                    fp.seek(0)
                    self._in_memory.seek(0)
                    self._in_memory.write(fp.read())
            else:
                # root path for figuring out directory of tests
                tmp_root = None
                with ZipFile(self._in_memory, 'a', ZIP_DEFLATED, False, compresslevel=9) as zf:
                    for root, folders, files in walk(_path):
                        if 'package.json' in files:
                            tmp_root = root
                        if tmp_root and root.replace(tmp_root,'') == '/tests':
                            continue
                        if root.find('__pycache__') != -1:
                            continue
                        if root.find('/.') != -1:
                            continue
                        for file in files:
                            if file.startswith('.'):
                                continue
                            full_path = path.join(root, file)
                            zf.write(full_path)
        except Exception as e:
            raise ValueError(f"InMemoryZip Error: {e}")


