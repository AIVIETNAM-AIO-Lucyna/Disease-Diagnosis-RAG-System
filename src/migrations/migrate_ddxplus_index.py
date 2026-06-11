import json
import sys

from opensearchpy.exceptions import NotFoundError

from src.db.vector_db.opensearch import get_opensearch_client
from src.settings import settings

current_version_uuid = "6faf44c9-5214-4488-8e28-84b9362a1389"
downgrade_version_uuid = "89f864ff-138b-4847-b9ef-2906d1971fa8"

LEGACY_INDEX_NAME = "init_diseases"
DDXPLUS_INDEX_NAME = "ddxplus_diseases"
ALIAS_NAME = settings.RETRIEVE_INDEX_ALIAS
PATH_TO_LEGACY_MAPPING = f"{settings.PATH_TO_INDICES}/diseases/init_mapping.json"
PATH_TO_DDXPLUS_MAPPING = f"{settings.PATH_TO_INDICES}/diseases/ddxplus_mapping.json"


def upgrade() -> None:
    client = get_opensearch_client()
    client.create_index(
        DDXPLUS_INDEX_NAME,
        {
            "settings": {"index": {"knn": True}},
            "mappings": json.load(open(PATH_TO_DDXPLUS_MAPPING)),
        },
    )
    try:
        current_indices = list(client.client.indices.get_alias(name=ALIAS_NAME).keys())
    except NotFoundError:
        current_indices = []
    alias_actions = [
        {"remove": {"index": index_name, "alias": ALIAS_NAME}}
        for index_name in current_indices
        if index_name != DDXPLUS_INDEX_NAME
    ]
    alias_actions.append({"add": {"index": DDXPLUS_INDEX_NAME, "alias": ALIAS_NAME}})
    client.client.indices.update_aliases(body={"actions": alias_actions})
    if client.client.indices.exists(index=LEGACY_INDEX_NAME):
        client.delete_index(LEGACY_INDEX_NAME)


def downgrade() -> None:
    client = get_opensearch_client()
    client.create_index(
        LEGACY_INDEX_NAME,
        {
            "settings": {"index": {"knn": True}},
            "mappings": json.load(open(PATH_TO_LEGACY_MAPPING)),
        },
    )
    try:
        current_indices = list(client.client.indices.get_alias(name=ALIAS_NAME).keys())
    except NotFoundError:
        current_indices = []
    alias_actions = [
        {"remove": {"index": index_name, "alias": ALIAS_NAME}}
        for index_name in current_indices
        if index_name != LEGACY_INDEX_NAME
    ]
    alias_actions.append({"add": {"index": LEGACY_INDEX_NAME, "alias": ALIAS_NAME}})
    client.client.indices.update_aliases(body={"actions": alias_actions})
    if client.client.indices.exists(index=DDXPLUS_INDEX_NAME):
        client.delete_index(DDXPLUS_INDEX_NAME)


if __name__ == "__main__":
    args = sys.argv[1]
    if args == "upgrade":
        upgrade()
    elif args == "downgrade":
        downgrade()
    else:
        print("Invalid argument")
