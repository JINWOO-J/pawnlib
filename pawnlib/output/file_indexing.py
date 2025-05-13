import os
import xxhash
import asyncio
import aiofiles
import json
import datetime
import re
from itertools import zip_longest
from tqdm import tqdm
import logging
import argparse
from rich.console import Console
from rich.progress import (
    Progress, TaskProgressColumn, SpinnerColumn, BarColumn, TextColumn,
    TimeElapsedColumn, TimeRemainingColumn
)
from pawnlib.typing.converter import get_file_detail

logger = logging.getLogger(__name__)

class FileIndexer:
    def __init__(self, base_dir="./", output_dir="./", prefix=None, worker=20, debug=False,
                 check_method="hash", checksum_filename="checksum.json", index_filename="file_list.txt",  exclude_files=None, exclude_extensions=None):
        self.base_dir = base_dir
        self.output_dir = output_dir
        self.prefix = prefix
        self.worker = worker
        self.debug = debug
        self.check_method = check_method
        self.exclude_files = exclude_files or ["ee.sock", "icon_genesis.zip", "download.py"]

        if self.exclude_files:
            self.exclude_files.append(checksum_filename)
            self.exclude_files.append(index_filename)

        self.exclude_extensions = exclude_extensions or ["sock"]
        self.indexed_files = {}
        self.result = {"status": "OK", "errors": {}}
        self.index_filename = os.path.join(output_dir, index_filename)
        self.checksum_filename = os.path.join(output_dir, checksum_filename)
        self.file_list = []
        self.total_file_count = 0

    def list_files_recursive(self):
        """
        Recursively list files in the base directory, excluding files and extensions as defined.
        """
        all_files = []
        for root, _, files in os.walk(self.base_dir):
            for file in files:
                full_path = os.path.join(root, file)
                if self.is_excluded(full_path):
                    all_files.append(full_path)

        self.file_list = all_files
        self.total_file_count = len(self.file_list)
        self.sliced_file_list = zip_longest(*[iter(self.file_list)] * self.worker, fillvalue=None)


    def is_excluded(self, file_path):
        """
        Check if a file should be excluded based on file name or extension.
        """
        basename = os.path.basename(file_path).lower()
        if basename in self.exclude_files:
            return False

        # for exclude in self.exclude_files:
        #     if exclude in file_path:
        #         return False
        _, ext = os.path.splitext(file_path)
        if ext and ext.lstrip(".") in self.exclude_extensions:
            return False
        return True

    async def async_executor(self, file_list, progress, task_id):
        """
        Execute file parsing tasks asynchronously.
        """
        tasks = [
            asyncio.create_task(self.parse_file(file, progress, task_id))
            for file in file_list if file
        ]
        await asyncio.gather(*tasks)

    async def parse_file(self, file_path, progress, task_id):
        """
        Parse a single file, calculate its checksum, and save to output.
        """
        checksum = await self.calculate_checksum(file_path)
        file_size = await self.get_file_size(file_path)
        relative_path = os.path.relpath(file_path, self.base_dir)
        download_url = f"{self.prefix}/{relative_path}" if self.prefix else relative_path

        self.indexed_files[relative_path] = {
            "file_size": file_size,
            "checksum": checksum,
        }

        async with aiofiles.open(self.index_filename, mode='a') as f:
            await f.write(f"{download_url}\n\tout={relative_path}\n")

        if self.debug:
            logger.debug(f"[Processed] {file_path} | Size: {file_size} | Checksum: {checksum}")

        # Update progress
        progress.update(task_id, advance=1)
        progress.update(task_id, description=f"[bold blue]Processed {progress.tasks[task_id].completed}/{self.total_file_count} files")

    async def calculate_checksum(self, file_path, read_size=10240):
        """
        Calculate the checksum of the last `read_size` bytes of a file asynchronously.
        """
        async with aiofiles.open(file_path, "rb") as f:
            await f.seek(0, 2)
            file_size = await f.tell()
            start_position = max(0, file_size - read_size)
            await f.seek(start_position)
            content = await f.read()
            return xxhash.xxh3_64_hexdigest(content)

    async def get_file_size(self, file_path):
        """
        Get the size of a file asynchronously.
        """
        return os.path.getsize(file_path)

    async def process_files(self):
        """
        Process all files asynchronously in batches, with `rich` progress tracking.
        """
        console = Console()
        with Progress(
                "[bold blue]{task.description}",
                BarColumn(bar_width=None),  # Fill the screen width
                TaskProgressColumn(show_speed=True),
                TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=console,
        ) as progress:
            task_id = progress.add_task(f"Processed 0/{self.total_file_count} files", total=self.total_file_count)
            for file_batch in self.sliced_file_list:
                await self.async_executor(file_batch, progress, task_id)

    def save_json(self, filename, data):
        """
        Save data to a JSON file.
        """
        try:
            with open(filename, "w") as f:
                json.dump(data, f, indent=4)
            logger.info(f"JSON saved to {self.pretty_file_info(filename)}")
        except Exception as e:
            logger.error(f"Failed to save JSON to {filename}: {e}")

    def load_json(self, filename):
        """
        Load data from a JSON file.
        """
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load JSON from {filename}: {e}")
            return {}

    async def check(self):
        """
        Verify files based on previously generated checksums.
        """
        indexed_data = self.load_json(self.checksum_filename)
        if not indexed_data:
            logger.error("No checksum file found. Run indexing first.")
            self.result["status"] = "FAIL"
            return self.result

        for file_name, meta in tqdm(indexed_data.items(), desc="Validating files"):
            full_path = os.path.join(self.base_dir, file_name)
            if not os.path.exists(full_path):
                logger.warning(f"File missing: {file_name}")
                self.result["errors"][file_name] = {"error": "File missing"}
                self.result["status"] = "FAIL"
                continue

            file_size = await self.get_file_size(full_path)
            if file_size != meta.get("file_size"):
                logger.warning(f"Size mismatch: {file_name} (expected: {meta.get('file_size')}, found: {file_size})")
                self.result["errors"][file_name] = {"error": "Size mismatch"}
                self.result["status"] = "FAIL"
                continue

            if self.check_method == "hash":
                checksum = await self.calculate_checksum(full_path)
                if checksum != meta.get("checksum"):
                    logger.warning(f"Checksum mismatch: {file_name} (expected: {meta.get('checksum')}, found: {checksum})")
                    self.result["errors"][file_name] = {"error": "Checksum mismatch"}
                    self.result["status"] = "FAIL"

        if self.result["status"] == "OK":
            logger.info("All files validated successfully.")
        return self.result

    @staticmethod
    def pretty_file_info(filename=None):
        file_info = get_file_detail(filename)
        return f"'{file_info.get('file_path')}' ({file_info.get('size_pretty')}) modification: {file_info.get('modification_time')}"

    async def run(self):
        """
        Main method to execute file indexing.
        """
        os.makedirs(self.output_dir, exist_ok=True)
        self.list_files_recursive()
        if os.path.exists(self.index_filename):
            os.remove(self.index_filename)
        await self.process_files()

        logger.info(f"INDEX saved to {self.pretty_file_info(self.index_filename)}")

        self.save_json(self.checksum_filename, self.indexed_files)


def main():
    parser = argparse.ArgumentParser(description="File Indexer with Asynchronous Processing.")
    parser.add_argument("--base-dir", default="./", help="Base directory to index files from.")
    parser.add_argument("--output-dir", default="./", help="Directory to save the index and checksum files.")
    parser.add_argument("--prefix", default=None, help="Prefix to add to file URLs.")
    parser.add_argument("--worker", type=int, default=20, help="Number of workers for async processing.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("--check", action="store_true", help="Validate files based on checksum.")
    parser.add_argument("--check-method", choices=["hash", "size_only"], default="hash", help="Method to validate files.")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    indexer = FileIndexer(
        base_dir=args.base_dir,
        output_dir=args.output_dir,
        prefix=args.prefix,
        worker=args.worker,
        debug=args.debug,
        check_method=args.check_method,
    )

    if args.check:
        asyncio.run(indexer.check())
    else:
        asyncio.run(indexer.run())


if __name__ == "__main__":
    main()
