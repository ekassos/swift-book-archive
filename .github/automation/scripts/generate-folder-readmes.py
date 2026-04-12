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

"""Generate navigational README files inside archive folders."""

import json
import re
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BOOK_DIR = REPO_ROOT / "archive"
DATA_PATH = REPO_ROOT / ".github" / "automation" / "releases.json"

EDITION_FILES = {
    "swift_book.epub": "EPUB",
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


def format_date(iso_date: str) -> str:
    """Convert 'YYYY-MM-DD' to 'Mon DD, YYYY' (e.g. 'Mar 11, 2026')."""
    dt = datetime.strptime(iso_date, "%Y-%m-%d")
    return dt.strftime("%b %-d, %Y")


def release_date(manifest: dict, version: str, release_type: str) -> str:
    raw = manifest.get("releases", {}).get(f"{version}/{release_type}", {}).get("date", "")
    return format_date(raw) if raw else ""


def latest_date(manifest: dict) -> str:
    raw = manifest.get("latest", {}).get("date", "")
    return format_date(raw) if raw else ""


def latest_sha(manifest: dict) -> str:
    return manifest.get("latest", {}).get("sha", "")


def latest_message(manifest: dict) -> str:
    return manifest.get("latest", {}).get("message", "")


def latest_numbered_release(versions: list[tuple[str, list[str]]]) -> tuple[str, str]:
    """Return (version, release_type) for the latest numbered release."""
    if not versions:
        return ("", "")
    latest_version, releases = versions[-1]
    return (latest_version, releases[-1])


def version_release_label(version: str, release_type: str) -> str:
    """Format a human-readable label like '6.3 (Beta 3)' or '6.2.3'."""
    if release_type == "fcs":
        return version
    return f"{version} ({release_label(release_type)})"


DOCS_SWIFT_ORG = "https://docs.swift.org/swift-book/documentation/the-swift-programming-language/"


def edition_links(directory: Path) -> list[str]:
    links = []
    for filename, label in EDITION_FILES.items():
        if (directory / filename).is_file():
            suffix = "" if filename == "swift_book.epub" else " PDF"
            links.append(f"- [{label}{suffix}]({filename})")
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
    lv, lr = latest_numbered_release(versions)
    label = version_release_label(lv, lr)
    lines = [
        "# Swift Book Archive",
        "",
        "Download current and previous PDF and EPUB editions of _The Swift Programming Language_ book from this folder.",
        "",
        "## Version. Choose a corresponding Swift version.",
        "",
    ]
    if lv:
        date = release_date(manifest, lv, lr) or "date unavailable"
        lines.extend([
            f"The latest numbered release, **{label}**, is the best choice for most readers, and mirrors the version of _The Swift Programming Language_ that's currently available at [docs.swift.org]({DOCS_SWIFT_ORG}).",
            "",
            f"- [{label}]({lv}/{lr}) ({date})",
            "",
        ])
    lines.extend([
        "**Latest** is a continuously updated preview of _The Swift Programming Language_ from the source repository and may include unpublished changes before an official release.",
        "",
        f"- [Latest](latest) ({latest_date(manifest) or 'date unavailable'})",
        "",
        "If you're working with a specific Swift version, choose the matching numbered release.",
        "",
    ])
    for version, _ in reversed(versions):
        lines.append(f"- [Swift {version}]({version})")
    write_readme(BOOK_DIR / "README.md", lines)


def generate_version_readme(manifest: dict, version: str, releases: list[str], is_latest_version: bool, latest_rel: str) -> None:
    version_dir = BOOK_DIR / version
    lines = [
        f"# Swift {version}",
        "",
        f"Download PDF and EPUB editions of _The Swift Programming Language_ book for Swift {version}. Choose a release.",
        "",
    ]
    if is_latest_version:
        lines.extend([
            f"**{release_label(latest_rel)}** is the latest release, and the best choice for most readers. It mirrors the version of _The Swift Programming Language_ that's currently available at [docs.swift.org]({DOCS_SWIFT_ORG}).",
            "",
        ])
    for release_type in reversed(releases):
        date = release_date(manifest, version, release_type) or "date unavailable"
        lines.append(f"- [{release_label(release_type)}]({release_type}) ({date})")
    lines.extend(
        [
            "",
            "## More",
            "",
            "- [Back to all versions](..)",
        ]
    )
    write_readme(version_dir / "README.md", lines)


def generate_release_readme(manifest: dict, version: str, release_type: str, is_latest_release: bool) -> None:
    release_dir = BOOK_DIR / version / release_type
    lines = [
        f"# Swift {version} {release_label(release_type)}",
        "",
    ]
    date = release_date(manifest, version, release_type)
    if date:
        lines.extend([f"Download PDF and EPUB editions of _The Swift Programming Language_ book for Swift {version} {release_label(release_type)}.", "", f"Release date: {date}", ""])
    else:
        lines.extend([f"Download PDF and EPUB editions of _The Swift Programming Language_ book for Swift {version} {release_label(release_type)}.", ""])
    if is_latest_release:
        lines.extend([
            f"This is the latest numbered release, and the best choice for most readers. It mirrors the version of _The Swift Programming Language_ that's currently available at [docs.swift.org]({DOCS_SWIFT_ORG}).",
            "",
        ])
    lines.extend(["## Edition. Pick the one that works for you.", ""])
    lines.extend(edition_links(release_dir) or ["- No editions found in this folder."])
    lines.extend(
        [
            "",
            "## More",
            "",
            f"- [Back to all Swift {version} versions](..)",
            "- [Back to all versions](../..)",
        ]
    )
    write_readme(release_dir / "README.md", lines)


def generate_latest_readme(manifest: dict) -> None:
    latest_dir = BOOK_DIR / "latest"
    lines = [
        "# Latest",
        "",
        "**Latest** is a continuously updated preview of _The Swift Programming Language_ from the source repository and may include unpublished changes before an official release.",
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
                f"SHA: `{sha}`",
                "",
                "Commit message:",
                "```text",
                *(message.splitlines() or [""]),
                "```",
                "",
                f"- [View upstream commit](https://github.com/swiftlang/swift-book/commit/{sha})",
                f"- [Browse upstream repository](https://github.com/swiftlang/swift-book/tree/{sha})",
                "",
            ]
    )
    lines.extend(["## Edition. Pick the one that works for you.", ""])
    lines.extend(edition_links(latest_dir) or ["- No editions found in this folder."])
    lines.extend(
        [
            "",
            "## More",
            "",
            "- [Back to all versions](..)",
        ]
    )
    write_readme(latest_dir / "README.md", lines)


def main() -> None:
    manifest = load_manifest()
    versions = scan_versions()
    lv, lr = latest_numbered_release(versions)
    generate_root_readme(manifest, versions)
    generate_latest_readme(manifest)
    for version, releases in versions:
        is_latest_version = version == lv
        generate_version_readme(manifest, version, releases, is_latest_version, lr)
        for release_type in releases:
            is_latest_release = is_latest_version and release_type == lr
            generate_release_readme(manifest, version, release_type, is_latest_release)
    print(f"Generated folder READMEs for {len(versions)} versions")


if __name__ == "__main__":
    main()
