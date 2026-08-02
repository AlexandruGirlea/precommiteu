from __future__ import annotations

import fnmatch
import os
import pathlib
from collections.abc import Iterable
from dataclasses import dataclass

CODE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".ipynb",
        ".java",
        ".ts",
        ".tsx",
        ".mts",
        ".cts",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".go",
        ".cs",
        ".php",
        ".c",
        ".h",
        ".kt",
        ".kts",
        ".rs",
        ".cpp",
        ".cc",
        ".cxx",
        ".hpp",
        ".hh",
        ".hxx",
        ".tf",
        ".tfvars",
        ".hcl",
        ".swift",
        ".scala",
        ".sc",
        ".rb",
    }
)

PROSE_EXTENSIONS: frozenset[str] = frozenset(
    {".md", ".rst", ".txt", ".adoc", ".org", ".tex", ".log"}
)

CODE_FILENAMES_EXACT: frozenset[str] = frozenset(
    {
        "dockerfile",
        "containerfile",
        "makefile",
        "cmakelists.txt",
        "gemfile",
        "rakefile",
        "pipfile",
        "build.gradle",
        "settings.gradle",
    }
)

SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        ".cache",
        ".tox",
        ".nox",
        "node_modules",
        "vendor",
        "dist",
        "build",
        "target",
        ".next",
        ".nuxt",
        "coverage",
        ".terraform",
        ".gradle",
        ".idea",
        ".vscode",
        "generated",
        "__generated__",
    }
)

BINARY_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".ico",
        ".pdf",
        ".zip",
        ".gz",
        ".tar",
        ".tgz",
        ".7z",
        ".jar",
        ".war",
        ".class",
        ".wasm",
        ".so",
        ".dylib",
        ".dll",
        ".exe",
        ".bin",
        ".sqlite",
        ".db",
        ".parquet",
    }
)

GENERATED_SUFFIXES: tuple[str, ...] = (
    ".min.js",
    ".min.css",
    ".bundle.js",
    ".generated.py",
    ".generated.ts",
    ".generated.tsx",
    ".generated.js",
    ".pb.go",
    ".pb.cc",
    ".pb.h",
    ".g.cs",
)

GENERATED_FILENAMES_EXACT: frozenset[str] = frozenset(
    {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock"}
)

MAX_SCAN_FILE_BYTES = 1_000_000
EU_IGNORE_FILENAME = ".eu-ignore"

PROSE_FILENAME_PREFIXES: tuple[str, ...] = (
    "readme",
    "changelog",
    "contributing",
    "code_of_conduct",
    "license",
    "notice",
    "authors",
    "maintainers",
)

PROSE_FILENAMES_EXACT: frozenset[str] = frozenset({"security.md"})

PROSE_PATH_PREFIXES: tuple[str, ...] = ("docs/", "documentation/", "doc/")

TEST_PATH_PREFIXES: tuple[str, ...] = (
    "test/",
    "tests/",
    "__tests__/",
    "spec/",
    "specs/",
    "fixtures/",
    "fixture/",
    "__fixtures__/",
    "testdata/",
    "test_data/",
    "e2e/",
)

TEST_BASENAME_SUFFIXES: tuple[str, ...] = (
    "_test",
    "_tests",
    "_spec",
    ".test",
    ".tests",
    ".spec",
)


@dataclass(frozen=True)
class EuIgnoreRule:
    pattern: str
    anchored: bool = False
    directory_only: bool = False
    has_slash: bool = False

    def matches(self, rel_posix: str, *, is_dir: bool = False) -> bool:
        rel = rel_posix.strip("/")
        pattern = self.pattern.strip("/")
        if not rel or not pattern:
            return False
        if self.directory_only:
            if self.anchored or self.has_slash:
                return any(
                    _path_pattern_matches(candidate, pattern)
                    for candidate in _directory_candidates(rel, is_dir=is_dir)
                )
            return any(
                fnmatch.fnmatchcase(part, pattern)
                for part in _directory_parts(rel, is_dir=is_dir)
            )
        if self.anchored and not self.has_slash:
            first = rel.split("/", 1)[0]
            return fnmatch.fnmatchcase(first, pattern)
        if not self.has_slash:
            return any(
                fnmatch.fnmatchcase(part, pattern)
                for part in pathlib.PurePosixPath(rel).parts
            )
        return _path_or_parent_pattern_matches(rel, pattern, is_dir=is_dir)


def parse_eu_ignore(text: str) -> tuple[EuIgnoreRule, ...]:
    rules: list[EuIgnoreRule] = []
    for raw_line in text.splitlines():
        line = raw_line.strip().replace("\\", "/")
        while line.startswith("./"):
            line = line[2:]
        if not line or line.startswith("#"):
            continue
        if line.startswith("!"):
            continue
        anchored = line.startswith("/")
        pattern = line[1:] if anchored else line
        directory_only = pattern.endswith("/")
        pattern = pattern.rstrip("/")
        if not pattern:
            continue
        rules.append(
            EuIgnoreRule(
                pattern=pattern,
                anchored=anchored,
                directory_only=directory_only,
                has_slash="/" in pattern,
            )
        )
    return tuple(rules)


def load_eu_ignore(repo_root: pathlib.Path) -> tuple[EuIgnoreRule, ...]:
    path = repo_root / EU_IGNORE_FILENAME
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ()
    return parse_eu_ignore(text)


def _relative_posix(path: pathlib.Path, repo_root: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except (ValueError, OSError):
        return path.as_posix().lstrip("./")


def is_eu_ignored(
    path: pathlib.Path,
    repo_root: pathlib.Path,
    rules: tuple[EuIgnoreRule, ...] | None = None,
) -> bool:
    active_rules = load_eu_ignore(repo_root) if rules is None else rules
    if not active_rules:
        return False
    rel = _relative_posix(path, repo_root)
    return any(rule.matches(rel, is_dir=path.is_dir()) for rule in active_rules)


def _directory_parts(rel_posix: str, *, is_dir: bool) -> tuple[str, ...]:
    parts = pathlib.PurePosixPath(rel_posix).parts
    return parts if is_dir else parts[:-1]


def _directory_candidates(rel_posix: str, *, is_dir: bool) -> tuple[str, ...]:
    parts = pathlib.PurePosixPath(rel_posix).parts
    max_len = len(parts) if is_dir else max(len(parts) - 1, 0)
    return tuple("/".join(parts[:idx]) for idx in range(1, max_len + 1))


def _path_or_parent_pattern_matches(rel_posix: str, pattern: str, *, is_dir: bool) -> bool:
    if _path_pattern_matches(rel_posix, pattern):
        return True
    return any(
        _path_pattern_matches(candidate, pattern)
        for candidate in _directory_candidates(rel_posix, is_dir=is_dir)
    )


def _path_pattern_matches(rel_posix: str, pattern: str) -> bool:
    path_parts = pathlib.PurePosixPath(rel_posix).parts
    pattern_parts = pathlib.PurePosixPath(pattern).parts
    return _path_pattern_parts_match(path_parts, pattern_parts)


def _path_pattern_parts_match(
    path_parts: tuple[str, ...],
    pattern_parts: tuple[str, ...],
) -> bool:
    if not pattern_parts:
        return not path_parts
    head = pattern_parts[0]
    if head == "**":
        if len(pattern_parts) == 1:
            return True
        return any(
            _path_pattern_parts_match(path_parts[index:], pattern_parts[1:])
            for index in range(len(path_parts) + 1)
        )
    if not path_parts or not fnmatch.fnmatchcase(path_parts[0], head):
        return False
    return _path_pattern_parts_match(path_parts[1:], pattern_parts[1:])


def _is_test_basename(name: str) -> bool:
    stem = name.rsplit(".", 1)[0].lower()
    if stem.startswith("test_") or stem.startswith("tests_"):
        return True
    return any(stem.endswith(suffix) for suffix in TEST_BASENAME_SUFFIXES)


def _is_under_test_prefix(rel_posix: str) -> bool:
    lower = rel_posix.lower().lstrip("./")
    if any(lower.startswith(prefix) for prefix in TEST_PATH_PREFIXES):
        return True
    return any(f"/{prefix}" in lower for prefix in TEST_PATH_PREFIXES)


def _is_prose_basename(name: str) -> bool:
    lower = name.lower()
    if lower in PROSE_FILENAMES_EXACT:
        return True
    for prefix in PROSE_FILENAME_PREFIXES:
        if lower == prefix or lower.startswith(prefix + "."):
            return True
    return False


def _is_under_prose_prefix(rel_posix: str) -> bool:
    lower = rel_posix.lower().lstrip("./")
    return any(lower.startswith(prefix) for prefix in PROSE_PATH_PREFIXES)


def _is_under_skipped_dir(rel_posix: str) -> bool:
    parts = pathlib.PurePosixPath(rel_posix.lower().lstrip("./")).parts
    return any(part in SKIP_DIR_NAMES for part in parts[:-1])


def _is_generated_name(name: str) -> bool:
    lower = name.lower()
    return lower in GENERATED_FILENAMES_EXACT or any(
        lower.endswith(suffix) for suffix in GENERATED_SUFFIXES
    )


def _looks_binary(path: pathlib.Path) -> bool:
    try:
        with path.open("rb") as fh:
            head = fh.read(4096)
    except OSError:
        return True
    return b"\x00" in head


def _has_shebang(path: pathlib.Path) -> bool:
    try:
        with path.open("rb") as fh:
            head = fh.read(2)
    except OSError:
        return False
    return head == b"#!"


def is_code_file(
    path: pathlib.Path,
    repo_root: pathlib.Path,
    *,
    skip_tests: bool = True,
    max_bytes: int | None = MAX_SCAN_FILE_BYTES,
) -> bool:
    name = path.name
    lower_name = name.lower()

    if _is_prose_basename(name):
        return False

    try:
        rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except (ValueError, OSError):
        rel = path.as_posix()
    if _is_under_skipped_dir(rel):
        return False
    if _is_generated_name(name):
        return False
    if _is_under_prose_prefix(rel):
        return False

    if skip_tests:
        if _is_under_test_prefix(rel):
            return False
        if _is_test_basename(name):
            return False

    ext = path.suffix.lower()
    if ext in BINARY_EXTENSIONS:
        return False
    if ext in PROSE_EXTENSIONS:
        return False
    if path.exists() and max_bytes is not None:
        try:
            if path.stat().st_size > max_bytes:
                return False
        except OSError:
            return False
    if path.is_file() and _looks_binary(path):
        return False

    if ext in CODE_EXTENSIONS or lower_name in CODE_FILENAMES_EXACT:
        return True

    return bool(path.is_file() and _has_shebang(path))


def should_scan_code_file(
    path: pathlib.Path,
    repo_root: pathlib.Path,
    *,
    config: object | None = None,
    skip_tests: bool | None = None,
    max_bytes: int | None = MAX_SCAN_FILE_BYTES,
    eu_ignore_rules: tuple[EuIgnoreRule, ...] | None = None,
) -> bool:
    active_rules = load_eu_ignore(repo_root) if eu_ignore_rules is None else eu_ignore_rules
    if is_eu_ignored(path, repo_root, active_rules):
        return False

    default_skip_tests = (
        bool(getattr(config, "skip_tests", True))
        if skip_tests is None
        else skip_tests
    )
    rel = _relative_posix(path, repo_root)
    override = bool(
        config and getattr(config, "is_test_path_overridden", lambda _f: False)(rel)
    )
    return is_code_file(
        path,
        repo_root,
        skip_tests=False if override else default_skip_tests,
        max_bytes=max_bytes,
    )


def collect_code_files(
    paths: Iterable[pathlib.Path],
    repo_root: pathlib.Path,
    *,
    skip_tests: bool = True,
    max_bytes: int | None = MAX_SCAN_FILE_BYTES,
    config: object | None = None,
    eu_ignore_rules: tuple[EuIgnoreRule, ...] | None = None,
) -> tuple[list[pathlib.Path], list[pathlib.Path]]:
    selected: list[pathlib.Path] = []
    oversized: list[pathlib.Path] = []
    seen: set[pathlib.Path] = set()
    active_rules = load_eu_ignore(repo_root) if eu_ignore_rules is None else eu_ignore_rules
    for raw_path in paths:
        path = raw_path.expanduser()
        if path.is_file():
            candidates = [path]
        elif path.is_dir():
            candidates = []
            for root, dirs, files in os.walk(path):
                root_path = pathlib.Path(root)
                dirs[:] = sorted(
                    d
                    for d in dirs
                    if d.lower() not in SKIP_DIR_NAMES
                    and not is_eu_ignored(root_path / d, repo_root, active_rules)
                )
                candidates.extend(root_path / name for name in sorted(files))
        else:
            continue
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            if not should_scan_code_file(
                candidate,
                repo_root,
                config=config,
                skip_tests=skip_tests,
                max_bytes=max_bytes,
                eu_ignore_rules=active_rules,
            ):
                if (
                    max_bytes is not None
                    and candidate.is_file()
                    and should_scan_code_file(
                        candidate,
                        repo_root,
                        config=config,
                        skip_tests=skip_tests,
                        max_bytes=None,
                        eu_ignore_rules=active_rules,
                    )
                ):
                    seen.add(resolved)
                    oversized.append(candidate)
                continue
            seen.add(resolved)
            selected.append(candidate)
    return selected, oversized
