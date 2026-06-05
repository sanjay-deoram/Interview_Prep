from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Version:
    version_number: int
    content: str
    created_at: datetime
    author: Optional[str] = None
    description: Optional[str] = None

    def __repr__(self) -> str:
        desc = f" — {self.description}" if self.description else ""
        author = f" by {self.author}" if self.author else ""
        return f"v{self.version_number}{author}{desc} ({self.created_at.strftime('%Y-%m-%d %H:%M:%S')})"


@dataclass
class CADFile:
    name: str
    created_at: datetime
    versions: list[Version] = field(default_factory=list)


class CADFileSystem:
    """
    In-memory CAD file management system.

    Files are keyed by name (case-sensitive, globally unique).
    Each file maintains an ordered list of versions; version numbers
    are auto-incremented integers starting at 1.
    Creating a file atomically creates version 1.
    """

    def __init__(self) -> None:
        self._files: dict[str, CADFile] = {}

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def create_file(
        self,
        name: str,
        content: str = "",
        author: Optional[str] = None,
        description: Optional[str] = None,
    ) -> CADFile:
        """Create a new file. Atomically creates version 1."""
        self._validate_name(name)
        if name in self._files:
            raise FileExistsError(f"File '{name}' already exists")

        now = datetime.now()
        initial_version = Version(
            version_number=1,
            content=content,
            created_at=now,
            author=author,
            description=description,
        )
        cad_file = CADFile(name=name, created_at=now, versions=[initial_version])
        self._files[name] = cad_file
        return cad_file

    def create_version(
        self,
        name: str,
        content: str,
        author: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Version:
        """Append a new version to an existing file."""
        file = self._get_file(name)
        next_num = len(file.versions) + 1
        new_version = Version(
            version_number=next_num,
            content=content,
            created_at=datetime.now(),
            author=author,
            description=description,
        )
        file.versions.append(new_version)
        return new_version

    def get_latest_version(self, name: str) -> Version:
        """Return the most recent version of a file. O(1)."""
        file = self._get_file(name)
        return file.versions[-1]

    def list_versions(self, name: str) -> list[Version]:
        """Return all versions of a file in chronological order."""
        file = self._get_file(name)
        return list(file.versions)

    def list_files(self) -> list[str]:
        """Return names of all files in the system."""
        return list(self._files.keys())

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _get_file(self, name: str) -> CADFile:
        self._validate_name(name)
        if name not in self._files:
            raise FileNotFoundError(f"File '{name}' does not exist")
        return self._files[name]

    @staticmethod
    def _validate_name(name: str) -> None:
        if not name or not name.strip():
            raise ValueError("File name must be a non-empty string")


# ------------------------------------------------------------------ #
# Demo / manual test
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    fs = CADFileSystem()

    # Create two files
    fs.create_file("chassis.cad", content="<geometry v1>", author="alice", description="Initial chassis geometry")
    fs.create_file("bracket.cad", content="<bracket v1>", author="bob")

    print("=== All files ===")
    for f in fs.list_files():
        print(f"  {f}")

    # Add versions to chassis.cad
    fs.create_version("chassis.cad", content="<geometry v2>", author="alice", description="Rounded edges")
    fs.create_version("chassis.cad", content="<geometry v3>", author="carol", description="Weight reduction pass")

    print("\n=== All versions of chassis.cad ===")
    for v in fs.list_versions("chassis.cad"):
        print(f"  {v}")

    print("\n=== Latest version of chassis.cad ===")
    print(f"  {fs.get_latest_version('chassis.cad')}")

    print("\n=== Latest version of bracket.cad ===")
    print(f"  {fs.get_latest_version('bracket.cad')}")

    # Edge cases
    print("\n=== Edge cases ===")

    try:
        fs.create_file("chassis.cad")
    except FileExistsError as e:
        print(f"  Duplicate file blocked: {e}")

    try:
        fs.get_latest_version("nonexistent.cad")
    except FileNotFoundError as e:
        print(f"  Missing file blocked: {e}")

    try:
        fs.create_file("")
    except ValueError as e:
        print(f"  Empty name blocked: {e}")
