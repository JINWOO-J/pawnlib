import os
import re
import time
import json
import boto3
import asyncio
import aioboto3
from datetime import datetime
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn,  DownloadColumn
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError
from pawnlib.config import pawn, setup_app_logger, LoggerMixin, LoggerMixinVerbose
from pawnlib.typing import sys_exit, extract_values_in_list, mask_string, convert_bytes
from botocore.client import Config
from botocore.exceptions import ClientError as BotoClientError
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.text import Text
from pawnlib.typing.constants import UnitMultiplierConstants, const

from rich.console import Console
from tqdm import tqdm
import threading
import logging

logger = logging.getLogger(__name__)

debug_console = Console(stderr=True)

def get_transfer_config(file_size):
    if file_size == 0:
        return None
    elif file_size >= 100 * 1024 * 1024:  # 예: 100MB 이상
        # boto3.setup_default_session(
        #     config=BotoSessionConfig(
        #         max_pool_connections=20,
        #         retries={'max_attempts': 3}
        #     )
        # )
        return TransferConfig(
            use_threads=True,
            max_concurrency=20,
            multipart_threshold=256 * 1024 * 1024,
            multipart_chunksize=16 * 1024 * 1024,
        )

    elif file_size >= 5 * 1024 * 1024:  # 예: 5MB 이상
        return TransferConfig(
            use_threads=True,
            max_concurrency=10,
            multipart_threshold=5 * 1024 * 1024,    # 5MB
            multipart_chunksize=5 * 1024 * 1024     # 5MB
        )
    else:
        return TransferConfig(
            use_threads=True,
            max_concurrency=10,
            multipart_threshold=1024,    # 5MB
            multipart_chunksize=1024     # 5MB
        )


class TqdmProgressCallback:
    def __init__(self, tqdm_instance, lock):
        self.tqdm_instance = tqdm_instance
        self.lock = lock

    def __call__(self, bytes_amount):
        if self.tqdm_instance is None:
            # tqdm_instance가 None인 경우 로그만 남기고 아무것도 하지 않음
            debug_console.log("tqdm_instance is None, cannot update progress.")
            return
        with self.lock:
            self.tqdm_instance.update(bytes_amount)


class SpeedColumn(TextColumn):

    def __init__(self, unit="B/s", **kwargs):
        """
        Custom column for displaying transfer speed based on true elapsed time.

        Args:
            unit (str): The unit for displaying speed, "B/s" or "Mbps".
            **kwargs: Additional arguments for the TextColumn.
        """
        super().__init__("[progress.speed]{task.fields[speed]}", **kwargs)
        self.unit = unit
        self.multiplier = const.get_unit_multiplier(unit)

    def render(self, task) -> Text:
        """
        Override the render method to calculate speed based on actual time elapsed.

        Args:
            task (Task): The Rich task instance being updated.

        Returns:
            Text: Rich text displaying the calculated speed.
        """
        if not hasattr(task, 'last_update_time'):
            # Initialize task-specific attributes the first time render is called
            task.total_bytes = 0
            task.last_update_time = time.time()
            task.start_time = task.last_update_time
            task.last_bytes_transferred = 0
            # task.fields["speed"] = "0.00 B/s"
            task.fields["speed"] = f"0.00 {self.unit} (avg: 0.00 {self.unit})"


        # Calculate actual time elapsed since last update
        current_time = time.time()
        time_elapsed = current_time - task.last_update_time
        total_elapsed = current_time - task.start_time

        # Calculate speed based on bytes transferred since last render
        bytes_transferred = task.completed - task.last_bytes_transferred

        if time_elapsed >= 1:  # Update speed every second
            current_speed = self._calculate_speed(bytes_transferred, time_elapsed)
            average_speed = self._calculate_speed(task.completed, total_elapsed)

            task.fields["speed"] = f"{current_speed:.2f} {self.unit} (avg: {average_speed:.2f})"

            # Update last recorded values
            task.last_update_time = current_time
            task.last_bytes_transferred = task.completed

        return Text(task.fields["speed"])

    def _calculate_speed(self, bytes_transferred, time_elapsed):
        """Calculate speed based on the selected unit and elapsed time."""
        return (bytes_transferred / self.multiplier) / time_elapsed


class ProgressCallback:
    def __init__(self, progress, task, total_bytes, unit="Mbps"):
        """
        Initializes the ProgressCallback object.

        Args:
            progress (Progress): Rich Progress instance for updating UI.
            task (TaskID): Task ID for tracking progress.
            total_bytes (int): Total size of the file in bytes.
            unit (str): Speed unit, either "B/s" or "Mbps".
        """
        self.progress = progress
        self.task = task
        self.total_bytes = total_bytes
        self.unit = unit
        self.multiplier = const.get_unit_multiplier(unit)
        self.total_bytes_transferred = 0
        self.bytes_since_last = 0
        self.time_since_last = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        if self.total_bytes == 0:
            # For zero-byte files, mark the task as complete immediately
            self.progress.update(self.task, completed=1, total=1, speed=f"0 {self.unit}")
            self.progress.refresh()

    def update_unit(self, unit):
        """Update the unit of speed and adjust the multiplier accordingly."""
        self.unit = unit
        self.multiplier = const.get_unit_multiplier(unit)

    def _calculate_speed(self, bytes_transferred, time_elapsed):
        """Calculate speed based on the selected unit and elapsed time."""
        return (bytes_transferred / self.multiplier) / time_elapsed if time_elapsed > 0 else 0

    def __call__(self, bytes_transferred):
        """
        Callable method to handle the progress update.

        Args:
            bytes_transferred (int): Bytes transferred in the last chunk.
        """
        current_time = time.time()
        time_elapsed = current_time - self.last_update_time
        total_elapsed = current_time - self.start_time
        self.total_bytes_transferred += bytes_transferred
        self.bytes_since_last += bytes_transferred
        self.time_since_last += time_elapsed

        # Update speed every second or upon completion
        if self.time_since_last >= 1 or self.total_bytes_transferred == self.total_bytes:
            current_speed = self._calculate_speed(self.bytes_since_last, self.time_since_last)
            average_speed = self._calculate_speed(self.total_bytes_transferred, total_elapsed)
            speed_str = f"{current_speed:.2f} {self.unit} (avg: {average_speed:.2f} {self.unit})"

            self.progress.update(self.task, completed=self.total_bytes_transferred, speed=speed_str)

            self.bytes_since_last = 0
            self.time_since_last = 0
            self.last_update_time = current_time
        else:
            self.progress.update(self.task, completed=self.total_bytes_transferred)
            self.last_update_time = current_time


class S3ClientBase(LoggerMixinVerbose):
    def __init__(self,
                 bucket_name="",
                 profile_name=None,
                 access_key=None,
                 secret_key=None,
                 endpoint_url=None,
                 overwrite=False,
                 dry_run=False,
                 use_dynamic_config=False,
                 verbose=0,
                 logger=None,
                 ):
        self.init_logger(verbose=verbose, logger=logger)
        self.access_key = access_key or os.environ.get('AWS_ACCESS_KEY_ID')
        self.secret_key = secret_key or os.environ.get('AWS_SECRET_ACCESS_KEY')
        self.endpoint_url = endpoint_url or os.environ.get('AWS_ENDPOINT_URL') or os.environ.get('S3_ENDPOINT_URL')
        self.bucket_name = bucket_name
        self.overwrite = overwrite
        self.dry_run = dry_run
        self.use_dynamic_config = use_dynamic_config
        self.profile_name = profile_name
        self.s3_client = None
        self.is_cloudflare = None
        self.session = None
        self.config = None
        self.create_s3_client()

    def create_s3_client(self):
        if self.profile_name:
            self.logger.info(f"Using profile: {self.profile_name}")
            self.session = boto3.Session(profile_name=self.profile_name)
            self.endpoint_url = None
        elif self.access_key and self.secret_key:
            self.logger.info(f"Using access key: {self.access_key}")
            self.session = boto3.Session(
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
            )
        else:
            self.session = boto3.Session()  # IAM Role, env vars 등

        self.is_cloudflare = len(self.access_key) == 32 if self.access_key else False

        config = Config(
            signature_version='s3v4',
            max_pool_connections=20,
            retries={
                'max_attempts': 10,
                'mode': 'standard'
            }
        )

        if self.is_cloudflare:
            pawn.console.log("Using Cloudflare")
            self.s3_client = self.session.client(
                's3',
                endpoint_url=self.endpoint_url,
                config=config,
                region_name='auto',
                # verify=False
            )
        else:
            if os.environ.get('S3_ENDPOINT_URL') == self.endpoint_url:
                self.endpoint_url = None
            self.s3_client = self.session.client(
                's3',
                # config=config,
                endpoint_url=self.endpoint_url,
            )

        # TransferConfig 설정
        self.config = TransferConfig(
            use_threads=True,  # 멀티스레딩 활성화
            max_concurrency=20,  # 멀티스레딩 동시 처리 수
            multipart_threshold=256 * 1024 * 1024,  # 멀티파트 업로드를 시작하는 파일 크기 (256MB)
            multipart_chunksize=50 * 1024 * 1024,  # 멀티파트 업로드를 위한 청크 크기 (16MB)
        )

        # self.config = TransferConfig(
        #     use_threads=True,
        #     max_concurrency=10,
        #     multipart_threshold=1024,  # 8MB
        #     multipart_chunksize=1024# 8MB
        # )

    def bucket_exists(self):
        """Check if the bucket exists."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except Exception as e:
            logger.error(f"[bold red]Bucket {self.bucket_name} does not exist: {e}[/bold red]")
            return False

    def print_config(self):
        config_tree = Tree("Uploader Configuration")
        config_tree.add(f"Service: [bold]{'Cloudflare R2' if self.is_cloudflare else 'AWS S3'}[/bold]")
        config_tree.add(f"Bucket Name: [cyan]{self.bucket_name}[/cyan]")
        config_tree.add(f"Overwrite: [green]{self.overwrite}[/green]")
        # config_tree.add(f"Info File: [yellow]{self.info_file}[/yellow]")


        # adapter = self.s3_client._endpoint.http_session.adapters.get('https://')

        pool_manager = self.s3_client._endpoint.http_session._manager


        s3_config = config_tree.add("S3 Client Configuration")
        s3_config.add(f"Region Name: [magenta]{self.s3_client.meta.region_name}[/magenta]")
        s3_config.add(f"Endpoint URL: [blue]{self.s3_client._endpoint.host}[/blue]")
        s3_config.add(f"Signature Version: [cyan]{self.s3_client._client_config.signature_version}[/cyan]")
        # from pawnlib.output import classdump, print_var
        # classdump(pool_manager)
        # print_var(pool_manager.pools._maxsize)
        s3_config.add(f"Pool: [cyan]{pool_manager.pools._maxsize}[/cyan]")

        creds = self.session.get_credentials()
        if creds:
            cred_info = config_tree.add("Credentials")
            cred_info.add(f"Access Key ID: [red]{mask_string(creds.access_key)}[/red]")
            cred_info.add(f"Secret Access Key: [red]{mask_string(creds.secret_key, show_chars=3)}[/red]")
            if creds.token:
                cred_info.add("Session Token: [red][REDACTED][/red]")
        else:
            config_tree.add("[bold red]No credentials found.[/bold red]")

        transfer_config = config_tree.add("TransferConfig")
        transfer_config.add(f"Multipart Threshold: [cyan]{self.config.multipart_threshold}[/cyan] bytes")
        transfer_config.add(f"Max Concurrency: [cyan]{self.config.max_concurrency}[/cyan]")
        transfer_config.add(f"Multipart Chunksize: [cyan]{self.config.multipart_chunksize}[/cyan] bytes")
        transfer_config.add(f"Use Threads: [green]{self.config.use_threads}[/green]")

        pawn.console.print(Panel(config_tree, title="Uploader Configuration", expand=False))

    def debug_info(self):
        self.print_config()

        try:
            response = self.s3_client.list_buckets()
            bucket_table = Table(title="Available Buckets")
            bucket_table.add_column("Bucket Name", style="cyan")
            for bucket in response['Buckets']:
                bucket_table.add_row(bucket['Name'])
            pawn.console.print(Panel(bucket_table, title="Successfully connected to S3/R2", expand=False))
        except Exception as e:
            pawn.console.print(Panel(f"[bold red]Error connecting to S3/R2:[/bold red] {str(e)}", title="Connection Error", expand=False))

    def test_upload(self, test_file_path):
        try:
            print(f"Attempting to upload test file: {test_file_path}")
            with open(test_file_path, 'rb') as file:
                self.s3_client.put_object(Bucket=self.bucket_name, Key='test_upload.txt', Body=file)
            print("Test upload successful")
        except Exception as e:
            print(f"Test upload failed: {str(e)}")

    # def __call__(self):
    #     return self.s3_client


class Uploader(S3ClientBase):
    def __init__(self, bucket_name, profile_name=None, access_key=None, secret_key=None,
                 endpoint_url=None, overwrite=False, info_file="", confirm_upload=False, keep_path=False,
                 use_dynamic_config=False, dry_run=False, verbose=0):
        super().__init__(bucket_name, profile_name, access_key, secret_key, endpoint_url, overwrite,
                         use_dynamic_config=use_dynamic_config, verbose=verbose)


        self.uploaded_files_info = []
        self.directory = ""
        self.append_suffix = ""
        self.total_uploaded_size = 0
        self.info_file = info_file
        self.confirm_upload = confirm_upload
        self.keep_path = keep_path

        self.dry_run = dry_run
        self.lock = threading.Lock()
        self.pbar_lock = threading.Lock()

    def upload_single_part(self, file_path, bucket_name, s3_key):
        with open(file_path, 'rb') as f:
            self.s3_client.put_object(Bucket=bucket_name, Key=s3_key, Body=f)

    def upload_file_in_thread(self, *args, **kwargs):
        file_pbar = kwargs.pop('file_pbar', None)
        # Create a threading event to signal when the upload is complete
        upload_complete = threading.Event()

        def target():
            try:
                self.upload_file(*args, file_pbar=file_pbar, **kwargs)
            finally:
                upload_complete.set()

        thread = threading.Thread(target=target)
        thread.start()

        while not upload_complete.is_set():
            time.sleep(0.1)  # Sleep briefly to reduce CPU usage
        thread.join()

    def is_exist_bucket(self, bucket_name=None):
        if not bucket_name:
            bucket_name = self.bucket_name

        bucket_list = extract_values_in_list("Name", S3Lister().list_buckets())

        if bucket_name in bucket_list:
            return True
        return False

    def is_exist_s3_key(self, key=""):
        if not key:
            return False

        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            pawn.console.log(f"S3 키 존재: {key}")
            return True
        except self.s3_client.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                pawn.console.log(f"S3 키 없음: {key}")
            else:
                pawn.console.error(f"S3 키 확인 중 오류 발생: {key} - {str(e)}")
            return False
        except Exception as e:
            pawn.console.error(f"예상치 못한 오류: {key} - {str(e)}")
            return False

    def get_existing_s3_keys(self, bucket_name, prefix):
        """Retrieve all existing keys from S3 under the specified prefix."""
        paginator = self.s3_client.get_paginator('list_objects_v2')
        keys = set()
        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            if 'Contents' in page:
                keys.update(obj['Key'] for obj in page['Contents'])
        return keys

    def upload_file(self, file_path, s3_prefix="", s3_key="", file_pbar=None, append_suffix="", confirm_upload=None, keep_path=None):
        if not s3_key:
            s3_key = os.path.join(s3_prefix, file_path).replace("\\", "/")

        s3_key = s3_key.lstrip("/")

        if self.dry_run:
            pawn.console.log(f"<Dry-Run> Uploading {file_path} to s3://{self.bucket_name}/{s3_key}")
            return

        if file_path.endswith('.sock'):
            debug_console.log(f"Skipping socket file: {file_path}")
            return

        file_size = os.path.getsize(file_path)

        try:
            if not self.overwrite:
                try:
                    self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
                    debug_console.log(f"\nFile already exists in S3: {s3_key}")
                    if file_pbar:
                        with self.pbar_lock:
                            file_pbar.update(file_size if file_size > 0 else 1)
                    return
                except self.s3_client.exceptions.ClientError:
                    pass

            if file_size == 0:
                # Handle zero-byte files
                self.s3_client.put_object(Bucket=self.bucket_name, Key=s3_key, Body=b'')
                if file_pbar:
                    with self.pbar_lock:
                        file_pbar.update(1)
            else:
                if self.use_dynamic_config:
                    config = get_transfer_config(file_size)
                else:
                    config = self.config

                # Ensure file_pbar is initialized
                if file_pbar is None:
                    file_pbar = tqdm(total=file_size, desc=f"Uploading {os.path.basename(file_path)}", unit="B", unit_scale=True)
                    debug_console.log(f"Created new file_pbar for file: {file_path}")

                progress_callback = TqdmProgressCallback(file_pbar, self.pbar_lock)
                self.s3_client.upload_file(
                    file_path, self.bucket_name, s3_key,
                    Config=config,
                    Callback=progress_callback,
                )

            # Record uploaded file info in a thread-safe manner
            file_info = {
                "file_name": s3_key,
                "size": file_size,
                "upload_time": datetime.now().isoformat()
            }
            with self.lock:
                self.total_uploaded_size += file_info["size"]
                self.uploaded_files_info.append(file_info)

        except Exception as e:
            if file_pbar:
                with self.pbar_lock:
                    file_pbar.write(f"Error uploading {file_path}: {str(e)}")
            debug_console.log(f"Error uploading {file_path}: {str(e)}")


    def upload_directory(self, source_dir="", s3_prefix="", append_suffix="", info_file="", unit="B/s", max_workers=None):
        if not self.is_exist_bucket():
            raise ValueError(f"The specified bucket does not exist - '{self.bucket_name}'")

        directory_path = source_dir.replace("./", "")

        # Get file list
        if os.path.isfile(directory_path):
            file_list = [{'name': os.path.basename(directory_path), 'size': os.path.getsize(directory_path)}]
            directory_path = os.path.dirname(directory_path)
        elif os.path.isdir(directory_path):
            file_list = self.get_file_list(directory_path)
        else:
            raise ValueError(f"The path {directory_path} does not exist.")

        total_files = len(file_list)
        total_size = sum(file_info['size'] for file_info in file_list)
        print(f"Total files to upload: {total_files}, Total size: {self.format_size(total_size)}")

        # Optimize max_workers
        if max_workers is None:
            max_workers = min(32, max(1, os.cpu_count() * 2))

        # Fetch existing keys with batch processing
        existing_keys = set()
        for page in self.s3_client.get_paginator('list_objects_v2').paginate(Bucket=self.bucket_name, Prefix=s3_prefix):
            if 'Contents' in page:
                existing_keys.update(obj['Key'] for obj in page['Contents'])

        success_files, failed_files, skipped_files = [], [], []

        if self.dry_run:
            for file_info in file_list:
                file_path = os.path.join(directory_path, file_info['name'])
                s3_key = os.path.join(s3_prefix, file_path).replace("\\", "/")
                if s3_key in existing_keys:
                    print(f"[DRY RUN] File already exists: '{file_path}' -> 's3://{self.bucket_name}/{s3_key}' (skipped)")
                else:
                    print(f"[DRY RUN] Would upload: '{file_path}' -> 's3://{self.bucket_name}/{s3_key}'")
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {}
                overall_pbar = tqdm(total=total_size, desc="Total Progress", unit="B", unit_scale=True, ncols=80, bar_format="{l_bar}{bar}| {percentage:.0f}% {rate_fmt}")

                for file_info in file_list:
                    file_path = os.path.join(directory_path, file_info['name'])
                    s3_key = os.path.join(s3_prefix, file_path).replace("\\", "/")

                    if not self.overwrite and s3_key in existing_keys:
                        debug_console.log(f"File already exists in S3: {s3_key}")
                        skipped_files.append(file_info)
                        continue

                    file_pbar = tqdm(total=file_info['size'], desc=f"Uploading {file_info['name']}", unit="B", unit_scale=True, ncols=80, bar_format="{l_bar}{bar}| {percentage:.0f}% {rate_fmt}", leave=False)
                    future = executor.submit(
                        self.upload_file_safe,
                        file_path=file_path,
                        directory_path=directory_path,
                        s3_key=s3_key,
                        append_suffix=append_suffix,
                        file_pbar=file_pbar,
                        overall_pbar=overall_pbar
                    )
                    future_to_file[future] = file_info

                for future in as_completed(future_to_file):
                    file_info = future_to_file[future]
                    try:
                        future.result()
                        success_files.append(file_info)
                    except Exception as e:
                        failed_files.append(file_info)
                        print(f"Error uploading {file_info['name']}: {str(e)}")
                overall_pbar.close()
        self.print_upload_summary(success_files, failed_files, skipped_files)

    def upload_file_safe(self, file_path, directory_path, s3_key="", append_suffix="", file_pbar=None, overall_pbar=None):
        """Uploads a single file and updates the overall progress."""
        file_size = os.path.getsize(file_path)

        try:
            # Pass the file_pbar and overall_pbar to the upload_file method
            self.upload_file(
                file_path,
                directory_path,
                s3_key=s3_key,
                append_suffix=append_suffix,
                file_pbar=file_pbar
            )
            if overall_pbar:
                with self.pbar_lock:
                    overall_pbar.update(file_size)  # Update overall progress bar after the file is uploaded
            if file_pbar:
                with self.pbar_lock:
                    file_pbar.set_postfix({"File": file_path})  # Show which file is being uploaded

        except Exception as e:
            if overall_pbar:
                with self.pbar_lock:
                    overall_pbar.update(file_size)  # Update overall progress in case of error
            if file_pbar:
                with self.pbar_lock:
                    file_pbar.set_postfix({"File": f"Error: {str(e)}"})  # Display error on file p

    def delete_all_files(self, max_workers=10):
        logger.info("Deleting all files in the bucket.")
        self.delete_objects(pattern=None, max_workers=max_workers)

    def delete_objects(self, pattern=None, max_workers=10):
        try:
            if pattern is not None:
                re.compile(pattern)  # Try to compile the regex pattern
        except re.error as e:
            logger.error(f"Invalid regular expression: {e}")
            return

        paginator = self.s3_client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=self.bucket_name)

        # Create a list of objects matching the pattern
        objects_to_delete = []
        for page in page_iterator:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    if pattern is None or re.search(pattern, key):  # Pattern filtering
                        objects_to_delete.append({'Key': key})

        if not objects_to_delete:
            logger.info(f"No files to delete in the bucket. (Pattern: '{pattern or 'all'}')")
            return

        total_files = len(objects_to_delete)

        for i, s3_object in enumerate(extract_values_in_list("Key", objects_to_delete)):
            logger.debug(f"({i}/{total_files}) Found object '{s3_object}'")

        logger.info(f"A total of {total_files} files match the pattern '{pattern or 'all'}' and will be deleted.")

        # Confirm deletion
        confirm = input("Are you sure you want to delete all files? (yes/no): ").strip().lower()
        if confirm != 'yes':
            logger.info("File deletion has been canceled.")
            return

        logger.info(f"Starting deletion of {total_files} files...")

        # Perform deletion using multithreading
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []

            # Batch delete 1000 objects at a time
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i:i + 1000]
                futures.append(
                    executor.submit(self._delete_batch, batch)
                )

            for future in as_completed(futures):
                try:
                    result = future.result()
                    logger.info(f"Deleted: {[obj['Key'] for obj in result]}")
                except Exception as e:
                    logger.info(f"An error occurred during deletion: {e}")

    def _delete_batch(self, batch):
        response = self.s3_client.delete_objects(
            Bucket=self.bucket_name,
            Delete={'Objects': batch}
        )
        return response.get('Deleted', [])

    def print_upload_summary(self, success_files, failed_files, skipped_files):
        """Print a summary of the upload process."""
        total_success = len(success_files)
        total_failed = len(failed_files)
        total_skipped = len(skipped_files)

        pawn.console.rule("Upload Summary:")
        pawn.console.print(f"  Successfully uploaded: {total_success}")
        pawn.console.print(f"  Failed uploads: {total_failed}")
        pawn.console.print(f"  Skipped files (already exist): {total_skipped}")
        pawn.console.print(f"  Total uploaded size: {self.format_size(self.total_uploaded_size)}")

        if success_files:
            pawn.console.rule("Successfully uploaded files:")
            for file_info in success_files:
                pawn.console.print(f"- {file_info['name']}: {self.format_size(file_info['size'])}")
        if failed_files:
            pawn.console.rule("Failed to upload files:")
            for file_info in failed_files:
                pawn.console.print(f"- {file_info['name']}: {self.format_size(file_info['size'])}")
        if skipped_files:
            pawn.console.rule("Skipped files:")
            for file_info in skipped_files:
                pawn.console.print(f"- {file_info['name']}: {self.format_size(file_info['size'])}")

    @staticmethod
    def format_size(size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    def get_file_list(self, directory_path):
        file_list = []
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_list.append({
                    'name': os.path.relpath(file_path, directory_path),
                    'size': os.path.getsize(file_path)
                })
        return file_list

    def calculate_directory_size(self, directory_path):
        total_size = 0
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                total_size += os.path.getsize(file_path)
        return total_size

    def upload_latest_info(self):
        latest_info = {
            "upload_date": datetime.now().isoformat(),
            "files": self.uploaded_files_info,
            "directory": self.directory,
            "append_suffix": self.append_suffix,
            "total_uploaded_size": self.total_uploaded_size
        }
        latest_info_json = json.dumps(latest_info, indent=4)

        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=self.info_file,
            Body=latest_info_json,
            ContentType="application/json"
        )
        print(f"Uploaded latest_info.json to s3://{self.bucket_name}/{self.info_file}")


class Downloader(S3ClientBase):
    def __init__(self, bucket_name, profile_name=None, access_key=None, secret_key=None, endpoint_url=None, overwrite=False, dry_run=False):
        # self.logger = self.get_logger()
        super().__init__(bucket_name, profile_name, access_key, secret_key, endpoint_url, overwrite, dry_run=dry_run)

    def is_s3_file(self,  key):
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except BotoClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                raise

    def is_s3_directory(self, prefix):
        response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix, MaxKeys=1)
        return 'Contents' in response

    def get_object_size(self, s3_key=""):
        """
        Get the size of an S3 object in bytes.

        Args:
            s3_key (str): The key of the object in the S3 bucket.

        Returns:
            int: The size of the object in bytes.

        Raises:
            ValueError: If s3_key is empty.
            botocore.exceptions.ClientError: If the object does not exist or access is denied.
        """
        if not s3_key:
            raise ValueError("The S3 key must be provided to get the object size.")

        try:
            head_object = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            object_size = head_object.get('ContentLength', 0)
            self.logger.debug(f"Size of '{s3_key}' in bucket '{self.bucket_name}': {object_size} bytes")
            return object_size
        except self.s3_client.exceptions.NoSuchKey:
            self.logger.error(f"Object '{s3_key}' does not exist in bucket '{self.bucket_name}'.")
            raise
        except self.s3_client.exceptions.ClientError as e:
            self.logger.error(f"Error retrieving object size for '{s3_key}': {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error while retrieving object size for '{s3_key}': {e}")
            raise


    def print_config(self):
        print(f"Downloader Configuration:")
        print(f"- Bucket Name: {self.bucket_name}")
        print(f"- Overwrite: {self.overwrite}")
        print(f"- Dry Run: {self.dry_run}")


    def download_file(self, s3_key, local_path, overwrite=False):
        """Download a single file from S3."""

        if self.dry_run:
            pawn.console.log(f"[DRY RUN] Would download 's3://{self.bucket_name}/{s3_key}' to '{local_path}'")
            return

        if not overwrite and os.path.exists(local_path):
            print(f"Skipping {local_path}, already exists.")
            return

        extract_directory = os.path.dirname(local_path)
        if extract_directory:
            os.makedirs(extract_directory, exist_ok=True)
        file_size = self.get_object_size(s3_key)

        with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                "[progress.percentage]{task.percentage:>3.1f}%",
                TimeElapsedColumn(),
                " • ",
                # "[progress.filesize]{task.completed}/{task.total}",
                TextColumn("[progress.speed]{task.fields[speed]}"),
        ) as progress:
            task = progress.add_task(f"Downloading {s3_key} [dim]({convert_bytes(file_size)})", total=file_size, speed="0 B/s")

            # def progress_callback(bytes_transferred):
            #     progress.update(task, advance=bytes_transferred)
            progress_callback = ProgressCallback(progress, task, file_size)

            self.s3_client.download_file(
                self.bucket_name, s3_key, local_path,
                Config=self.config,
                Callback=progress_callback
            )

    def download_directory(self, s3_directory, local_path=None, overwrite=False, keep_path=False):
        """Download an entire directory from S3."""
        if local_path is None:
            local_path = os.path.basename(s3_directory)  # Set default local path to the base name of s3_directory

        paginator = self.s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=s3_directory):
            for obj in page.get('Contents', []):
                s3_key = obj['Key']
                base_name = os.path.basename(s3_key)
                relative_path = os.path.relpath(s3_key, start=s3_directory)
                if relative_path.startswith("."):
                    relative_path = relative_path[2:]  # Remove leading "./"
                elif relative_path == "":
                    continue  # Skip if relative path is empty
                if keep_path:
                    local_file_path = os.path.join(local_path, relative_path)
                else:
                    local_file_path = os.path.join(local_path, base_name)
                local_file_path = os.path.normpath(local_file_path)


                if local_file_path and base_name != local_file_path :
                    os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                self.download_file(s3_key, local_file_path, overwrite=overwrite)

    def download_from_info(self, s3_info_key, local_path=None, overwrite=False):
        """Download files as specified in the info.json file from S3."""
        # 먼저 info.json 파일을 S3에서 다운로드하여 로컬에 저장합니다.
        local_info_path = os.path.join("/tmp", os.path.basename(s3_info_key))
        self.download_file(s3_info_key, local_info_path, overwrite=True)

        # info.json 파일을 열어 디렉토리와 파일 목록을 가져옵니다.
        with open(local_info_path, 'r') as f:
            info = json.load(f)
            pawn.console.log(info)

        directory = info.get("directory")
        files = info.get("files", [])

        if not directory or not files:
            sys_exit(f"Error: Invalid info.json file. 'directory' or 'files' field is missing.\n")

        pawn.console.log(f"Starting download for directory {directory} based on info.json...")

        # 로컬 디렉토리 설정
        if local_path:
            local_directory = os.path.join(local_path, directory)
        else:
            local_directory = directory

        # info.json에 정의된 파일들을 다운로드합니다.
        for file_info in files:
            file_name = file_info.get("file_name")
            if file_name:
                # 로컬 경로 설정 (디렉토리 경로와 파일 이름을 합침)
                file_local_path = os.path.join(local_directory, os.path.relpath(file_name, directory))
                self.download_file(file_name, file_local_path, overwrite=overwrite)

        pawn.console.log(f"Download completed for directory {directory}")


class S3Lister(S3ClientBase):
    console = pawn.console

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loop = asyncio.get_event_loop()

        self.aiosession = self.create_aiosession()


    def create_aiosession(self):
        if self.profile_name:
            return aioboto3.Session(profile_name=self.profile_name)
        elif self.access_key and self.secret_key:
            return aioboto3.Session(
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
            )
        return aioboto3.Session()

    async def get_bucket_region(self, s3_client, bucket_name):
        """
        Fetches the region for a given bucket, defaults to 'us-east-1' if None.

        :param s3_client: The S3 client instance to interact with S3.
        :type s3_client: aioboto3.client
        :param bucket_name: The name of the S3 bucket.
        :type bucket_name: str

        :return: The region of the S3 bucket, or 'us-east-1' if not specified.
        :rtype: str
        """
        try:
            response = await s3_client.get_bucket_location(Bucket=bucket_name)
            # If the region is None, it means the bucket is in 'us-east-1'
            return response.get('LocationConstraint') or 'us-east-1'
        except ClientError as e:
            print(f"Error fetching bucket region for {bucket_name}: {e}")
            return None

    async def _list_buckets_async(self, include_size=False):
        """
        Lists all S3 buckets asynchronously, with the option to include their sizes.

        :param include_size: Whether to include the size of each bucket.
        :type include_size: bool

        :return: List of dictionaries containing bucket names and sizes (if requested).
        :rtype: list
        """
        async with self.aiosession.client('s3', endpoint_url=self.endpoint_url) as s3_client:
            response = await s3_client.list_buckets()
            buckets = response.get('Buckets', [])
            bucket_list = []

            if include_size:
                # Progress bar setup
                with Progress(
                        TextColumn("{task.description}"),
                        BarColumn(),
                        TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
                        TimeElapsedColumn(),
                ) as progress:
                    task = progress.add_task("Calculating bucket sizes...", total=len(buckets))

                    for bucket in buckets:
                        bucket_name = bucket['Name']

                        # Fetch region for the bucket
                        region = await self.get_bucket_region(s3_client, bucket_name)
                        if region is None:
                            print(f"Could not determine region for bucket {bucket_name}, skipping...")
                            continue

                        # Calculate size using the region-specific S3 client
                        async with self.aiosession.client('s3', region_name=region) as region_s3_client:
                            progress.update(task, description=f"Calculating size for: {bucket_name}")
                            size = await self.calculate_bucket_size_async(bucket_name, region_s3_client)
                            bucket_list.append({'Name': bucket_name, 'Size': size})
                            progress.update(task, advance=1)
            else:
                bucket_list = [{'Name': bucket['Name']} for bucket in buckets]

            return bucket_list

    def list_buckets(self, include_size=False):
        """
        Returns a list of all S3 buckets, with optional size information.

        :param include_size: Whether to include bucket sizes.
        :type include_size: bool

        :return: List of buckets (and sizes if included).
        :rtype: list
        """
        buckets = self.loop.run_until_complete(self._list_buckets_async(include_size=include_size))
        return buckets

    async def calculate_bucket_size_async(self, bucket_name, s3_client):
        """
        Calculates the total size of an S3 bucket asynchronously.

        :param bucket_name: The name of the bucket to calculate the size for.
        :type bucket_name: str
        :param s3_client: The S3 client instance used to interact with the bucket.
        :type s3_client: aioboto3.client

        :return: The total size of the bucket in bytes.
        :rtype: int
        """
        total_size = 0
        paginator = s3_client.get_paginator('list_objects_v2')

        async for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                total_size += sum(obj['Size'] for obj in page['Contents'])

        return total_size

    def display_buckets(self, include_size=False):
        """
        Displays a table of S3 buckets, with optional size information.

        :param include_size: Whether to display the size of each bucket.
        :type include_size: bool
        """
        buckets = self.list_buckets(include_size=include_size)
        if not buckets:
            self.console.log("No S3 buckets found.")
            return

        table = Table(title="Available S3 Buckets")
        table.add_column("Index", style="cyan")  # Added index column
        table.add_column("Bucket Name", style="cyan")
        if include_size:
            table.add_column("Size", style="magenta")

        for idx, bucket in enumerate(buckets, 1):  # Added enumeration for index
            if include_size:
                size_str = convert_bytes(bucket['Size'])
                table.add_row(str(idx), bucket['Name'], size_str)
            else:
                table.add_row(str(idx), bucket['Name'])

        self.console.print(table)

    async def _ls_async(self, bucket_name="", prefix='', recursive=False):
        """
        Asynchronously lists objects in a specified S3 bucket.

        :param bucket_name: The name of the bucket to list objects from.
        :type bucket_name: str
        :param prefix: Prefix to filter objects by.
        :type prefix: str
        :param recursive: Whether to list objects recursively.
        :type recursive: bool

        :return: A tree structure representing the objects in the bucket.
        :rtype: Tree
        """
        if bucket_name:
            self.bucket_name = bucket_name

        tree = Tree(f"Contents of Bucket: {self.bucket_name}")

        async with self.aiosession.client('s3', endpoint_url=self.endpoint_url) as s3_client:
            await self.list_objects(tree, s3_client, prefix, recursive)

        return tree

    def ls(self, bucket_name="", prefix='', recursive=False, include_size=False):
        """
        Lists objects in a specified S3 bucket or displays all available buckets.

        :param bucket_name: The name of the bucket to list objects from.
        :type bucket_name: str
        :param prefix: Prefix to filter objects by.
        :type prefix: str
        :param recursive: Whether to list objects recursively.
        :type recursive: bool
        :param include_size: Whether to display the size of each bucket.
        :type include_size: bool
        """
        if not bucket_name:
            bucket_name = self.bucket_name

        if bucket_name:
            self.console.rule("Bucket Info")
            tree = self.loop.run_until_complete(self._ls_async(bucket_name, prefix, recursive))
            self.console.print(tree)
        else:
            self.console.rule("Bucket List")
            self.display_buckets(include_size=include_size)

    async def list_objects(self, tree, s3_client, prefix='', recursive=False):
        """
        Asynchronously lists objects in a bucket and adds them to a tree structure.

        :param tree: The tree structure to add the objects to.
        :type tree: Tree
        :param s3_client: The S3 client instance to interact with the bucket.
        :type s3_client: aioboto3.client
        :param prefix: Prefix to filter objects by.
        :type prefix: str
        :param recursive: Whether to list objects recursively.
        :type recursive: bool
        """
        paginator = s3_client.get_paginator('list_objects_v2')

        async for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    size = convert_bytes(obj['Size'])
                    key = obj['Key']
                    # Add the object information to the tree
                    tree.add(f"{key} [dim]{size}[/dim]")

    def display_tree(self, tree):
        """
        Displays the tree structure representing the objects in a bucket.

        :param tree: The tree structure to display.
        :type tree: Tree
        """
        self.console.print(tree)
