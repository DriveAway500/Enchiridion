# SPDX-License-Identifier: GPL-3.0-only
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, TypeAlias

logger = logging.getLogger(__name__)

# JSON object keys are always strings, so dict[str, Any] is the accurate type.
JSONRecords: TypeAlias = list[dict[str, Any]]


class JSONHandlerError(Exception):
    """Base error for JSON operations."""


class InvalidPathError(JSONHandlerError):
    """Invalid path (wrong extension)."""


class JSONLoadError(JSONHandlerError):
    """Failed to read or decode the JSON file."""


class JSONValidationError(JSONHandlerError):
    """The JSON content is not a list of objects (list[dict])."""


class JSONSaveError(JSONHandlerError):
    """Failed to serialize or write the JSON file."""


class JSONHandler:
    @staticmethod
    def _validate_extension(path: Path) -> None:
        if path.suffix.lower() != ".json":
            raise InvalidPathError(f"Invalid extension for JSON file: {path}")

    @staticmethod
    def _validate_records(data: Any, source: str) -> JSONRecords:
        """Ensure ``data`` is a list of dicts.

        Raises:
            JSONValidationError: if ``data`` is not a list, or if any item
                in the list is not a dict.
        """
        if not isinstance(data, list):
            raise JSONValidationError(
                f"Expected a list in {source}, got {type(data).__name__}"
            )

        for index, item in enumerate(data):
            if not isinstance(item, dict):
                raise JSONValidationError(
                    f"Expected a dict at index {index} in {source}, "
                    f"got {type(item).__name__}"
                )

        return data

    @staticmethod
    def load(file_path: str | os.PathLike[str]) -> JSONRecords:
        """Read a JSON file and return its content as ``list[dict]``.

        Raises:
            InvalidPathError: if the extension is not ``.json``.
            JSONLoadError: if the file is missing, unreadable, or malformed.
            JSONValidationError: if the content is not a list of dicts.
        """
        path = Path(file_path)
        JSONHandler._validate_extension(path)

        try:
            logger.info("Loading JSON from %s", path)
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError as exc:
            logger.error("Malformed JSON in %s: %s", path, exc)
            raise JSONLoadError(f"Malformed JSON in {path}: {exc}") from exc
        except OSError as exc:
            logger.error("I/O error while reading %s: %s", path, exc)
            raise JSONLoadError(f"Could not read {path}: {exc}") from exc

        try:
            return JSONHandler._validate_records(data, str(path))
        except JSONValidationError as exc:
            logger.error("Invalid JSON structure: %s", exc)
            raise

    @staticmethod
    def save(
        file_path: str | os.PathLike[str],
        data: JSONRecords,
        *,
        indent: int = 4,
        base_dir: str | os.PathLike[str] | None = None,
            ) -> None:
        """Atomically write ``data`` to ``file_path`` as JSON.

        * validates that ``data`` is a list of dicts
        * validates the file extension
        * resolves the path
        * creates missing directories
        * writes to a temporary file and swaps it in with ``os.replace``

        Raises:
            JSONValidationError: if ``data`` is not a list of dicts.
            InvalidPathError: if the extension is invalid.
            JSONSaveError: if the data is not serializable or an I/O error occurs.
        """
        target = Path(file_path).resolve()
        JSONHandler._validate_extension(target)
        JSONHandler._validate_records(data, "data to save")

        directory = target.parent
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.error("Failed to create directory %s: %s", directory, exc)
            raise JSONSaveError(f"Could not create directory {directory}: {exc}") from exc

        temp_path: Path | None = None  # only used for cleanup in `finally`
        try:
            with tempfile.NamedTemporaryFile(
                "w", delete=False, dir=directory, encoding="utf-8", suffix=".tmp"
            ) as tmp:
                tmp_file = Path(tmp.name)  # always a Path, never None
                temp_path = tmp_file
                json.dump(data, tmp, indent=indent, ensure_ascii=False)
                tmp.flush()
                os.fsync(tmp.fileno())

            os.replace(tmp_file, target)
            temp_path = None  # already moved, nothing to clean up
            logger.info("JSON saved to %s", target)

        except (TypeError, ValueError) as exc:
            logger.error("Data is not JSON serializable (%s): %s", target, exc)
            raise JSONSaveError(f"Data is not JSON serializable: {exc}") from exc
        except OSError as exc:
            logger.error("I/O error while writing %s: %s", target, exc)
            raise JSONSaveError(f"Could not write {target}: {exc}") from exc
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    logger.warning("Could not remove temporary file %s", temp_path)