import json
import sys

from src.db.vector_db.opensearch import get_opensearch_client
from src.schemas import (
    PROCESSOR_SCORE_RANKER,
    Combination,
    PipelineProcessor,
    ScoreRankerProcessorBody,
    ScoreTechnique,
    SearchPipeline,
)
from src.settings import settings

current_version_uuid = "89f864ff-138b-4847-b9ef-2906d1971fa8"

SEARCH_PIPELINE_NAME = "hybrid-rrf"
SEARCH_PIPELINE = SearchPipeline(
    description="Initial score ranker pipeline for diseases index",
    phase_results_processors=[
        PipelineProcessor(
            processor_name=PROCESSOR_SCORE_RANKER,
            body=ScoreRankerProcessorBody(
                combination=Combination(technique=ScoreTechnique.RRF)
            ),
        ),
    ],
)
PATH_TO_INIT_MAPPING = settings.indices_dir / "diseases/init_mapping.json"


def upgrade() -> None:
    client = get_opensearch_client()
    with open(PATH_TO_INIT_MAPPING, encoding="utf-8") as mapping_file:
        mappings = json.load(mapping_file)
    client.create_index(
        "init_diseases",
        {
            "settings": {"index": {"knn": True}},
            "mappings": mappings,
        },
    )
    client.create_alias("diseases", "init_diseases")
    client.create_search_pipeline(
        SEARCH_PIPELINE_NAME,
        SEARCH_PIPELINE.to_dict(),
    )


def downgrade() -> None:
    client = get_opensearch_client()
    client.delete_search_pipeline(SEARCH_PIPELINE_NAME)
    client.delete_alias("diseases", "init_diseases")
    client.delete_index("init_diseases")


if __name__ == "__main__":
    args = sys.argv[1]
    if args == "upgrade":
        upgrade()
    elif args == "downgrade":
        downgrade()
    else:
        print("Invalid argument")
