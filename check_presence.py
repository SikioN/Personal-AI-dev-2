
from src.utils.graph_loader import hydrate_in_memory_graph
from src.kg_model.knowledge_graph_model import KnowledgeGraphModel, KnowledgeGraphModelConfig
from src.db_drivers.graph_driver import GraphDriverConfig
from src.utils.wikidata_utils import WikidataMapper
from src.utils import Logger

from src.db_drivers.vector_driver.embedders import EmbedderModelConfig
from src.kg_model.embeddings_model import EmbeddingsModelConfig

logger = Logger("log/check_presence")

# Configure Embedder to use HF path
embedder_cfg = EmbedderModelConfig(model_name_or_path='intfloat/multilingual-e5-small')
embeddings_cfg = EmbeddingsModelConfig(embedder_config=embedder_cfg)

config = KnowledgeGraphModelConfig(
    graph_config=GraphDriverConfig(db_vendor='inmemory_graph'),
    embeddings_config=embeddings_cfg
)
kg_model = KnowledgeGraphModel(config=config)
kg_model.graph_struct.db_conn.open_connection()

data_dir = "wikidata_big/kg" 
mapper = WikidataMapper(data_dir)
hydrate_in_memory_graph(kg_model, mapper, data_dir)

rr_id = "Q25559009"
connector = kg_model.graph_struct.db_conn
internal_ids = connector.strid_nodes_index.get(rr_id)

print(f"\n[Check] Richard Richards ({rr_id}) in index: {internal_ids}")

if internal_ids:
    node = connector.nodes.get(list(internal_ids)[0])
    print(f"[Check] Node object: {node}")
else:
    print("[ERROR] Richard Richards NOT found in graph index!")
