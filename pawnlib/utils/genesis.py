from pawnlib.utils.icx_signer import __make_params_serialized
from hashlib import sha3_256
from pawnlib.typing import format_hex, keys_exists, token_hex, get_size
from pawnlib.output.file import open_json, is_file, is_directory, is_json, write_json
from pawnlib.utils.in_memory_zip import read_file_from_zip, read_genesis_dict_from_zip
from pawnlib.config import pawn
import json
import shutil
import os
import zipfile
import tempfile
import re


class GenesisGenerator:
    def __init__(self, genesis_json_or_dict=None, base_dir=None, genesis_filename="icon_genesis.zip"):
        self.genesis_json_or_dict = genesis_json_or_dict
        self.base_dir = base_dir if base_dir else pawn.get_path()
        self.genesis_filename = genesis_filename
        self.prepare_temp_dir = None
        self.final_temp_dir = None
        self.cid = None
        self.genesis_json = None

    def make_temp_dir(self):
        self.prepare_temp_dir = tempfile.mkdtemp()
        self.final_temp_dir = tempfile.mkdtemp()

    def initialize(self):
        if isinstance(self.genesis_json_or_dict, dict):
            self.genesis_json = self.genesis_json_or_dict
        elif isinstance(self.genesis_json_or_dict, str) and is_file(self.genesis_json_or_dict):
            self.genesis_json = open_json(self.genesis_json_or_dict)
        else:
            raise ValueError(f"Invalid genesis_json_or_dict: {type(self.genesis_json)}")
        self.make_temp_dir()

    def run(self, genesis_json_or_dict=None, base_dir=None, genesis_filename="icon_genesis.zip"):
        if genesis_json_or_dict:
            self.genesis_json_or_dict = genesis_json_or_dict
        if base_dir:
            self.base_dir = base_dir
        if genesis_filename:
            self.genesis_filename = genesis_filename

        self.initialize()
        self.log_initialization_info()
        self.parse_and_write_genesis_json()
        self.write_genesis_zip()
        self.cid = create_cid(self.genesis_json_or_dict)
        pawn.console.debug(f"cid = {self.cid}")
        return self.cid

    def log_initialization_info(self):
        pawn.console.debug(f"Base dir -> {self.base_dir}")
        pawn.console.debug(f"Generating prepare temporary -> {self.prepare_temp_dir}")
        pawn.console.debug(f"Generating final temporary -> {self.final_temp_dir}")

    def parse_and_write_genesis_json(self):
        for account in self.genesis_json.get('accounts', []):
            if keys_exists(account, "score", "contentId"):
                pawn.console.debug(account['score']['contentId'])
                parsed_content_id = self.make_score_zip(account['score']['contentId'])
                pawn.console.debug(f"parsed_content_id={parsed_content_id}")
                account['score']['contentId'] = parsed_content_id
        write_json(filename=f"{self.final_temp_dir}/genesis.json", data=self.genesis_json)

    def write_genesis_zip(self):
        genesis_zip_file = f"{self.base_dir}/{self.genesis_filename}"
        make_zip_without(self.final_temp_dir, genesis_zip_file, ['tests'])
        file_info = get_size(genesis_zip_file, attr=True)
        pawn.console.debug(f"Generated {genesis_zip_file} => {file_info}")

    @staticmethod
    def extract_content_pattern(string):
        pattern = r'(.*?):{{([^:]*):(.*)}}'
        match = re.search(pattern, string)
        if match:
            pawn.console.debug(f"[yellow]Matched[/yellow] {string} =>  {match.groups()}")
            return match.group(1), match.group(2), match.group(3)

    def make_score_zip(self, content_id):
        template_key, template_type, template_dir = self.extract_content_pattern(content_id)
        # pawn.console.debug(f"{content_id} => {template_key}, {template_type}, {template_dir}")
        score_dir = f"{self.base_dir}/{template_dir}"
        if template_type in ["ziphash","hash"] and (is_directory(score_dir) or is_file(score_dir)):
            pawn.console.debug(f"{template_type} =>{score_dir}")
            pawn.console.debug(f"Found '{template_type}' directory -> {score_dir}")
            _score_file = self.make_zip_or_copy_file(template_type, score_dir)
            return f"hash:{_score_file}"
        else:
            raise ValueError(f"Not found file  >> '{score_dir}' for '{content_id}'")

    def make_zip_or_copy_file(self, template_type, score_dir):
        _score_file = f"{self.prepare_temp_dir}/{token_hex(16)}"
        if template_type == "ziphash":
            make_zip_without(score_dir, _score_file, ['tests'])
        elif template_type == "hash":
            shutil.copy(score_dir, _score_file)
        _score_hash = calculate_hash(_score_file)
        _score_hash_file = f"{self.final_temp_dir}/{_score_hash}"
        os.rename(_score_file, _score_hash_file)
        return _score_hash


def make_zip_without(src_dir, dst_file, exclude_dirs):
    with zipfile.ZipFile(dst_file, 'w', zipfile.ZIP_DEFLATED, False, compresslevel=9) as zipf:
        for root, dirs, files in os.walk(src_dir):
            if not any(exclude_dir in root for exclude_dir in exclude_dirs):
                for file in files:
                    file_path = os.path.join(root, file)
                    zip_info = zipfile.ZipInfo(os.path.relpath(file_path, src_dir))
                    zip_info.date_time = (1980, 1, 1, 0, 0, 0)  # ZIP file format requires year >= 1980
                    with open(file_path, 'rb') as f:
                        zipf.writestr(zip_info, f.read())

def calculate_hash(file_path):
    """Return the SHA-256 hash of a zip file."""
    with open(file_path, 'rb') as file:
        file_bytes = file.read()
        readable_hash = sha3_256(file_bytes).hexdigest()
    return readable_hash


def create_cid(data: dict):
    _inner_data = __make_params_serialized(data)
    data = f"genesis_tx.{_inner_data}".encode()
    pawn.console.debug(data)
    cid_hash = sha3_256(data).digest().hex()
    cid = format_hex(cid_hash[:6])
    return cid


def create_cid_from_genesis_file(genesis_file):
    try:
        file_dict = open_json(genesis_file)
        readable_hash = create_cid(file_dict)
        return readable_hash
    except FileNotFoundError:
        print(f"Error: File '{genesis_file}' not found.")
    except PermissionError:
        print(f"Error: Permission denied for file '{genesis_file}'.")
    except Exception as e:
        print(f"Error: An unexpected error occurred - {str(e)}")


def create_cid_from_genesis_zip(zip_file_name):
    return create_cid(read_genesis_dict_from_zip(zip_file_name))


genesis_generator = GenesisGenerator().run
