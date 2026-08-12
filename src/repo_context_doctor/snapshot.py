"""Bounded, symlink-free repository discovery and controlled text reads."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from repo_context_doctor.privacy import is_sensitive_path

EXCLUDED_DIRECTORIES = {
    ".git",
    ".hg",
    ".idea",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "htmlcov",
    "node_modules",
    "out",
    "target",
    "vendor",
    "venv",
}


@dataclass(frozen=True, slots=True)
class ScanLimits:
    max_depth: int = 10
    max_entries: int = 20_000
    max_file_bytes: int = 256 * 1024


@dataclass(slots=True)
class RepositorySnapshot:
    root: Path
    limits: ScanLimits
    files: dict[str, Path] = field(default_factory=dict)
    directories: set[str] = field(default_factory=set)
    symlinks_skipped: list[str] = field(default_factory=list)
    sensitive_files: set[str] = field(default_factory=set)
    oversized_files: set[str] = field(default_factory=set)
    undecodable_files: set[str] = field(default_factory=set)
    read_errors: dict[str, str] = field(default_factory=dict)
    discovery_errors: list[str] = field(default_factory=list)
    depth_limited: bool = False
    entry_limited: bool = False
    entries_seen: int = 0

    @property
    def lower_files(self) -> dict[str, str]:
        return {path.lower(): path for path in self.files}

    def has_file(self, relative: str) -> bool:
        return relative.replace("\\", "/").lower() in self.lower_files

    def actual_path(self, relative: str) -> str | None:
        return self.lower_files.get(relative.replace("\\", "/").lower())

    def has_directory(self, relative: str) -> bool:
        wanted = relative.replace("\\", "/").strip("/").lower()
        return any(path.lower() == wanted for path in self.directories)

    def read_text(self, relative: str, *, max_bytes: int | None = None) -> str | None:
        """Read one discovered non-sensitive file as UTF-8 without following links."""

        actual = self.actual_path(relative)
        if actual is None:
            return None
        if actual in self.sensitive_files:
            return None

        path = self.files[actual]
        limit = min(max_bytes or self.limits.max_file_bytes, self.limits.max_file_bytes)
        try:
            if path.stat(follow_symlinks=False).st_size > limit:
                self.oversized_files.add(actual)
                return None
            data = path.read_bytes()
        except OSError as exc:
            self.read_errors[actual] = type(exc).__name__
            return None

        if len(data) > limit:
            self.oversized_files.add(actual)
            return None
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            self.undecodable_files.add(actual)
            return None


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def discover_repository(root: Path, *, limits: ScanLimits | None = None) -> RepositorySnapshot:
    """Discover bounded repository metadata without following symlinks."""

    resolved = root.resolve(strict=True)
    if not resolved.is_dir():
        raise NotADirectoryError(str(root))

    snapshot = RepositorySnapshot(root=resolved, limits=limits or ScanLimits())
    stack: list[tuple[Path, int]] = [(resolved, 0)]

    while stack:
        directory, depth = stack.pop()
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name.lower())
        except OSError as exc:
            relative = "." if directory == resolved else _relative(resolved, directory)
            snapshot.discovery_errors.append(f"{relative}: {type(exc).__name__}")
            continue

        for entry in entries:
            snapshot.entries_seen += 1
            if snapshot.entries_seen > snapshot.limits.max_entries:
                snapshot.entry_limited = True
                stack.clear()
                break

            path = Path(entry.path)
            relative = _relative(resolved, path)
            try:
                if entry.is_symlink():
                    snapshot.symlinks_skipped.append(relative)
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if entry.name.lower() in EXCLUDED_DIRECTORIES:
                        continue
                    snapshot.directories.add(relative)
                    if depth >= snapshot.limits.max_depth:
                        snapshot.depth_limited = True
                    else:
                        stack.append((path, depth + 1))
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
            except OSError as exc:
                snapshot.discovery_errors.append(f"{relative}: {type(exc).__name__}")
                continue

            snapshot.files[relative] = path
            if is_sensitive_path(path):
                snapshot.sensitive_files.add(relative)

    return snapshot
