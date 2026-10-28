from __future__ import annotations

import sys
import csv
import gzip
import hashlib
import argparse
from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "pkg"

# URLs selected from the PKG25S4 entries in your supplied URL file.
DATASETS = {
    "entities": {
        "filename": "C21_BioEntities.tsv.gz",
        "url": (
            "https://download.scidb.cn/download?"
            "fileId=ef2ccca61d30eb8eeff98f3581307d9e"
            "&path=/V3/PKG25S4/TSV/C21_BioEntities.tsv.gz"
            "&shortLink=eQjUfa&fileName=C21_BioEntities.tsv.gz"
        ),
    },
    "relationships": {
        "filename": "C22_Bioentity_Relationships.tsv.gz",
        "url": (
            "https://download.scidb.cn/download?"
            "fileId=80d6c0d836620275643d78998bcec667"
            "&path=/V3/PKG25S4/TSV/C22_Bioentity_Relationships.tsv.gz"
            "&shortLink=eQjUfa&fileName=C22_Bioentity_Relationships.tsv.gz"
        ),
    }
}


def verify_gzip_header(path: Path) -> None:
    """Check that the downloaded file is readable as a gzip TSV."""
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as file:
        header = file.readline().rstrip("\r\n")

    if not header:
        raise ValueError(f"{path.name} has an empty TSV header.")

    columns = header.split("\t")
    if len(columns) < 2:
        raise ValueError(
            f"{path.name} does not appear to contain a multi-column TSV."
        )

    if len(columns) != len(set(columns)):
        raise ValueError(f"{path.name} has duplicate column names.")

    print(f"Header verified: {path.name} ({len(columns)} columns)")


def download_dataset(key: str) -> None:
    dataset = DATASETS[key]
    filename = dataset["filename"]
    url = dataset["url"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    destination = OUTPUT_DIR / filename
    partial = OUTPUT_DIR / f"{filename}.part"

    if destination.exists():
        raise FileExistsError(
            f"{destination} already exists. "
            "Move it elsewhere or remove it deliberately before retrying."
        )

    digest = hashlib.sha256()
    total_bytes = 0

    try:
        with requests.get(
            url,
            stream=True,
            timeout=(20, 120),
            allow_redirects=True,
        ) as response:
            response.raise_for_status()

            with partial.open("wb") as output:
                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):
                    if not chunk:
                        continue

                    output.write(chunk)
                    digest.update(chunk)
                    total_bytes += len(chunk)

        if total_bytes == 0:
            raise ValueError(f"{filename} downloaded as an empty file.")

        # Reject an HTML error/login page saved under a .gz filename.
        with partial.open("rb") as downloaded:
            magic_bytes = downloaded.read(2)

        if magic_bytes != b"\x1f\x8b":
            raise ValueError(
                f"{filename} does not have a gzip signature. "
                "The download URL may have returned an error page."
            )

        # Check that gzip decompression can read the TSV header.
        verify_gzip_header(partial)

        # Only publish the file after the checks above pass.
        partial.replace(destination)

        print(f"Saved: {destination}")
        print(f"Compressed bytes: {total_bytes:,}")
        print(f"SHA-256: {digest.hexdigest()}")

    except Exception:
        partial.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download selected PKG25S4 TSV tables."
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        choices=sorted(DATASETS.keys()),
        default=["entities", "relationships"],
        help=(
            "Tables to download. Default: entities relationships. "
            "Add paper_entities and papers for evidence provenance."
        ),
    )
    args = parser.parse_args()

    for key in args.tables:
        print(f"\nDownloading dataset table: {key}")
        download_dataset(key)


if __name__ == "__main__":
    main()
