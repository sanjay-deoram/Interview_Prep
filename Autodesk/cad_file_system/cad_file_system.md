# Cad File System

Problem Statement:

We're building a simple CAD file management system.

Users work on CAD files and save new versions of those files over time.

Please implement a system that supports the following operations:

- Create a file
- Create a new version of an existing file
- Retrieve the latest version of a file
- List all versions of a file

## My Initial Thinking

Requirements:

- Create file, create new version of a existing file, retrieve latest version of a file, list all version of a file.

Assumptions:

- When creating a FILE is it safe to assume that it HAS to be a .cad file?
- If a latest verison of that file doesnt exist, then we return 404 not found. - For versioning is it safe to add the verision number at the end? eg: original file would be doc.cad then new version would be doc_v1.cad, doc_v2.cad.

Edge Cases:

Questions:

- If a user tries to create a new version of a file, and the file doesnt exist, should we create a new file?
- There could be conflicts within a file, i'm assuming that 2 files CANNOT have the same name.
