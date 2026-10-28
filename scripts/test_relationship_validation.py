from pathlib import Path
# from pprint import pprint

from app.services.pkg_dataset import validate_relationships

DATA_DIR = Path("data/pkg")

result = validate_relationships(
    entity_path=DATA_DIR / "C21_BioEntities.tsv.gz",
    relationship_path=DATA_DIR / "C22_Bioentity_Relationships.tsv.gz",
)

print(result)
