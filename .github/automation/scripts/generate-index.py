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

"""Update the README version index from the local archive tree and release manifest."""

from datetime import datetime
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BOOK_DIR = REPO_ROOT / "archive"
README_PATH = REPO_ROOT / "README.md"
DATA_PATH = REPO_ROOT / ".github" / "automation" / "releases.json"

BOOK_FILES = [
    "swift_book.epub",
    "swift_book_digital.pdf",
    "swift_book_digital_dark.pdf",
    "swift_book_print.pdf",
    "swift_book_print_dark.pdf",
]

README_START = "<!-- VERSION-INDEX:START -->"
README_END = "<!-- VERSION-INDEX:END -->"
LINK_LABELS = {
    "swift_book.epub": "EPUB",
    "swift_book_digital.pdf": "Light",
    "swift_book_digital_dark.pdf": "Dark",
    "swift_book_print.pdf": "Light",
    "swift_book_print_dark.pdf": "Dark",
}


def version_sort_key(version: str) -> tuple:
    """Return a tuple of ints for natural version sorting."""
    return tuple(int(x) for x in version.split("."))


def format_release_date(date_str: str) -> str:
    """Format an ISO date like 2026-02-12 as Feb 12, 2026."""
    if not date_str:
        return "-"
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %-d, %Y")


def release_sort_key(release_type: str) -> tuple:
    """Sort betas before fcs, betas numerically."""
    if release_type == "fcs":
        return (1, 0)
    match = re.match(r"beta-(\d+)", release_type)
    if match:
        return (0, int(match.group(1)))
    return (0, 0)


def scan_versions() -> list[dict]:
    """Scan archive/ and return a sorted list of version entries."""
    versions: dict[str, list[dict]] = {}

    for version_dir in sorted(BOOK_DIR.iterdir()):
        if not version_dir.is_dir() or version_dir.name == "latest":
            continue
        version = version_dir.name
        releases = []
        for release_dir in sorted(version_dir.iterdir()):
            if not release_dir.is_dir():
                continue
            release_type = release_dir.name
            files = [f.name for f in sorted(release_dir.iterdir()) if f.is_file() and f.name in BOOK_FILES]
            if not files:
                continue
            raw_version = version.removesuffix(".0") if re.match(r"^\d+\.0$", version) else version
            releases.append(
                {
                    "type": release_type,
                    "path": f"archive/{version}/{release_type}",
                    "files": files,
                }
            )
        releases.sort(key=lambda release: release_sort_key(release["type"]))
        if releases:
            versions[version] = releases

    result = []
    for version in sorted(versions, key=version_sort_key):
        result.append({"version": version, "releases": versions[version]})
    return result


def release_label(release_type: str) -> str:
    """Return the human-readable label for a release type."""
    return "Stable" if release_type == "fcs" else release_type.replace("-", " ").title()


def version_cell_text(version: str, release_type: str, index: int) -> str:
    """Return the display label used in the version column."""
    label = release_label(release_type)
    if index == 0 and label == "Stable":
        return version
    if index == 0:
        return f"{version} ({label})"
    return f"└─ {label}"


def recommended_release(versions: list[dict]) -> tuple[str, str, str]:
    """Return the latest versioned release shown in the table."""
    if not versions:
        return ("", "", "")

    entry = versions[-1]
    release = entry["releases"][-1]
    label = version_cell_text(entry["version"], release["type"], 0)
    return (entry["version"], release["type"], label)


def load_release_manifest() -> dict:
    """Load release metadata stored by the workflow."""
    if not DATA_PATH.is_file():
        return {}

    with DATA_PATH.open() as handle:
        return json.load(handle)


def release_date(version: str, release_type: str, manifest: dict) -> str:
    """Resolve a release date from the manifest."""
    release_key = f"{version}/{release_type}"
    return manifest.get("releases", {}).get(release_key, {}).get("date", "")


def latest_release_date(manifest: dict) -> str:
    """Resolve the latest row date from the manifest."""
    return manifest.get("latest", {}).get("date", "")


def generate_versions_intro(recommended_label: str) -> str:
    """Generate helper text for choosing a version."""
    if recommended_label:
        return (
            f"The latest numbered release, **{recommended_label}**, is the best choice for most readers, "
            "and mirrors the version of _The Swift Programming Language_ that's currently available at "
            "[docs.swift.org](https://docs.swift.org/swift-book/documentation/the-swift-programming-language/). "
        )

    return (
        "The latest numbered release is the best choice for most readers and mirrors the version of "
        "_The Swift Programming Language_ that's currently available at "
        "[docs.swift.org](https://docs.swift.org/swift-book/documentation/the-swift-programming-language/)."
    )


def generate_latest_intro() -> str:
    """Generate helper text for the Latest preview row."""
    return (
        "**Latest** is a continuously updated preview of _The Swift Programming Language_ from the source repository and may include "
        "unpublished changes before an official release."
    )


def generate_previous_versions_intro() -> str:
    """Generate helper text for the previous versions table."""
    return "If you're working with a specific Swift version, choose the matching numbered release."


def generate_readme_table(
    versions: list[dict],
    manifest: dict,
    recommended: tuple[str, str],
    include_latest: bool = True,
    exclude_recommended: bool = False,
    only_recommended: bool = False,
    bold_recommended: bool = False,
) -> str:
    """Generate a Markdown table of available versions."""
    latest_files = [f.name for f in sorted((BOOK_DIR / "latest").iterdir()) if f.is_file() and f.name in BOOK_FILES]

    def render_file_links(base_path: str, filenames: list[str]) -> str:
        links = []
        for filename in filenames:
            links.append(f"[{LINK_LABELS[filename]}]({base_path}/{filename}?raw=1)")
        return " · ".join(links) if links else "-"

    lines = [
        "| Version | Release Date | Folder | EPUB | Digital PDF | Print PDF |",
        "|---------|--------------|--------|------|-------------|-----------|",
    ]

    if include_latest and latest_files:
        epub_files = [name for name in latest_files if name == "swift_book.epub"]
        digital_files = [name for name in latest_files if name.startswith("swift_book_digital")]
        print_files = [name for name in latest_files if name.startswith("swift_book_print")]
        latest_row = (
            "| Latest | "
            f"{format_release_date(latest_release_date(manifest))} | "
            "[Open ↗](archive/latest) | "
            f"{render_file_links('archive/latest', epub_files)} | "
            f"{render_file_links('archive/latest', digital_files)} | "
            f"{render_file_links('archive/latest', print_files)} |"
        )
    else:
        latest_row = None

    for entry in reversed(versions):
        ordered_releases = list(reversed(entry["releases"]))
        displayed_index = 0
        for index, release in enumerate(ordered_releases):
            is_recommended = (entry["version"], release["type"]) == recommended
            if only_recommended and not is_recommended:
                continue
            if exclude_recommended and (entry["version"], release["type"]) == recommended:
                continue
            if displayed_index == 0 and index > 0:
                lines.append(f"| {entry['version']} |  |  |  |  |  |")
            base_path = f"archive/{entry['version']}/{release['type']}"
            epub_files = [name for name in release["files"] if name == "swift_book.epub"]
            digital_files = [name for name in release["files"] if name.startswith("swift_book_digital")]
            print_files = [name for name in release["files"] if name.startswith("swift_book_print")]
            folder_link = f"[Open ↗]({base_path})"
            version_cell = version_cell_text(entry["version"], release["type"], index)
            if is_recommended:
                version_cell = f"{version_cell} ★"
                if bold_recommended:
                    version_cell = f"**{version_cell}**"
            lines.append(
                f"| {version_cell} | {format_release_date(release_date(entry['version'], release['type'], manifest))} | {folder_link} | "
                f"{render_file_links(base_path, epub_files)} | "
                f"{render_file_links(base_path, digital_files)} | "
                f"{render_file_links(base_path, print_files)} |"
            )
            displayed_index += 1
    if latest_row is not None:
        lines.append(latest_row)
    return "\n".join(lines)


def update_readme(versions: list[dict]) -> None:
    """Inject the version table between the sentinel comments in README.md."""
    readme = README_PATH.read_text()
    manifest = load_release_manifest()
    recommended_version_name, recommended_release_type, recommended_label = recommended_release(versions)
    intro = generate_versions_intro(recommended_label)
    primary_table = generate_readme_table(
        versions,
        manifest,
        (recommended_version_name, recommended_release_type),
        include_latest=True,
        exclude_recommended=False,
        only_recommended=True,
        bold_recommended=True,
    )
    previous_versions_table = generate_readme_table(
        versions,
        manifest,
        (recommended_version_name, recommended_release_type),
        include_latest=False,
        exclude_recommended=True,
    )
    block = (
        f"{README_START}\n"
        f"{intro}\n\n"
        f"{generate_latest_intro()}\n\n"
        f"{primary_table}\n\n"
        "### Previous Versions\n\n"
        f"{generate_previous_versions_intro()}\n\n"
        f"{previous_versions_table}\n"
        f"{README_END}"
    )

    if README_START in readme and README_END in readme:
        readme = re.sub(
            rf"{re.escape(README_START)}.*?{re.escape(README_END)}",
            block,
            readme,
            flags=re.DOTALL,
        )
    else:
        readme = readme.replace(
            "## Acknowledgments",
            f"## Available Versions\n\n{block}\n\n## Acknowledgments",
        )
    README_PATH.write_text(readme)

def main() -> None:
    versions = scan_versions()
    update_readme(versions)
    print(f"Updated README.md version index for {len(versions)} versions")


if __name__ == "__main__":
    main()
