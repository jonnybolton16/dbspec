"""DBSpec loader utilities.

Utilities for loading DBSpec files. Files are discovered and read by the
loader, with their content passed to the parser.
"""

from collections import Counter
from enum import StrEnum
from pathlib import Path

from dbspec.errors import (
    DBSpecError,
    DBSpecFileError,
    DBSpecLoadError,
    DBSpecModelError,
)
from dbspec.models import Database, DBSpecFileModel, Table
from dbspec.parser import parse_dbspec_file


class SymlinkPolicy(StrEnum):
    """Symlink-handling policies."""

    FOLLOW = "follow"
    IGNORE = "ignore"
    RAISE = "raise"


def _quote(path: Path) -> str:
    """Quote a path for error messages."""
    return repr(str(path))


def _reraise_walk_error(e: OSError) -> None:
    """Reraise a directory-traversal OSError as a DBSpecLoadError."""
    msg = f"Error traversing directory: {e}"
    raise DBSpecLoadError(msg) from e


def _resolve_or_raise(path: Path) -> Path:
    """Resolve a path, or raise if it cannot be resolved.

    Use a bespoke error message if the path itself is missing, or if it
    is a dangling symlink.

    Raises:
      DBSpecLoadError: If the path cannot be resolved.
    """
    try:
        return path.resolve(strict=True)
    except FileNotFoundError as e:
        target = "Symlink target" if path.is_symlink() else "Path"
        msg = f"{target} not found: {_quote(path)}"
        raise DBSpecLoadError(msg) from e
    except OSError as e:
        msg = f"Could not resolve path {_quote(path)}: {e}"
        raise DBSpecLoadError(msg) from e


def load_database(path: str | Path, symlink_policy: SymlinkPolicy) -> Database:
    """Load DBSpec files from the given path into a database model.

    If `path` is a single file, it must have a `.dbspec` extension.

    If `path` is a directory, all `.dbspec` files below it are loaded.

    If `path` is a symlink, it is always followed, with its target
    loaded. However, symlinks encountered during directory traversal are
    not necessarily followed; `symlink_policy` determines how they are
    handled.

    If file-level errors are encountered, loading continues for the
    remaining files, and all errors are collected and raised together.

    Raises:
      DBSpecLoadError: If
       - the path does not exist, or cannot be resolved or traversed
       - no DBSpec files are found at the path
       - one or more DBSpec files cannot be processed
       - database-level validation or construction fails
    """
    # convert str path to Path, if necessary
    path = Path(path)

    # handle missing paths, and resolve explicitly-specified symlinks
    requested_path = path
    path = _resolve_or_raise(requested_path)

    # initialise model and error collections
    models: list[DBSpecFileModel] = []
    errors: list[DBSpecError] = []

    def collect_file(filepath: Path) -> None:
        try:
            models.append(parse_dbspec_file(filepath))
        except DBSpecFileError as e:
            errors.append(e)

    # handle single file
    if path.is_file():
        if path.suffix != ".dbspec":
            msg = f"Not a .dbspec file: {_quote(requested_path)}"
            raise DBSpecLoadError(msg)
        collect_file(path)

    # handle directory
    elif path.is_dir():
        visited_dirs: set[Path] = set()
        for dirpath, subdirs, filenames in path.walk(
            on_error=_reraise_walk_error,
            follow_symlinks=symlink_policy == SymlinkPolicy.FOLLOW,
        ):
            # handle infinite directory symlink recursion
            if symlink_policy == SymlinkPolicy.FOLLOW:
                # get a single canonical directory path in case we've
                # already reached this directory from a different source
                resolved_dirpath = _resolve_or_raise(dirpath)

                # skip directories we've already visited
                if resolved_dirpath in visited_dirs:
                    subdirs.clear()  # skip subdirectories
                    continue  # skip files
                visited_dirs.add(resolved_dirpath)

            # process each file in the directory
            for filename in filenames:
                filepath = dirpath / filename

                # handle unresolved file symlinks
                if filepath.is_symlink():
                    if symlink_policy == SymlinkPolicy.FOLLOW:
                        # resolve the symlink, skipping if not a file
                        filepath = _resolve_or_raise(filepath)
                    elif symlink_policy == SymlinkPolicy.IGNORE:
                        # ignore the symlink
                        continue
                    elif symlink_policy == SymlinkPolicy.RAISE:
                        # raise
                        msg = (
                            "Symlink encountered while traversing directory: "
                            + _quote(filepath.relative_to(path))
                        )
                        raise DBSpecLoadError(msg)

                # skip non-.dbspec files, and other non-regular files
                if filepath.is_file() and filepath.suffix == ".dbspec":
                    collect_file(filepath)

    # handle neither
    else:
        msg = f"Path is not a file or directory: {_quote(path)}"
        raise DBSpecLoadError(msg)

    # TODO: db-level validation:
    #  no duplicate tables
    #  foreign-key reference targets exist, and columns form primary key/unique
    #  foreign-keys have matching column data types
    #  others?

    # raise errors before building the database
    if errors:
        raise DBSpecLoadError(errors)
    if not models:
        msg = "No .dbspec files found"
        raise DBSpecLoadError(msg)

    # build database
    database = Database()
    for model in models:
        if isinstance(model, Table):
            database.add_table(model)
        else:
            msg = f"Database loading not implemented for {type(model).__name__}"
            raise NotImplementedError(msg)

    return database
