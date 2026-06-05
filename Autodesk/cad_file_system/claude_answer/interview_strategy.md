# Autodesk Interview: CAD File Management System

## How to Ace This Interview

---

## Phase 1: Clarifying Questions (First 5–10 minutes)

Before writing a single line of code, ask these questions. Interviewers at companies like Autodesk
reward candidates who think like engineers, not typists. Silence here is a red flag.

### About the File Model
- "When we say 'create a file', are we storing actual binary content, or are we treating
  content as an opaque string/blob for now?"
- "Are file names unique? Is the namespace global or per-user?"
- "Are file names case-sensitive? (`Drawing.cad` vs `drawing.cad`)"
- "Should file names be restricted to `.cad` extension, or is this system extension-agnostic?"

### About Versioning
- "When a file is first created, does that implicitly create version 1? Or is the file created
  empty and you must call 'create version' separately?"
- "Is versioning linear (1, 2, 3...) or do we need to support branching (like Git)?"
- "Can a version be deleted? Can a file be deleted?"
- "Is there metadata attached to a version — author, description/commit message, timestamp?"

### About Retrieval
- "Can users retrieve a *specific* version by number, or only the latest?"
- "What should happen if `get_latest_version` is called on a file with no versions?"

### About Scale and Concurrency
- "Is this single-user or multi-user? Do we need to worry about concurrent writes to the same file?"
- "How many files and versions are we expecting? (Guides data structure choices)"

---

## Assumptions Made (State these out loud before coding)

Based on a typical response from the interviewer, assume:

1. File names are **unique, case-sensitive strings** (no extension enforcement).
2. Creating a file **creates version 1 atomically** — a file always has at least one version.
3. Versioning is **linear, auto-incremented integers** (1, 2, 3...).
4. Content is an **opaque string** (no binary concern for now).
5. Version metadata includes: `version_number`, `content`, `created_at`, optional `author`
   and `description`.
6. No deletion operations needed (out of scope for now).
7. **Single-threaded** for this session — note thread safety as a follow-up.
8. Everything **in-memory** — no persistence layer.

---

## Design Walkthrough (Talk through this before coding)

### Data Structures

**Core storage:** `Dict[str, CADFile]` — a hash map keyed by file name.

- `O(1)` average-case lookup, insert, and existence check.
- Files don't need to be ordered globally, so a dict is preferred over a list.

**Per-file version storage:** `List[Version]` — an ordered list of versions.

- Append is `O(1)`.
- "Latest version" is always `versions[-1]` — `O(1)`, no scanning needed.
- "List all versions" is `O(n)` where `n` = number of versions for that file.
- Version number is deterministic: `len(versions) + 1` before append.

**Why not a dict for versions?**
Versions are sequential integers starting at 1. A list gives us index-based access,
ordered traversal, and O(1) append. A dict would waste overhead and add no benefit
for this access pattern.

### Class Structure

```
CADFileSystem          ← the main interface / entry point
    _files: dict       ← internal state

CADFile                ← represents a named file and its version history
    name: str
    created_at: datetime
    versions: List[Version]

Version                ← a snapshot of a file at a point in time
    version_number: int
    content: str
    created_at: datetime
    author: Optional[str]
    description: Optional[str]
```

Using `@dataclass` for `Version` and `CADFile` gives us free `__repr__` and clean
construction — makes debugging output readable in an interview setting.

---

## Edge Cases to Handle

| Scenario | Behavior |
|---|---|
| `create_file("foo.cad")` called twice | Raise `FileExistsError` |
| `create_version("nonexistent.cad", ...)` | Raise `FileNotFoundError` |
| `get_latest_version("nonexistent.cad")` | Raise `FileNotFoundError` |
| `list_versions("nonexistent.cad")` | Raise `FileNotFoundError` |
| `create_file("")` or `None` file name | Raise `ValueError` |
| File created with empty string content | Valid — content is optional |
| `get_latest_version` on a file with versions | Returns last element of list |

---

## Complexity Analysis

| Operation | Time | Space |
|---|---|---|
| `create_file` | O(1) avg | O(1) new file entry |
| `create_version` | O(1) | O(1) new version entry |
| `get_latest_version` | O(1) | O(1) |
| `list_versions` | O(k) where k = # versions | O(k) for the copy returned |
| `list_files` | O(n) where n = # files | O(n) |

**Overall space:** O(F × V) where F = total files, V = average versions per file.

---

## Tradeoffs and Design Decisions

### 1. Storing full content per version vs. diffs
**Chose:** Full content per version.

- **Pro:** Simple to implement, O(1) retrieval of any version's content.
- **Con:** High memory usage if content is large (CAD files can be gigabytes).
- **Real-world:** A production system would store diffs or binary deltas and reconstruct
  on read — but that adds significant complexity not warranted in a 1-hour interview.

### 2. Auto-increment version numbers vs. timestamps vs. hashes
**Chose:** Auto-increment integers.

- **Pro:** Predictable, human-readable, deterministic.
- **Con:** In a distributed/concurrent system, two concurrent writes could get the same number.
- **Real-world:** Use UUIDs or content-addressed hashing (like Git's SHA) for distributed systems.

### 3. Raising exceptions vs. returning None / sentinel values
**Chose:** Raising typed exceptions (`FileNotFoundError`, `FileExistsError`).

- **Pro:** Caller is forced to handle the error explicitly. Pythonic. Matches stdlib conventions.
- **Con:** Slightly more verbose call sites.
- **Alternative:** Return `Optional[...]` and `None` on failure — simpler but silently swallowable.

### 4. Returning copies vs. references from `list_versions`
**Chose:** Return a copy (`list(self._files[name].versions)`).

- **Pro:** Caller cannot mutate the internal list — protects invariants.
- **Con:** O(k) copy cost each call.
- **Alternative:** Return a read-only view — overkill for this scope.

### 5. First version created at file creation vs. separate call
**Chose:** File creation atomically creates version 1.

- **Reason:** A file with no versions is a meaningless intermediate state. This
  eliminates a class of bugs and simplifies the API.

---

## What This Design Does NOT Handle (Follow-up Conversation)

These are great things to proactively mention — shows you think beyond the prompt:

1. **Thread safety** — `dict` and `list` operations are not atomic. A `threading.Lock`
   per file (or a `RWLock`) would be needed for concurrent access.

2. **Persistence** — all state is lost on process exit. A real system would serialize to
   disk (SQLite, a file-based store, or a proper database).

3. **Version branching** — what if two engineers fork from v3 independently? Linear versioning
   breaks down. Would need a tree structure (like Git's DAG).

4. **Large content / binary files** — CAD files are large. Content should not live in-memory
   as strings; content-addressed storage (store by hash, retrieve by hash) is standard.

5. **Soft deletes** — marking files/versions as deleted without actually removing data,
   for audit trails and recovery.

6. **Access control** — who can write to a file? Who can read it?

7. **Search** — find files by name pattern, by author, by date range.

---

## How to Present in the Interview

1. **Restate the problem** in your own words — confirms understanding.
2. **Ask clarifying questions** from Phase 1 above — 3–5 focused ones.
3. **State assumptions out loud** — "I'll assume file names are unique and case-sensitive."
4. **Sketch the data structures** in comments or verbally before writing logic.
5. **Write the models first** (`Version`, `CADFile`), then the system class.
6. **Test with a quick driver** — creates a file, adds versions, retrieves latest, lists all.
7. **Proactively call out limitations** — shows senior-level thinking.

The interviewer is not just evaluating the code. They're evaluating:
- Do you ask the right questions?
- Do you communicate your reasoning clearly?
- Do you anticipate edge cases?
- Do you know when to keep it simple vs. when to add complexity?
