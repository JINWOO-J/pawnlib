from io import BytesIO
from os import path, walk
from zipfile import ZipFile, ZIP_DEFLATED


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
        except ZipException:
            raise ZipException

