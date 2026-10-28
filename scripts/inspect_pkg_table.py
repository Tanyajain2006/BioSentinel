from pathlib import Path
from unittest import result

from app.services.pkg_dataset import inspect_table


DATA_DIR = Path("data/pkg")

entity_file = DATA_DIR / "C21_BioEntities.tsv.gz"
result_entity = inspect_table(entity_file)
print(result_entity)

relationship_file = DATA_DIR / "C22_Bioentity_Relationships.tsv.gz"
result_relationship = inspect_table(relationship_file)
print(result_relationship)