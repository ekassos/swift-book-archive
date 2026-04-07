#!/usr/bin/env python3
# Copyright 2026 Evangelos Kassos
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Update data/releases.json from the upstream swift-book repository."""

import argparse
import json
import re
import subprocess
import tempfile
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data" / "releases.json"
BOOK_DIR = REPO_ROOT / "swift-book"
DEFAULT_UPSTREAM_REPO = REPO_ROOT / "swift-book-repo"
UPSTREAM_REPO_URL = "https://github.com/swiftlang/swift-book.git"
TAG_PATTERN = re.compile(r"^swift-(?P<version>\d+(?:\.\d+){0,2})-(?P<release>fcs|beta-\d+)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha", help="Specific upstream commit SHA to record as latest.")
    parser.add_argument(
        "--sync-all-tags",
        action="store_true",
        help="Refresh all tagged releases from the upstream repository.",
    )
    parser.add_argument(
        "--upstream-repo",
        type=Path,
        help="Path to an existing upstream swift-book checkout to read from.",
    )
    return parser.parse_args()


def git_output(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def load_manifest() -> dict:
    if not DATA_PATH.is_file():
        return {"latest": {}, "releases": {}}

    with DATA_PATH.open() as handle:
        manifest = json.load(handle)

    manifest.setdefault("latest", {})
    manifest.setdefault("releases", {})
    return manifest


def version_sort_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def release_sort_key(release_type: str) -> tuple[int, int]:
    if release_type == "fcs":
        return (1, 0)
    match = re.match(r"beta-(\d+)", release_type)
    if match:
        return (0, int(match.group(1)))
    return (0, 0)


def ordered_manifest(manifest: dict) -> OrderedDict:
    ordered = OrderedDict()
    ordered["latest"] = OrderedDict(
        (key, manifest.get("latest", {}).get(key))
        for key in ("date", "sha")
        if key in manifest.get("latest", {})
    )

    releases = OrderedDict()
    for release_path in sorted(
        manifest.get("releases", {}),
        key=lambda path: (
            version_sort_key(path.split("/", 1)[0]),
            release_sort_key(path.split("/", 1)[1]),
        ),
    ):
        entry = manifest["releases"][release_path]
        releases[release_path] = OrderedDict(
            (key, entry.get(key))
            for key in ("date", "sha", "tag")
            if key in entry
        )
    ordered["releases"] = releases
    return ordered


def write_manifest(manifest: dict) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(ordered_manifest(manifest), indent=2) + "\n")


def published_release_paths() -> set[str]:
    paths: set[str] = set()
    if not BOOK_DIR.is_dir():
        return paths

    for version_dir in BOOK_DIR.iterdir():
        if not version_dir.is_dir() or version_dir.name == "latest":
            continue
        for release_dir in version_dir.iterdir():
            if release_dir.is_dir():
                paths.add(f"{version_dir.name}/{release_dir.name}")
    return paths


def normalize_release_path(tag: str) -> str | None:
    match = TAG_PATTERN.match(tag)
    if not match:
        return None

    version = match.group("version")
    if "." not in version:
        version = f"{version}.0"
    return f"{version}/{match.group('release')}"


def resolve_upstream_repo(
    existing_repo: Path | None,
) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
    if existing_repo is not None:
        return existing_repo, None

    if DEFAULT_UPSTREAM_REPO.is_dir():
        return DEFAULT_UPSTREAM_REPO, None

    tempdir = tempfile.TemporaryDirectory(prefix="swift-book-upstream-")
    repo_path = Path(tempdir.name)
    subprocess.run(
        ["git", "clone", "--quiet", "--filter=blob:none", UPSTREAM_REPO_URL, str(repo_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return repo_path, tempdir


def update_latest_entry(manifest: dict, repo_dir: Path, sha: str | None, published_paths: set[str]) -> None:
    target = sha or "HEAD"
    latest_sha = git_output(repo_dir, "rev-parse", target)
    latest_date = git_output(repo_dir, "show", "-s", "--format=%cs", latest_sha)
    manifest["latest"] = {
        **manifest.get("latest", {}),
        "date": latest_date,
        "sha": latest_sha,
    }

    tags = [tag for tag in git_output(repo_dir, "tag", "--points-at", latest_sha).splitlines() if tag]
    for tag in tags:
        release_path = normalize_release_path(tag)
        if release_path is None or release_path not in published_paths:
            continue
        manifest["releases"][release_path] = {
            **manifest["releases"].get(release_path, {}),
            "date": latest_date,
            "sha": latest_sha,
            "tag": tag,
        }


def sync_all_tags(manifest: dict, repo_dir: Path, published_paths: set[str]) -> int:
    manifest["releases"] = {
        release_path: entry
        for release_path, entry in manifest["releases"].items()
        if release_path in published_paths
    }

    count = 0
    for tag in git_output(repo_dir, "tag", "--list", "swift-*").splitlines():
        release_path = normalize_release_path(tag)
        if release_path is None or release_path not in published_paths:
            continue
        date_output = git_output(
            repo_dir,
            "for-each-ref",
            "--format=%(taggerdate:short)%09%(creatordate:short)",
            f"refs/tags/{tag}",
        )
        tagger_date, _, creator_date = date_output.partition("\t")
        tag_date = tagger_date or creator_date
        tag_sha = git_output(repo_dir, "rev-list", "-n", "1", tag)
        manifest["releases"][release_path] = {
            **manifest["releases"].get(release_path, {}),
            "date": tag_date,
            "sha": tag_sha,
            "tag": tag,
        }
        count += 1
    return count


def main() -> None:
    args = parse_args()
    manifest = load_manifest()
    published_paths = published_release_paths()
    repo_dir, tempdir = resolve_upstream_repo(args.upstream_repo)

    try:
        updated_tags = sync_all_tags(manifest, repo_dir, published_paths) if args.sync_all_tags else 0
        update_latest_entry(manifest, repo_dir, args.sha, published_paths)
        write_manifest(manifest)
    finally:
        if tempdir is not None:
            tempdir.cleanup()

    latest_sha = manifest.get("latest", {}).get("sha", "")[:7]
    print(f"Updated data/releases.json with latest {latest_sha} and {updated_tags} tagged releases")


if __name__ == "__main__":
    main()
