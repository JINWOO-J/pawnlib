from pawnlib.utils.icx_signer import __make_params_serialized as make_params_serialized
from hashlib import sha3_256
from pawnlib.typing import format_hex, keys_exists, token_hex, get_size, sys_exit, FlatDict, error_and_exit, get_file_detail
from pawnlib.output.file import open_json, is_file, is_directory, is_json, write_json
from pawnlib.utils.in_memory_zip import read_file_from_zip, read_genesis_dict_from_zip
from pawnlib.config import pawn
import json
import shutil
import os
import zipfile
import tempfile
import re
import copy


class GenesisGenerator:
    """
    A class to generate and manage genesis files, including creating a temporary directory,
    parsing JSON, creating CID, and writing the genesis zip file.

    :param genesis_json_or_dict: A JSON dictionary or file path representing the genesis data.
    :type genesis_json_or_dict: Union[dict, str]
    :param base_dir: The base directory where the temporary files and final zip will be stored. Defaults to the pawnlib path.
    :type base_dir: str
    :param genesis_filename: The name of the genesis zip file to be created. Defaults to 'icon_genesis.zip'.
    :type genesis_filename: str

    Example:

        .. code-block:: python

            from pawnlib.utils import GenesisGenerator

            # Define a genesis JSON object
            genesis_data = {
                "accounts": [
                    {
                        "address": "hx112759c9e5718c48527f0242887b7f9f852da29d",
                        "balance": "0x2961fff8ca4a62327800000",
                        "name": "god"
                    },
                    {
                        "address": "hx1000000000000000000000000000000000000000",
                        "balance": "0x0",
                        "name": "treasury"
                    },
                    {
                        "address": "cx0000000000000000000000000000000000000001",
                        "name": "governance",
                        "score": {
                            "contentId": "hash:{{hash:governance/governance-2.2.1-optimized.jar}}",
                            "contentType": "application/java",
                            "owner": "hx522759c9e5718c48527f0242887b7f9f852da29d"
                        }
                    }
                ],
                "chain": {
                    "revision": "0x17",
                    "blockInterval": "0x3e8",
                    "roundLimitFactor": "0x10",
                    "fee": {
                        "stepPrice": "0x2e90edd00",
                        "stepLimit": {
                            "invoke": "0x9502f900",
                            "query": "0x2faf080"
                        },
                        "stepCosts": {
                            "apiCall": "0x2710",
                            "contractCall": "0x61a8",
                            "contractCreate": "0x3b9aca00",
                            "contractSet": "0x3a98",
                            "contractUpdate": "0x3b9aca00",
                            "default": "0x186a0",
                            "delete": "-0xf0",
                            "deleteBase": "0xc8",
                            "get": "0x19",
                            "getBase": "0xbb8",
                            "input": "0xc8",
                            "log": "0x64",
                            "logBase": "0x1388",
                            "schema": "0x1",
                            "set": "0x140",
                            "setBase": "0x2710"
                        }
                    },
                    "validatorList": [
                        "hx522759c9e5718c48527f0242887b7f9f852da29d"
                    ]
                },
                "message": "genesis for local node",
                "nid": "0x99"
            }

            # Create a GenesisGenerator object
            generator = GenesisGenerator(genesis_json_or_dict=genesis_data)

            # Run the generator to process and generate the genesis zip file
            cid = generator.run()
            print(f"Generated CID: {cid}")
    """

    def __init__(self, genesis_json_or_dict=None, base_dir=None, genesis_filename="icon_genesis.zip"):
        """
        Initialize the GenesisGenerator with the given genesis data, base directory, and zip filename.

        :param genesis_json_or_dict: Genesis data as a dictionary or file path.
        :param base_dir: Base directory to store the files.
        :param genesis_filename: Name of the final genesis zip file.
        """
        self.genesis_json_or_dict = copy.deepcopy(genesis_json_or_dict)
        self.base_dir = base_dir if base_dir else pawn.get_path()
        self.genesis_filename = genesis_filename
        self.prepare_temp_dir = None
        self.final_temp_dir = None
        self.cid = None
        self.nid = None
        self.genesis_json = None
        self.genesis_zip_info = {}

    def make_temp_dir(self):
        """
        Create temporary directories for preparing and finalizing the genesis file.
        """
        self.prepare_temp_dir = tempfile.mkdtemp()
        self.final_temp_dir = tempfile.mkdtemp()

    def initialize(self):
        """
        Initialize the genesis generator by loading the genesis JSON data from either a dictionary or a file.
        If it's a file path, the data will be loaded from the file.

        :raises ValueError: If the genesis data is neither a valid dictionary nor a valid file path.
        """
        if isinstance(self.genesis_json_or_dict, dict):
            self.genesis_json = copy.deepcopy(self.genesis_json_or_dict)
        elif isinstance(self.genesis_json_or_dict, str) and is_file(self.genesis_json_or_dict):
            self.genesis_json = open_json(self.genesis_json_or_dict)
        else:
            raise ValueError(f"Invalid genesis_json_or_dict: {type(self.genesis_json)}")
        self.make_temp_dir()

    def run(self, genesis_json_or_dict=None, base_dir=None, genesis_filename=None):
        """
        Main method to execute the genesis generation process. It initializes the data, logs relevant information,
        parses the genesis JSON, writes the zip file, and generates the CID.

        :param genesis_json_or_dict: Optional genesis data as a dictionary or file path.
        :param base_dir: Optional base directory to store the files.
        :param genesis_filename: Optional name of the final genesis zip file.
        :return: CID (content identifier) of the generated genesis file.
        :rtype: str
        """
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
        self.create_cid()
        pawn.console.debug(f"cid = {self.cid}")
        return self.cid

    def log_initialization_info(self):
        """
        Log the base directory and temporary directory information for debugging purposes.
        """
        pawn.console.debug(f"Base dir -> {self.base_dir}")
        pawn.console.debug(f"Generating prepare temporary -> {self.prepare_temp_dir}")
        pawn.console.debug(f"Generating final temporary -> {self.final_temp_dir}")

    def create_cid(self, data=None):
        """
        Create a CID (Content Identifier) by serializing the genesis data and calculating its hash.

        :param data: Optional data to be serialized and used to create the CID. If not provided, it uses `genesis_json_or_dict`.
        :return: The CID generated from the serialized data.
        :rtype: str
        """
        if data:
            self.genesis_json_or_dict = data
        serialized_data = make_params_serialized(self.genesis_json_or_dict)
        encoded_data = f"genesis_tx.{serialized_data}".encode()
        pawn.console.debug(encoded_data)
        cid_hash = sha3_256(encoded_data).digest().hex()
        self.cid = format_hex(cid_hash[:6])
        return self.cid

    def parse_and_write_genesis_json(self):
        """
        Parse the `genesis_json` data and replace `contentId` fields with the result of `make_score_zip()`.
        Then, write the updated genesis JSON to a temporary file.
        """
        for account in self.genesis_json.get('accounts', []):
            if keys_exists(account, "score", "contentId"):
                pawn.console.debug(account['score']['contentId'])
                parsed_content_id = self.make_score_zip(account['score']['contentId'])
                pawn.console.debug(f"parsed_content_id={parsed_content_id}")
                account['score']['contentId'] = parsed_content_id
        self.nid = self.genesis_json.get('nid')
        write_json(filename=f"{self.final_temp_dir}/genesis.json", data=self.genesis_json)

    def write_genesis_zip(self):
        """
        Write the genesis JSON to a zip file.

        :return: Information about the generated zip file, including its size and attributes.
        :rtype: dict
        """
        # genesis_zip_file = f"{self.base_dir}/{self.genesis_filename}"
        genesis_zip_file = self.genesis_filename
        make_zip_without(self.final_temp_dir, genesis_zip_file, ['tests'])
        # self.genesis_zip_info = get_size(genesis_zip_file, attr=True)
        self.genesis_zip_info = get_file_detail(genesis_zip_file)
        pawn.console.debug(f"Generated {genesis_zip_file} => {self.genesis_zip_info.get('size_pretty')}")
        return self.genesis_zip_info

    @staticmethod
    def extract_content_pattern(string):
        """
        Extracts a template key, template type, and template directory from the provided string using a regex pattern.

        :param string: The string containing the content pattern.
        :return: A tuple of the extracted template key, template type, and template directory.
        :rtype: tuple
        """
        pattern = r'(.*?):{{([^:]*):(.*)}}'
        match = re.search(pattern, string)
        if match:
            pawn.console.debug(f"[yellow]Matched[/yellow] {string} =>  {match.groups()}")
            return match.group(1), match.group(2), match.group(3)
        else:
            pawn.console.log(f"[red]Pattern not matched score.contentId:[/red] pattern={pattern} string={string}")

    def make_score_zip(self, content_id):
        """
        Create a zip file or copy the file based on the content ID and its type (e.g., ziphash or hash).

        :param content_id: The content ID that describes how to process the score directory.
        :return: The resulting hash with the file type.
        :rtype: str
        :raises ValueError: If the file or directory described by the content ID cannot be found.
        """
        template_key, template_type, template_dir = self.extract_content_pattern(content_id)
        score_dir = f"{self.base_dir}/{template_dir}"
        if template_type in ["ziphash", "hash"] and (is_directory(score_dir) or is_file(score_dir)):
            pawn.console.debug(f"{template_type} =>{score_dir}")
            pawn.console.debug(f"Found '{template_type}' directory -> {score_dir}")
            _score_file = self.make_zip_or_copy_file(template_type, score_dir)
            return f"hash:{_score_file}"
        else:
            raise ValueError(f"Not found file  >> '{score_dir}' for '{content_id}'")

    def make_zip_or_copy_file(self, template_type, score_dir):
        """
        Either create a zip file or copy a file, depending on the template type, and return the hash of the result.

        :param template_type: The type of the operation to perform ("ziphash" or "hash").
        :param score_dir: The directory or file to be processed.
        :return: The hash of the resulting file.
        :rtype: str
        """
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
    """
    Create a zip archive from the source directory, excluding specified subdirectories.

    :param src_dir: The source directory to zip.
    :type src_dir: str
    :param dst_file: The output file path for the zip archive.
    :type dst_file: str
    :param exclude_dirs: List of directory names to exclude from the zip archive.
    :type exclude_dirs: list
    """
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
    """
    Return the SHA-256 hash of a file.

    :param file_path: Path to the file to be hashed.
    :type file_path: str
    :return: The SHA-256 hash of the file.
    :rtype: str
    """
    with open(file_path, 'rb') as file:
        file_bytes = file.read()
        readable_hash = sha3_256(file_bytes).hexdigest()
    return readable_hash


def create_cid(data: dict):
    """
    Create a CID (Content Identifier) from a given dictionary by serializing the data and hashing it.

    :param data: The dictionary containing the genesis data.
    :type data: dict
    :return: The CID created from the serialized data.
    :rtype: str
    """
    _inner_data = make_params_serialized(data)
    data = f"genesis_tx.{_inner_data}".encode()
    pawn.console.debug(data)
    cid_hash = sha3_256(data).digest().hex()
    cid = format_hex(cid_hash[:6])
    return cid


def create_cid_from_genesis_file(genesis_file):
    """
    Create a CID from a genesis file by loading the file and generating the CID.

    :param genesis_file: Path to the genesis JSON file.
    :type genesis_file: str
    :return: The CID created from the genesis file.
    :rtype: str
    :raises FileNotFoundError: If the genesis file is not found.
    :raises PermissionError: If there are permission issues with the file.
    :raises Exception: If any other unexpected errors occur.
    """
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
    """
    Create a CID from a genesis zip file by extracting the JSON data from the zip and generating the CID.

    :param zip_file_name: Path to the genesis zip file.
    :type zip_file_name: str
    :return: The CID created from the zip file.
    :rtype: str
    """
    return create_cid(read_genesis_dict_from_zip(zip_file_name))


def validate_genesis_json(genesis_json=None):
    """
    Validate the structure of a genesis JSON object to ensure it contains all mandatory keys.

    :param genesis_json: The genesis JSON object to validate.
    :type genesis_json: dict
    :return: True if the genesis JSON is valid.
    :rtype: bool
    :raises SystemExit: If the genesis JSON is missing mandatory keys or is not a dictionary.
    """
    if not isinstance(genesis_json, dict):
        sys_exit("genesis_json is not dict")
    flat_dict = FlatDict(genesis_json)

    mandatory_keys = ["accounts", "chain", "chain.validatorList", "message", "nid"]
    missing_keys = []
    for key in mandatory_keys:
        if key not in flat_dict:
            missing_keys.append(key)

    if missing_keys:
        error_and_exit(
            "Invalid genesis_json format. Missing mandatory keys.\n"
            f"[bold red]Missing mandatory keys:[/bold red] {', '.join(missing_keys)}"
        )

    pawn.console.log("[bold bright_white]Genesis JSON validation successful.[/bold bright_white]")
    return True

genesis_generator = GenesisGenerator().run
