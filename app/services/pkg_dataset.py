import csv
import gzip
import sys
from pathlib import Path
from collections import Counter

def inspect_table(path: Path) -> dict:
    result = {
        "filename": path.name,
        "exists": path.is_file(),
        "valid": False,
        "columns": [],
        "column_count": 0,
        "errors": [],
    }

    if not path.is_file():
        result["errors"].append("File not found.")
        return result

    try:
        with gzip.open(
            path,
            "rt",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.reader(file, delimiter="\t")
            header = next(reader, None)

            if not header:
                raise ValueError("Missing TSV header.")

            if len(header) != len(set(header)):
                raise ValueError("Duplicate column names.")

            result["columns"] = header
            result["column_count"] = len(header)
            result["valid"] = True

    except (OSError, EOFError, UnicodeError, csv.Error, ValueError) as exc:
        result["errors"].append(str(exc))

    return result


def configure_csv_field_limit() -> None:
    """Allow CSV fields larger than Python's default limit."""
    limit = sys.maxsize

    while True:
        try:
            csv.field_size_limit(limit)
            break
        except OverflowError:
            limit //= 10


def validate_relationships(
    entity_path: Path,
    relationship_path: Path,
) -> dict:
    configure_csv_field_limit()
    """Check whether relationship rows reference known entities."""

    result = {
        "valid": False,
        "entity_count": 0,
        "relationship_count": 0,
        "duplicate_entity_ids": [],
        "missing_entity_references": [],
        "missing_required_values": 0,
        "relation_type_counts": {},
        "errors": [],
    }

    # Step 1: Read the entity IDs.
    entity_ids = set()

    try:
        with gzip.open(
            entity_path, "rt", encoding="utf-8-sig", newline=""
        ) as file:
            reader = csv.DictReader(file, delimiter="\t")

            if not reader.fieldnames or "EntityId" not in reader.fieldnames:
                raise ValueError("Entity table must contain 'EntityId'.")

            duplicates = set()

            for row in reader:
                entity_id = (row.get("EntityId") or "").strip()

                if not entity_id:
                    result["missing_required_values"] += 1
                    continue

                if entity_id in entity_ids:
                    duplicates.add(entity_id)

                entity_ids.add(entity_id)

            result["entity_count"] = len(entity_ids)
            result["duplicate_entity_ids"] = sorted(duplicates)

    except (OSError, EOFError, UnicodeError, csv.Error, ValueError) as exc:
        result["errors"].append(f"Entity table: {exc}")
        return result

    # Step 2: Check each relationship against the entity IDs.
    missing_references = set()
    relation_counts = Counter()

    try:
        with gzip.open(
            relationship_path, "rt", encoding="utf-8-sig", newline=""
        ) as file:
            reader = csv.DictReader(file, delimiter="\t")

            required_columns = {
                "entity_id1",
                "entity_id2",
                "relation_type",
            }

            if not reader.fieldnames or not required_columns.issubset(
                set(reader.fieldnames)
            ):
                raise ValueError(
                    "Relationship table must contain "
                    "'entity_id1', 'entity_id2', and 'relation_type'."
                )

            for row in reader:
                result["relationship_count"] += 1

                source_id = (row.get("entity_id1") or "").strip()
                target_id = (row.get("entity_id2") or "").strip()
                relation_type = (row.get("relation_type") or "").strip()

                if not source_id or not target_id or not relation_type:
                    result["missing_required_values"] += 1

                if relation_type:
                    relation_counts[relation_type] += 1

                if source_id and source_id not in entity_ids:
                    missing_references.add(source_id)

                if target_id and target_id not in entity_ids:
                    missing_references.add(target_id)

            result["missing_entity_references"] = sorted(missing_references)
            result["relation_type_counts"] = dict(sorted(relation_counts.items()))

    except (OSError, EOFError, UnicodeError, csv.Error, ValueError) as exc:
        result["errors"].append(f"Relationship table: {exc}")
        return result

    # Step 3: Summarize structural integrity.
    result["valid"] = (
        not result["errors"]
        and not result["duplicate_entity_ids"]
        and not result["missing_entity_references"]
        and result["missing_required_values"] == 0
    )

    return result
