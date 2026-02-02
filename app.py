import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network
import pandas as pd
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.kg_model.knowledge_graph_model import KnowledgeGraphModel, KnowledgeGraphModelConfig
from src.pipelines.qa.qa_engine import QAEngine
from src.utils.kg_navigator import KGNavigator

# Page config
st.set_page_config(page_title="KG QA Navigator", layout="wide", page_icon="🕸️")

st.title("🕸️ Personal-AI KG QA Navigator")
st.markdown("Query your Knowledge Graph using natural language and visualize the temporal evidence.")

# Paths
ROOT_DIR = os.getcwd()
MODEL_PATH = os.path.join(ROOT_DIR, 'models/wikidata_finetuned_remote/wikidata_finetuned')

@st.cache_resource
def load_engine():
    from src.db_drivers.vector_driver.embedders import EmbedderModelConfig
    from src.kg_model.embeddings_model import EmbeddingsModelConfig
    from src.db_drivers.vector_driver import VectorDriverConfig, VectorDBConnectionConfig
    from src.kg_model.graph_model import GraphModelConfig
    from src.db_drivers.graph_driver import GraphDriverConfig
    
    # Correct relative paths that assume running from src/kg_model
    nodes_path = os.path.join(ROOT_DIR, "data/graph_structures/vectorized_nodes/wikidata_test")
    triplets_path = os.path.join(ROOT_DIR, "data/graph_structures/vectorized_triplets/wikidata_test")
    
    nodes_cfg = VectorDriverConfig(
        db_vendor='chroma', db_config=VectorDBConnectionConfig(
            conn={'path': nodes_path},
            db_info={'db': 'default_db', 'table': "personalaitable"}))
            
    triplets_cfg = VectorDriverConfig(
        db_vendor='chroma', db_config=VectorDBConnectionConfig(
            conn={'path': triplets_path},
            db_info={'db': 'default_db', 'table': "personalaitable"}))

    # Force In-Memory Graph Driver to avoid Neo4j issues locally
    graph_driver_cfg = GraphDriverConfig(db_vendor='inmemory_graph')
    graph_cfg = GraphModelConfig(driver_config=graph_driver_cfg)

    # Pre-configure embedder with finetuned model
    # Use HF hub path if local path is not guaranteed
    embedder_cfg = EmbedderModelConfig(model_name_or_path='intfloat/multilingual-e5-small')
    
    emb_cfg = EmbeddingsModelConfig(
        nodesdb_driver_config=nodes_cfg,
        tripletsdb_driver_config=triplets_cfg,
        embedder_config=embedder_cfg
    )
    
    config = KnowledgeGraphModelConfig(
        embeddings_config=emb_cfg,
        graph_config=graph_cfg
    )
    
    kg_model = KnowledgeGraphModel(config)
    
    # Hydrate the In-Memory graph from raw files
    with st.spinner("📦 Loading and Hydrating Knowledge Graph..."):
        from src.utils.wikidata_utils import WikidataMapper
        from src.utils.graph_loader import hydrate_in_memory_graph
        kg_data_path = os.path.join(ROOT_DIR, "wikidata_big/kg")
        mapper = WikidataMapper(kg_data_path)
        hydrate_in_memory_graph(kg_model, mapper, kg_data_path)
    
    st.sidebar.success("✅ Graph Hydrated")
    
    engine = QAEngine(kg_model, MODEL_PATH)
    navigator = KGNavigator(kg_model)
    return engine, navigator, kg_model

try:
    engine, navigator, kg_model = load_engine()
except Exception as e:
    st.error(f"Error loading models: {e}")
    st.stop()

# Sidebar - Settings & Diagnostics
st.sidebar.title("🎛️ Control Panel")
top_k = st.sidebar.slider("Ranked results count", 1, 15, 5)
graph_depth = st.sidebar.slider("Subgraph graph depth", 1, 3, 1)
min_confidence = st.sidebar.slider("Min confidence score", 0.0, 1.0, 0.3)

st.sidebar.markdown("---")
st.sidebar.subheader("🖥️ System Info")
# Device Info
import torch
from src.utils.device_utils import get_device
current_device = get_device(verbose=False).upper()
st.sidebar.info(f"**Device:** {current_device}")

# LLM Info
from src.agents.AgentDriver import AgentDriverConfig
llm_cfg = AgentDriverConfig()
st.sidebar.info(f"**LLM:** {llm_cfg.name.capitalize()}")

# KG Stats
stats = kg_model.count_items()
st.sidebar.write(f"📊 **Nodes:** {stats['graph_info']['nodes']}")
st.sidebar.write(f"📊 **Triplets:** {stats['graph_info']['triplets']}")

# Main Search
query = st.text_input("💬 Ask a question about the graph:", placeholder="e.g., When was Albert Einstein born?")

if query:
    with st.spinner("🔍 Reasoning over the Knowledge Graph..."):
        results = engine.get_ranked_results(query, top_k=top_k)
        
    # Sidebar - Last Query Debug
    if hasattr(engine, 'last_extraction'):
        st.sidebar.markdown("---")
        st.sidebar.subheader("🧪 Debug Diagnostics")
        st.sidebar.write("**Extracted Entities:**")
        st.sidebar.code(", ".join(engine.last_extraction['entities']))
        if engine.last_extraction['mapped_ids']:
            st.sidebar.write("**Mapped WD IDs:**")
            st.sidebar.code(", ".join(engine.last_extraction['mapped_ids']))
        st.sidebar.write(f"**Matched Nodes:** {len(engine.last_extraction['matched_node_ids'])}")

    # Filter by confidence
    results = [r for r in results if r['confidence'] >= min_confidence]

    if not results:
        st.warning("⚠️ No relevant information found in the graph.")
        st.info("💡 Try adjusting the 'Min confidence score' in the sidebar or check if the entities are in the dataset.")
    else:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("🏆 Top Ranked Facts")
            for i, res in enumerate(results):
                with st.expander(f"#{i+1}: {res['confidence']:.2%}", expanded=(i==0)):
                    st.markdown(f"**Fact:** `{res['text']}`")
                    st.progress(res['confidence'])
                    st.caption(f"ID: {res['triplet'].id[:8]}...")
                    
        with col2:
            st.subheader("🕸️ Interactive Subgraph")
            # Extract neighborhood
            seed_nodes = []
            for res in results:
                seed_nodes.append(res['triplet'].start_node.id)
                seed_nodes.append(res['triplet'].end_node.id)
            
            neighborhood = navigator.get_neighborhood(list(set(seed_nodes)), depth=graph_depth)
            nx_graph = navigator.triplets_to_nx(neighborhood)
            
            if len(nx_graph) == 0:
                st.info("No connections found for visualization.")
            else:
                net = Network(height="600px", width="100%", bgcolor="#0E1117", font_color="white", directed=True)
                
                for node, attrs in nx_graph.nodes(data=True):
                    # Check if node name or id is a Wikidata ID
                    label = attrs['label']
                    title = f"Type: {attrs['type']}"
                    color = "#2ECC71" if attrs['type'] == "object" else "#3498DB"
                    
                    # Try to map label if it's an ID
                    if label.startswith('Q') and label[1:].isdigit():
                        mapped_label = engine.mapper.get_label(label)
                        if mapped_label != label:
                            label = f"{mapped_label} ({label})"
                    
                    net.add_node(node, label=label, title=title, color=color)
                    
                for source, target, attrs in nx_graph.edges(data=True):
                    edge_label = attrs['label']
                    if attrs.get('time'):
                        edge_label += f"\n({attrs['time']})"
                    net.add_edge(source, target, label=edge_label, title=f"Relation: {attrs['label']}\nTime: {attrs.get('time', 'N/A')}", color="#F1C40F")
                
                net.set_options("""
                var options = {
                  "edges": {
                    "arrows": { "to": { "enabled": true } },
                    "color": { "inherit": true },
                    "smooth": {"type": "curvedCW", "roundness": 0.2},
                    "font": {"size": 10, "strokeWidth": 2, "strokeColor": "#000000"}
                  },
                  "physics": {
                    "stabilization": { "iterations": 100 },
                    "barnesHut": { "gravitationalConstant": -8000, "springLength": 200 }
                  }
                }
                """)
            
            # Save and read as HTML
            path = "tmp_graph.html"
            net.save_graph(path)
            with open(path, 'r', encoding='utf-8') as f:
                html_data = f.read()
            components.html(html_data, height=650)
            os.remove(path)

st.markdown("---")
st.caption("Powered by Finetuned E5-Small & Personal-AI Graph Engine")
