import os
import json
import boto3
from datetime import datetime
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, DownloadColumn
from boto3.s3.transfer import TransferConfig
from pawnlib.config import pawn
from pawnlib.typing import sys_exit


class Uploader:
    def __init__(self, bucket_name, profile_name=None, overwrite=False, info_file=""):
        if profile_name:
            self.session = boto3.Session(profile_name=profile_name)
        else:
            self.session = boto3.Session()

        self.s3 = self.session.client('s3')
        self.bucket_name = bucket_name
        self.overwrite = overwrite
        self.uploaded_files_info = []
        self.directory = ""
        self.append_suffix = ""
        self.total_uploaded_size = 0
        self.info_file = info_file

        # TransferConfig 설정
        self.config = TransferConfig(
            multipart_threshold=256 * 1024 * 1024,  # 멀티파트 업로드를 시작하는 파일 크기 (256MB)
            max_concurrency=20,  # 멀티스레딩 동시 처리 수
            multipart_chunksize=16 * 1024 * 1024,  # 멀티파트 업로드를 위한 청크 크기 (16MB)
            use_threads=True  # 멀티스레딩 활성화
        )

    def upload_directory(self, directory_path, append_suffix="", info_file=""):
        if not os.path.isdir(directory_path):
            raise ValueError(f"The directory {directory_path} does not exist or is not a directory.")

        if info_file:
            self.info_file = info_file

        total_size = self.calculate_directory_size(directory_path)
        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.1f}%",
            TimeElapsedColumn(),
            " • ",
            "[progress.filesize]{task.completed}/{task.total}",
        )

        with progress:
            task = progress.add_task(f"Uploading {directory_path}", total=total_size)
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    self.upload_file(file_path, directory_path, progress, task, append_suffix=append_suffix)

        if self.info_file:
            self.upload_latest_info()

    def upload_file(self, file_path="", directory_path="", progress="", task="", append_suffix=""):
        if file_path.endswith('.sock'):
            progress.console.log(f"Skipping .sock file: {file_path}")
            return

        relative_path = os.path.relpath(file_path, directory_path)

        parts = directory_path.split(os.sep)
        if append_suffix and parts:
            parts[0] += append_suffix
        base_dir = os.path.join(*parts)

        s3_key = os.path.join(base_dir, relative_path).replace("\\", "/")
        try:
            if not self.overwrite:
                try:
                    self.s3.head_object(Bucket=self.bucket_name, Key=s3_key)
                    progress.console.log(f"Skipping {s3_key}, already exists.")
                    return
                except self.s3.exceptions.ClientError:
                    pass

            progress.console.log(f"Uploading {file_path} to s3://{self.bucket_name}/{s3_key}")

            def progress_callback(bytes_transferred):
                progress.update(task, advance=bytes_transferred)

            self.s3.upload_file(
                file_path, self.bucket_name, s3_key,
                Config=self.config,  # 개선된 TransferConfig 사용
                Callback=progress_callback
            )

            file_info = {
                "file_name": s3_key,
                "size": os.path.getsize(file_path),
                "upload_time": datetime.now().isoformat()
            }
            self.total_uploaded_size += file_info["size"]
            self.uploaded_files_info.append(file_info)
        except Exception as e:
            progress.console.log(f"Error uploading {file_path}: {str(e)}")


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

        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=self.info_file,
            Body=latest_info_json,
            ContentType="application/json"
        )
        print(f"Uploaded latest_info.json to s3://{self.bucket_name}/{self.info_file}")


class Downloader:
    def __init__(self, profile_name=None, bucket_name=None, overwrite=False):
        if profile_name:
            self.session = boto3.Session(profile_name=profile_name)
        else:
            self.session = boto3.Session()

        self.s3 = self.session.client('s3')
        self.bucket_name = bucket_name
        self.overwrite = overwrite

        # TransferConfig 설정
        self.config = TransferConfig(
            use_threads=True,
            max_concurrency=10,
            multipart_threshold=8 * 1024 * 1024,  # 8MB
            multipart_chunksize=8 * 1024 * 1024  # 8MB
        )

    def download_file(self, s3_key, local_path, overwrite=False):
        """Download a single file from S3."""
        if not overwrite and os.path.exists(local_path):
            print(f"Skipping {local_path}, already exists.")
            return

        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        # S3 객체의 파일 크기를 가져옵니다.
        head_object = self.s3.head_object(Bucket=self.bucket_name, Key=s3_key)
        file_size = head_object['ContentLength']

        # print(f"Downloading {s3_key} to {local_path}...")

        with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                "[progress.percentage]{task.percentage:>3.1f}%",
                TimeElapsedColumn(),
                " • ",
                "[progress.filesize]{task.completed}/{task.total}",
        ) as progress:
            task = progress.add_task(f"Downloading {s3_key}", total=file_size)

            def progress_callback(bytes_transferred):
                progress.update(task, advance=bytes_transferred)

            self.s3.download_file(
                self.bucket_name, s3_key, local_path,
                Config=self.config,
                Callback=progress_callback
            )

    def download_directory(self, s3_directory, local_path=None, overwrite=False):
        """Download an entire directory from S3."""
        if local_path is None:
            local_path = s3_directory

        paginator = self.s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=s3_directory):
            for obj in page.get('Contents', []):
                s3_key = obj['Key']
                relative_path = os.path.relpath(s3_key, s3_directory)
                local_file_path = os.path.join(local_path, relative_path)
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
