import argparse
import csv
import sys
import gzip
from collections import Counter
from pathlib import Path


def set_csv_field_size_limit():
    limit = sys.maxsize

    while True:
        try:
            csv.field_size_limit(limit)
            break
        except OverflowError:
            limit //= 10
            

def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Inspect unresolved PKG entity references."
    )

    parser.add_argument(
        "--max-examples",
        type=int,
        default=10,
        help="Maximum unresolved relationship rows to print (default: 10).",
    )

    args = parser.parse_args()

    if args.max_examples < 0:
        parser.error("--max-examples must be zero or greater")

    return args


def load_entity_ids(entity_file: Path) -> set[str]:
    """Load unique entity IDs from the entity TSV file."""
    entity_ids = set()

    with gzip.open(
        entity_file,
        "rt",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file, delimiter="\t")

        if not reader.fieldnames or "EntityId" not in reader.fieldnames:
            raise ValueError(
                "Entity table must contain the 'EntityId' column."
            )

        for row in reader:
            entity_id = (row.get("EntityId") or "").strip()

            if entity_id:
                entity_ids.add(entity_id)

    return entity_ids


def get_namespace(entity_id: str) -> str:
    """Classify an entity ID by its observed identifier prefix."""
    if entity_id.startswith("NCBIGene"):
        return "NCBIGene"
    if entity_id.startswith("CHEBI"):
        return "CHEBI"
    if entity_id.startswith("mesh"):
        return "mesh"
    return "other"


def inspect_missing_references(
    relationship_file: Path,
    entity_ids: set[str],
    max_examples: int,
) -> tuple[set[str], Counter, Counter]:
    """
    Scan relationships and summarize unresolved entity references.

    Namespace counts count each unresolved ID at most once per row.
    Relationship-type counts count affected rows, not unique IDs.
    """
    missing_ids = set()
    missing_id_prefix_counts = Counter()
    affected_relation_counts = Counter()
    examples_printed = 0

    with gzip.open(
        relationship_file,
        "rt",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file, delimiter="\t")

        required_columns = {
            "PMID",
            "entity_id1",
            "entity_id2",
            "relation_type",
        }

        if not reader.fieldnames or not required_columns.issubset(
            set(reader.fieldnames)
        ):
            raise ValueError(
                "Relationship table must contain these columns: "
                + ", ".join(sorted(required_columns))
            )

        for row in reader:
            source_id = (row.get("entity_id1") or "").strip()
            target_id = (row.get("entity_id2") or "").strip()

            missing_source = (
                bool(source_id) and source_id not in entity_ids
            )
            missing_target = (
                bool(target_id) and target_id not in entity_ids
            )

            # Collect unresolved IDs for this relationship row.
            unresolved_in_row = set()

            if missing_source:
                unresolved_in_row.add(source_id)

            if missing_target:
                unresolved_in_row.add(target_id)

            # Count distinct unresolved IDs across the entire dataset.
            missing_ids.update(unresolved_in_row)

            # Count each unresolved ID once per relationship row,
            # grouped by its observed namespace.
            for entity_id in unresolved_in_row:
                prefix = get_namespace(entity_id)
                missing_id_prefix_counts[prefix] += 1

            # Count relationship rows containing unresolved endpoints.
            if unresolved_in_row:
                relation_type = (
                    row.get("relation_type") or ""
                ).strip() or "(missing)"

                affected_relation_counts[relation_type] += 1

                # Limit printed examples only; never stop scanning early.
                if examples_printed < max_examples:
                    print("\nUnresolved relationship:")
                    print(f"  PMID: {row.get('PMID')}")
                    print(f"  entity_id1: {source_id}")
                    print(f"  entity_id2: {target_id}")
                    print(f"  relation_type: {relation_type}")

                    examples_printed += 1

    return (
        missing_ids,
        missing_id_prefix_counts,
        affected_relation_counts,
    )


def main() -> None:
    """Run the unresolved-reference inspection."""
    set_csv_field_size_limit()
    
    args = parse_arguments()

    data_dir = Path("data/pkg")
    entity_file = data_dir / "C21_BioEntities.tsv.gz"
    relationship_file = (
        data_dir / "C22_Bioentity_Relationships.tsv.gz"
    )

    # Step 1: Check input files.
    for file_path in (entity_file, relationship_file):
        if not file_path.is_file():
            raise FileNotFoundError(
                f"Required dataset file not found: {file_path}"
            )

    # Step 2: Load entity IDs.
    entity_ids = load_entity_ids(entity_file)
    print(f"Unique entity IDs loaded: {len(entity_ids):,}")

    # Step 3: Inspect every relationship row.
    (
        missing_ids,
        missing_id_prefix_counts,
        affected_relation_counts,
    ) = inspect_missing_references(
        relationship_file=relationship_file,
        entity_ids=entity_ids,
        max_examples=args.max_examples,
    )

    # Step 4: Report the results.
    print("\n" + "=" * 50)
    print("UNRESOLVED REFERENCE SUMMARY")
    print("=" * 50)

    print(f"Distinct unresolved IDs: {len(missing_ids):,}")
    print("Sample unresolved IDs:", sorted(missing_ids))

    print("\nUnresolved ID occurrences by namespace:")
    for prefix, count in missing_id_prefix_counts.most_common():
        print(f"  {prefix}: {count:,}")

    print("\nRelationship rows affected, by type:")
    for relation_type, count in affected_relation_counts.most_common():
        print(f"  {relation_type}: {count:,}")

    print("\nInspection complete.")
    print("Note: these counts identify unresolved references;")


if __name__ == "__main__":
    main()
