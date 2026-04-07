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

"""Generate navigational README files inside swift-book folders."""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BOOK_DIR = REPO_ROOT / "swift-book"
DATA_PATH = REPO_ROOT / "data" / "releases.json"

PDF_FILES = {
    "swift_book_digital.pdf": "Digital Light",
    "swift_book_digital_dark.pdf": "Digital Dark",
    "swift_book_print.pdf": "Print Light",
    "swift_book_print_dark.pdf": "Print Dark",
}


def version_sort_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def release_sort_key(release_type: str) -> tuple[int, int]:
    if release_type == "fcs":
        return (1, 0)
    match = re.match(r"beta-(\d+)", release_type)
    if match:
        return (0, int(match.group(1)))
    return (0, 0)


def release_label(release_type: str) -> str:
    if release_type == "fcs":
        return "Stable"
    return release_type.replace("-", " ").title()


def load_manifest() -> dict:
    if not DATA_PATH.is_file():
        return {}
    return json.loads(DATA_PATH.read_text())


def release_date(manifest: dict, version: str, release_type: str) -> str:
    return manifest.get("releases", {}).get(f"{version}/{release_type}", {}).get("date", "")


def latest_date(manifest: dict) -> str:
    return manifest.get("latest", {}).get("date", "")


def latest_sha(manifest: dict) -> str:
    return manifest.get("latest", {}).get("sha", "")


def latest_message(manifest: dict) -> str:
    return manifest.get("latest", {}).get("message", "")


def pdf_links(directory: Path) -> list[str]:
    links = []
    for filename, label in PDF_FILES.items():
        if (directory / filename).is_file():
            links.append(f"- [{label}]({filename})")
    return links


def write_readme(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines).rstrip() + "\n")


def scan_versions() -> list[tuple[str, list[str]]]:
    versions: list[tuple[str, list[str]]] = []
    version_dirs = [
        item
        for item in BOOK_DIR.iterdir()
        if item.is_dir() and item.name != "latest"
    ]
    for version_dir in sorted(version_dirs, key=lambda item: version_sort_key(item.name)):
        releases = [
            release_dir.name
            for release_dir in sorted(version_dir.iterdir(), key=lambda item: release_sort_key(item.name))
            if release_dir.is_dir()
        ]
        if releases:
            versions.append((version_dir.name, releases))
    return versions


def generate_root_readme(manifest: dict, versions: list[tuple[str, list[str]]]) -> None:
    lines = [
        "# Swift Book Files",
        "",
        "Browse the PDF editions stored in this folder.",
        "",
        "## Latest",
        "",
        f"- [Latest preview](latest) ({latest_date(manifest) or 'date unavailable'})",
        "",
        "## Versions",
        "",
    ]
    for version, _ in reversed(versions):
        lines.append(f"- [Swift {version}]({version})")
    write_readme(BOOK_DIR / "README.md", lines)


def generate_version_readme(manifest: dict, version: str, releases: list[str]) -> None:
    version_dir = BOOK_DIR / version
    lines = [
        f"# Swift {version}",
        "",
        "Available releases in this folder:",
        "",
    ]
    for release_type in reversed(releases):
        date = release_date(manifest, version, release_type) or "date unavailable"
        lines.append(f"- [{release_label(release_type)}]({release_type}) ({date})")
    lines.extend(
        [
            "",
            "## Navigation",
            "",
            "- [Back to swift-book](..)",
            "- [Latest preview](../latest)",
        ]
    )
    write_readme(version_dir / "README.md", lines)


def generate_release_readme(manifest: dict, version: str, release_type: str) -> None:
    release_dir = BOOK_DIR / version / release_type
    lines = [
        f"# Swift {version} {release_label(release_type)}",
        "",
    ]
    date = release_date(manifest, version, release_type)
    if date:
        lines.extend([f"Release date: {date}", ""])
    lines.extend(["## PDFs", ""])
    lines.extend(pdf_links(release_dir) or ["- No PDFs found in this folder."])
    lines.extend(
        [
            "",
            "## Navigation",
            "",
            "- [Back to this version](..)",
            "- [Back to swift-book](../..)",
            "- [Latest preview](../../latest)",
        ]
    )
    write_readme(release_dir / "README.md", lines)


def generate_latest_readme(manifest: dict) -> None:
    latest_dir = BOOK_DIR / "latest"
    lines = [
        "# Latest Swift Book Preview",
        "",
        "This folder contains the most recent preview PDFs built from the upstream swift-book repository.",
        "",
    ]
    date = latest_date(manifest)
    sha = latest_sha(manifest)
    message = latest_message(manifest)
    if date:
        lines.extend([f"Latest commit date: {date}", ""])
    if sha:
        lines.extend(
            [
                "## Upstream Commit",
                "",
                "```text",
                f"SHA: {sha}",
                "Message:",
                *(message.splitlines() or [""]),
                "```",
                "",
                f"- [View upstream commit](https://github.com/swiftlang/swift-book/commit/{sha})",
                "- [Browse upstream repository](https://github.com/swiftlang/swift-book)",
                "",
            ]
        )
    lines.extend(["## PDFs", ""])
    lines.extend(pdf_links(latest_dir) or ["- No PDFs found in this folder."])
    lines.extend(
        [
            "",
            "## Navigation",
            "",
            "- [Back to swift-book](..)",
            "- [Repository README](../..)",
        ]
    )
    write_readme(latest_dir / "README.md", lines)


def main() -> None:
    manifest = load_manifest()
    versions = scan_versions()
    generate_root_readme(manifest, versions)
    generate_latest_readme(manifest)
    for version, releases in versions:
        generate_version_readme(manifest, version, releases)
        for release_type in releases:
            generate_release_readme(manifest, version, release_type)
    print(f"Generated folder READMEs for {len(versions)} versions")


if __name__ == "__main__":
    main()
