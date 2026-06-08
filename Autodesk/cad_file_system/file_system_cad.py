from dataclasses import dataclass
import datetime
from typing import List


class Version:
    def __init__(self, id) -> None:
        self.id = id
        self.created_at = datetime.datetime.now()


@dataclass
class File:
    def __init__(
        self,
        name: str,
    ) -> None:
        self.name: str = ""
        self.versions: List[Version] = []

    def list_verisons(self,file_name: str):
        for v in self.versions:
            print(f"File name: {file_name} Version: {v.id} | created at: {v.created_at}")


class FileManager:
    def __init__(self) -> None:
        self.files: dict[str:File] = {}

    def create_file(self, file_name):
        """Creates a brand new file"""
        if self.file_exists(file_name):
            raise Exception(f"{file_name} already exists")

        self.files[file_name] = File(name=file_name)
        return f"{file_name} created sucessfully"

    def create_new_version(self, file_name: str):
        """Creates a new version of a file"""
        if not self.file_exists(file_name):
            raise Exception("File does not exist")

        file = self.files[file_name]
        latest_version = len(file.versions) + 1
        file.versions.append(Version(id=latest_version))
        return f"{file_name} version: {latest_version} created succesfully"

    def list_all_verisons(self, file_name):
        if not self.file_exists(file_name):
            raise Exception("File does not exists")

        file: File = self.files[file_name]
        file.list_verisons(file_name)

    def file_exists(self, file_name) -> bool:
        """Check if this file exists in files"""

        if not file_name:
            raise Exception("Please provide file name")

        if file_name in self.files:
            return True

        return False

    def list_all_files(self):
        for f in self.files:
            print(f.__str__())


file_manager = FileManager()

file_manager.create_file("document1.cad")
file_manager.create_file("document2.cad")

file_manager.list_all_files()

file_manager.create_new_version("document1.cad")
file_manager.list_all_verisons("document1.cad")
