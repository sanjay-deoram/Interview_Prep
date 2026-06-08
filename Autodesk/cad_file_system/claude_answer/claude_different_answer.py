"""
CAD File Management System
===========================
In-memory implementation supporting:
  - create_file       : register a new file with its initial content
  - create_version    : append a new version to an existing file
  - get_latest_version: retrieve the most recent version of a file
  - list_versions     : retrieve the full version history of a file

Design decisions, trade-offs, and edge-case analysis are documented in
INTERVIEW_STRATEGY.md alongside this file.

Author note (for interview): I'm using Python 3.10+ features (match/case
available but avoided for broader compatibility). Type hints throughout.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Exceptions  (specific > generic — easier for callers to handle precisely)
# ---------------------------------------------------------------------------

class CADFileSystemError(Exception):
    """Base exception for all CAD file system errors."""


class CADFileNotFoundError(CADFileSystemError):
    """Raised when a file cannot be found by name or ID."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"File not found: '{identifier}'")
        self.identifier = identifier


class FileAlreadyExistsError(CADFileSystemError):
    """Raised when attempting to create a file whose name is already taken."""

    def __init__(self, name: str) -> None:
        super().__init__(f"A file named '{name}' already exists.")
        self.name = name


class NoVersionsError(CADFileSystemError):
    """Raised when version access is attempted on a file with no versions.

    Under normal usage this should be unreachable (create_file always writes
    v1), but we guard against it defensively.
    """

    def __init__(self, name: str) -> None:
        super().__init__(f"File '{name}' has no versions.")
        self.name = name


# ---------------------------------------------------------------------------
# Domain objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FileVersion:
    """
    An immutable snapshot of a file at a point in time.

    Frozen so that historical versions can never be accidentally mutated —
    an important invariant for an audit trail / version history system.

    Attributes:
        version_number: 1-indexed integer. v1 is always the initial creation.
        content:        The file payload. Typed as str here (swap to bytes
                        for real binary CAD data with zero API changes).
        created_at:     UTC timestamp of when this version was saved.
        author:         Optional identifier of who saved this version.
        comment:        Optional human-readable note (e.g. "Added corner fillet").
    """
    version_number: int
    content: str
    created_at: datetime
    author: Optional[str] = None
    comment: Optional[str] = None

    def __repr__(self) -> str:
        author_str = f", author='{self.author}'" if self.author else ""
        comment_str = f", comment='{self.comment}'" if self.comment else ""
        return (
            f"FileVersion(v{self.version_number}"
            f", created_at={self.created_at.isoformat()}"
            f"{author_str}{comment_str})"
        )


@dataclass
class CADFile:
    """
    Represents a CAD file and its complete version history.

    The file's *identity* is its UUID (file_id), not its name. This means:
      - Renames are cheap: update name + the index in CADFileSystem.
      - Any external references (links, logs) use file_id and stay valid
        across renames.

    Invariants:
      - versions is always ordered by version_number ascending.
      - version_number of versions[i] == i + 1  (1-indexed sequential).
      - len(versions) >= 1 after create_file completes.

    Attributes:
        file_id:    Stable UUID string. Never changes after creation.
        name:       Human-readable name. Mutable (rename support).
        created_at: When the file was first registered in the system.
        versions:   Ordered list of FileVersion objects; append-only.
    """
    file_id: str
    name: str
    created_at: datetime
    versions: list[FileVersion] = field(default_factory=list)

    @property
    def latest_version(self) -> FileVersion:
        """O(1) access to the most recent version."""
        if not self.versions:
            raise NoVersionsError(self.name)
        return self.versions[-1]

    @property
    def version_count(self) -> int:
        return len(self.versions)

    def __repr__(self) -> str:
        return (
            f"CADFile(name='{self.name}', id={self.file_id[:8]}…"
            f", versions={self.version_count})"
        )


# ---------------------------------------------------------------------------
# Core system
# ---------------------------------------------------------------------------

class CADFileSystem:
    """
    In-memory CAD file management system.

    Storage layout
    ---------------
    _files_by_id   : Dict[file_id  -> CADFile]   primary store
    _files_by_name : Dict[name     -> file_id ]   secondary index for name lookup

    Both provide O(1) lookup. They must be kept in sync on every mutation
    (create, delete, rename). This is the only place we pay for the dual-index
    — small cost for a large usability win.

    Thread safety
    -------------
    Not implemented here (single-threaded assumption per requirements), but
    the natural extension is a per-file RLock for version creation and a
    global Lock for file creation/deletion. I'd reach for threading.RLock
    and a context manager wrapper.

    Persistence
    -----------
    All data lives in Python dicts. To add persistence, extract a
    StorageBackend ABC and swap in a SQLAlchemy or Redis backend without
    touching the public API.
    """

    def __init__(self) -> None:
        self._files_by_id: dict[str, CADFile] = {}
        self._files_by_name: dict[str, str] = {}   # name -> file_id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_file(
        self,
        name: str,
        content: str,
        author: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> CADFile:
        """
        Register a new file and save its initial content as version 1.

        Args:
            name:    File name. Must be non-empty and unique within the system.
            content: Initial file content. Must not be None.
            author:  Optional. Who is creating the file.
            comment: Optional. Note on the initial version.

        Returns:
            The newly created CADFile object.

        Raises:
            ValueError:            If name is empty/whitespace or content is None.
            FileAlreadyExistsError: If a file with this name already exists.

        Example:
            >>> fs = CADFileSystem()
            >>> f = fs.create_file("assembly.dwg", "<cad data>", author="alice")
            >>> f.version_count
            1
        """
        self._validate_name(name)
        self._validate_content(content)

        if name in self._files_by_name:
            raise FileAlreadyExistsError(name)

        now = _utcnow()
        file_id = str(uuid.uuid4())

        initial_version = FileVersion(
            version_number=1,
            content=content,
            created_at=now,
            author=author,
            comment=comment,
        )

        cad_file = CADFile(
            file_id=file_id,
            name=name,
            created_at=now,
            versions=[initial_version],
        )

        # Commit to both indexes atomically (no partial state)
        self._files_by_id[file_id] = cad_file
        self._files_by_name[name] = file_id

        return cad_file

    def create_version(
        self,
        identifier: str,
        content: str,
        author: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> FileVersion:
        """
        Append a new version to an existing file.

        Args:
            identifier: Either the file's name or its UUID file_id.
            content:    The new version's content. Must not be None.
            author:     Optional. Who is saving this version.
            comment:    Optional. What changed in this version.

        Returns:
            The newly created FileVersion object.

        Raises:
            ValueError:          If content is None.
            CADFileNotFoundError: If no file matches the identifier.

        Example:
            >>> fs = CADFileSystem()
            >>> fs.create_file("part.stp", "v1 data")
            >>> v2 = fs.create_version("part.stp", "v2 data", comment="Chamfer added")
            >>> v2.version_number
            2
        """
        self._validate_content(content)

        cad_file = self._resolve(identifier)

        next_version_number = cad_file.version_count + 1
        new_version = FileVersion(
            version_number=next_version_number,
            content=content,
            created_at=_utcnow(),
            author=author,
            comment=comment,
        )

        cad_file.versions.append(new_version)
        return new_version

    def get_latest_version(self, identifier: str) -> FileVersion:
        """
        Retrieve the most recently saved version of a file.

        Args:
            identifier: Either the file's name or its UUID file_id.

        Returns:
            The FileVersion with the highest version number.

        Raises:
            CADFileNotFoundError: If no file matches the identifier.
            NoVersionsError:      If the file exists but has no versions
                                  (defensive guard; shouldn't occur normally).

        Example:
            >>> fs = CADFileSystem()
            >>> fs.create_file("beam.ipt", "initial")
            >>> fs.create_version("beam.ipt", "updated")
            >>> v = fs.get_latest_version("beam.ipt")
            >>> v.version_number
            2
        """
        cad_file = self._resolve(identifier)
        return cad_file.latest_version  # O(1) via versions[-1]

    def list_versions(self, identifier: str) -> list[FileVersion]:
        """
        Return all versions of a file, ordered from oldest (v1) to newest.

        Returns a *copy* of the internal list so callers can't accidentally
        mutate the version history.

        Args:
            identifier: Either the file's name or its UUID file_id.

        Returns:
            List of FileVersion objects in ascending version order.
            Always contains at least one version.

        Raises:
            CADFileNotFoundError: If no file matches the identifier.

        Example:
            >>> fs = CADFileSystem()
            >>> fs.create_file("frame.dwg", "v1")
            >>> fs.create_version("frame.dwg", "v2")
            >>> versions = fs.list_versions("frame.dwg")
            >>> [v.version_number for v in versions]
            [1, 2]
        """
        cad_file = self._resolve(identifier)
        return list(cad_file.versions)  # defensive copy

    def get_file(self, identifier: str) -> CADFile:
        """
        Retrieve the CADFile metadata object (not a specific version).

        Useful for inspecting file_id, name, created_at, version_count.

        Args:
            identifier: Either the file's name or its UUID file_id.

        Raises:
            CADFileNotFoundError: If no file matches the identifier.
        """
        return self._resolve(identifier)

    def delete_file(self, identifier: str) -> str:
        """
        Permanently remove a file and all its versions from the system.

        After deletion, the file's name becomes available for reuse.

        Args:
            identifier: Either the file's name or its UUID file_id.

        Returns:
            The name of the deleted file (useful for confirmation messages).

        Raises:
            CADFileNotFoundError: If no file matches the identifier.
        """
        cad_file = self._resolve(identifier)

        # Remove from both indexes atomically
        del self._files_by_id[cad_file.file_id]
        del self._files_by_name[cad_file.name]

        return cad_file.name

    def rename_file(self, identifier: str, new_name: str) -> CADFile:
        """
        Rename a file. The file_id (stable identity) does not change.

        Args:
            identifier: Current name or file_id.
            new_name:   Desired new name. Must be non-empty and not in use.

        Raises:
            ValueError:            If new_name is empty/whitespace.
            CADFileNotFoundError:  If no file matches the identifier.
            FileAlreadyExistsError: If new_name is already taken.
        """
        self._validate_name(new_name)
        cad_file = self._resolve(identifier)

        if new_name == cad_file.name:
            return cad_file  # no-op

        if new_name in self._files_by_name:
            raise FileAlreadyExistsError(new_name)

        old_name = cad_file.name
        cad_file.name = new_name

        # Update name index (file_id index doesnt need change)
        del self._files_by_name[old_name]
        self._files_by_name[new_name] = cad_file.file_id

        return cad_file

    def list_files(self) -> list[CADFile]:
        """
        Return all files in the system, sorted by creation time (oldest first).

        Returns:
            List of CADFile objects. Empty list if no files exist.
        """
        return sorted(self._files_by_id.values(), key=lambda f: f.created_at)

    @property
    def file_count(self) -> int:
        """Total number of files in the system."""
        return len(self._files_by_id)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve(self, identifier: str) -> CADFile:
        """
        Look up a CADFile by name or by file_id.

        Strategy: try name index first (most common caller pattern),
        then try ID index. Raises CADFileNotFoundError if neither matches.

        This is the single choke-point for all file lookups — keeps
        error handling DRY and ensures consistent behavior everywhere.
        """
        # Try name first (most common usage pattern)
        if identifier in self._files_by_name:
            file_id = self._files_by_name[identifier]
            return self._files_by_id[file_id]

        # Fall back to ID lookup (for system-internal callers)
        if identifier in self._files_by_id:
            return self._files_by_id[identifier]

        raise CADFileNotFoundError(identifier)

    @staticmethod
    def _validate_name(name: str) -> None:
        """Fail fast on obviously invalid file names."""
        if not name or not name.strip():
            raise ValueError("File name must be a non-empty string.")

    @staticmethod
    def _validate_content(content: str) -> None:
        """Fail fast if content is None (empty string is allowed)."""
        if content is None:
            raise ValueError("File content must not be None.")


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime.

    Centralised here so tests can monkeypatch this one spot if needed.
    """
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _run_tests() -> None:
    """
    Self-contained test suite.

    In a real project this would live in test_cad_file_system.py and run
    via pytest. Inlined here for interview convenience — run this file
    directly to verify correctness.
    """
    import traceback

    passed = 0
    failed = 0

    def check(description: str, condition: bool) -> None:
        nonlocal passed, failed
        status = "✓ PASS" if condition else "✗ FAIL"
        print(f"  {status}: {description}")
        if condition:
            passed += 1
        else:
            failed += 1

    def expect_raises(exc_type, fn, description: str) -> None:
        nonlocal passed, failed
        try:
            fn()
            print(f"  ✗ FAIL: {description} (expected {exc_type.__name__}, got nothing)")
            failed += 1
        except exc_type:
            print(f"  ✓ PASS: {description}")
            passed += 1
        except Exception as e:
            print(f"  ✗ FAIL: {description} (expected {exc_type.__name__}, got {type(e).__name__}: {e})")
            failed += 1

    print("\n" + "="*60)
    print("  CAD File System — Test Suite")
    print("="*60)

    # ------------------------------------------------------------------
    print("\n[1] create_file — happy path")
    fs = CADFileSystem()
    f = fs.create_file("assembly.dwg", "initial cad data", author="alice", comment="first save")
    check("returns CADFile", isinstance(f, CADFile))
    check("name is set", f.name == "assembly.dwg")
    check("has exactly 1 version", f.version_count == 1)
    check("version is v1", f.latest_version.version_number == 1)
    check("content is stored", f.latest_version.content == "initial cad data")
    check("author is stored", f.latest_version.author == "alice")
    check("comment is stored", f.latest_version.comment == "first save")
    check("file_id is a UUID string", len(f.file_id) == 36)
    check("system has 1 file", fs.file_count == 1)

    # ------------------------------------------------------------------
    print("\n[2] create_file — error paths")
    expect_raises(FileAlreadyExistsError,
                  lambda: fs.create_file("assembly.dwg", "duplicate"),
                  "duplicate name raises FileAlreadyExistsError")
    expect_raises(ValueError,
                  lambda: fs.create_file("", "data"),
                  "empty name raises ValueError")
    expect_raises(ValueError,
                  lambda: fs.create_file("   ", "data"),
                  "whitespace-only name raises ValueError")
    expect_raises(ValueError,
                  lambda: fs.create_file("valid.dwg", None),
                  "None content raises ValueError")

    # ------------------------------------------------------------------
    print("\n[3] create_version — happy path")
    v2 = fs.create_version("assembly.dwg", "v2 data", author="bob", comment="chamfer added")
    check("returns FileVersion", isinstance(v2, FileVersion))
    check("version number is 2", v2.version_number == 2)
    check("content is stored", v2.content == "v2 data")
    check("author is stored", v2.author == "bob")
    check("file now has 2 versions", f.version_count == 2)

    v3 = fs.create_version("assembly.dwg", "v3 data")
    check("third version is v3", v3.version_number == 3)
    check("file now has 3 versions", f.version_count == 3)

    # ------------------------------------------------------------------
    print("\n[4] create_version — error paths")
    expect_raises(CADFileNotFoundError,
                  lambda: fs.create_version("nonexistent.dwg", "data"),
                  "nonexistent file raises CADFileNotFoundError")
    expect_raises(ValueError,
                  lambda: fs.create_version("assembly.dwg", None),
                  "None content raises ValueError")

    # ------------------------------------------------------------------
    print("\n[5] get_latest_version")
    latest = fs.get_latest_version("assembly.dwg")
    check("returns FileVersion", isinstance(latest, FileVersion))
    check("returns v3 (most recent)", latest.version_number == 3)
    check("content matches v3", latest.content == "v3 data")

    # Lookup by file_id also works
    latest_by_id = fs.get_latest_version(f.file_id)
    check("lookup by file_id returns same version", latest_by_id.version_number == 3)

    expect_raises(CADFileNotFoundError,
                  lambda: fs.get_latest_version("ghost.dwg"),
                  "nonexistent file raises CADFileNotFoundError")

    # ------------------------------------------------------------------
    print("\n[6] list_versions")
    versions = fs.list_versions("assembly.dwg")
    check("returns list", isinstance(versions, list))
    check("list has 3 versions", len(versions) == 3)
    check("ordered v1, v2, v3", [v.version_number for v in versions] == [1, 2, 3])

    # Mutating the returned list does NOT corrupt internal state
    versions.append(FileVersion(99, "injected", _utcnow()))
    check("internal state not corrupted (defensive copy)", f.version_count == 3)

    expect_raises(CADFileNotFoundError,
                  lambda: fs.list_versions("ghost.dwg"),
                  "nonexistent file raises CADFileNotFoundError")

    # ------------------------------------------------------------------
    print("\n[7] delete_file")
    fs2 = CADFileSystem()
    fs2.create_file("temp.dwg", "data")
    deleted_name = fs2.delete_file("temp.dwg")
    check("delete returns file name", deleted_name == "temp.dwg")
    check("system is now empty", fs2.file_count == 0)
    expect_raises(CADFileNotFoundError,
                  lambda: fs2.get_file("temp.dwg"),
                  "deleted file raises CADFileNotFoundError")

    # Name is freed after deletion — can be reused
    fs2.create_file("temp.dwg", "reborn")
    check("freed name can be reused", fs2.file_count == 1)

    expect_raises(CADFileNotFoundError,
                  lambda: fs2.delete_file("nonexistent.dwg"),
                  "deleting nonexistent file raises CADFileNotFoundError")

    # ------------------------------------------------------------------
    print("\n[8] rename_file")
    fs3 = CADFileSystem()
    original = fs3.create_file("old_name.dwg", "data")
    original_id = original.file_id

    renamed = fs3.rename_file("old_name.dwg", "new_name.dwg")
    check("rename returns updated CADFile", renamed.name == "new_name.dwg")
    check("file_id unchanged after rename", renamed.file_id == original_id)
    check("lookup by new name works", fs3.get_file("new_name.dwg").name == "new_name.dwg")
    expect_raises(CADFileNotFoundError,
                  lambda: fs3.get_file("old_name.dwg"),
                  "old name no longer findable after rename")

    # Self-rename is a no-op (idempotent, not an error)
    same = fs3.rename_file("new_name.dwg", "new_name.dwg")
    check("self-rename is a no-op", same.name == "new_name.dwg")

    # Renaming to a name already owned by a *different* file is an error
    fs3.create_file("another.dwg", "data")
    expect_raises(FileAlreadyExistsError,
                  lambda: fs3.rename_file("new_name.dwg", "another.dwg"),
                  "rename to another existing file's name raises FileAlreadyExistsError")

    # ------------------------------------------------------------------
    print("\n[9] list_files")
    fs4 = CADFileSystem()
    fs4.create_file("c.dwg", "data")
    fs4.create_file("a.dwg", "data")
    fs4.create_file("b.dwg", "data")
    all_files = fs4.list_files()
    check("returns 3 files", len(all_files) == 3)
    check("ordered by creation time", [f.name for f in all_files] == ["c.dwg", "a.dwg", "b.dwg"])

    # ------------------------------------------------------------------
    print("\n[10] single-version edge case")
    fs5 = CADFileSystem()
    fs5.create_file("solo.dwg", "only version")
    latest = fs5.get_latest_version("solo.dwg")
    check("single version: latest is v1", latest.version_number == 1)
    versions = fs5.list_versions("solo.dwg")
    check("single version: list has 1 item", len(versions) == 1)

    # ------------------------------------------------------------------
    print("\n" + "="*60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")

    if failed > 0:
        raise SystemExit(f"{failed} test(s) failed.")


# ---------------------------------------------------------------------------
# Demo / quick usage example
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("\n--- CAD File System Demo ---\n")

    fs = CADFileSystem()

    # Create files
    gear = fs.create_file("gear_assembly.dwg", "<dwg:v1:gear>", author="alice")
    bracket = fs.create_file("mounting_bracket.stp", "<stp:v1:bracket>", author="bob")

    print(f"Created: {gear}")
    print(f"Created: {bracket}")

    # Iterate on the gear design
    fs.create_version("gear_assembly.dwg", "<dwg:v2:gear+teeth>",
                      author="alice", comment="Added 24 teeth profile")
    fs.create_version("gear_assembly.dwg", "<dwg:v3:gear+teeth+bore>",
                      author="charlie", comment="Added centre bore 12mm")

    # Check latest
    latest = fs.get_latest_version("gear_assembly.dwg")
    print(f"\nLatest version of gear_assembly.dwg: {latest}")

    # Full history
    print("\nVersion history for gear_assembly.dwg:")
    for v in fs.list_versions("gear_assembly.dwg"):
        print(f"  {v}")

    # System overview
    print(f"\nTotal files in system: {fs.file_count}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _run_tests()
    _demo()