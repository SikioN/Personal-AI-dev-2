import numpy as np
import torch
import os
from typing import List, Dict, Tuple
from src.kg_model.knowledge_graph_model import KnowledgeGraphModel
from src.utils.data_structs import Triplet, TripletCreator
from src.db_drivers.vector_driver import VectorDBInstance
from src.pipelines.qa.kg_reasoning.medium_reasoner.entities_extractor import EntitiesExtractor, EntitiesExtractorConfig
from src.pipelines.qa.kg_reasoning.medium_reasoner.entities2nodes_matching import Entities2NodesMatcher, Entities2NodesMatcherConfig
from src.utils.kg_navigator import KGNavigator

class QAEngine:
    """Core engine for KG QA with ranking and confidence scoring."""
    def __init__(self, kg_model: KnowledgeGraphModel, finetuned_model_path: str):
        self.kg_model = kg_model
        
        # Override embedder with finetuned weights
        from sentence_transformers import SentenceTransformer
        from src.utils.device_utils import get_device
        
        # Check if the path exists locally
        if os.path.exists(finetuned_model_path):
            finetuned_model_path = os.path.abspath(finetuned_model_path)
        else:
            print(f"Model path {finetuned_model_path} not found locally, assuming HuggingFace model name.")

        # Use dynamic device detection for the transformer
        device = get_device()
        self.kg_model.embeddings_struct.embedder.config.model_name_or_path = finetuned_model_path
        self.kg_model.embeddings_struct.embedder.config.device = device
        self.kg_model.embeddings_struct.embedder.model = SentenceTransformer(
            finetuned_model_path, 
            device=device
        )

        self.entities_extractor = EntitiesExtractor()
        self.nodes_matcher = Entities2NodesMatcher(self.kg_model)
        
        # Load Wikidata Mapper
        from src.utils.wikidata_utils import WikidataMapper
        kg_data_path = os.path.join(os.getcwd(), "wikidata_big/kg")
        self.mapper = WikidataMapper(kg_data_path)

    def get_ranked_results(self, query: str, top_k: int = 5) -> List[Dict]:
        """Process query and return ranked triplets with confidence scores."""
        # 1. Extract entities with fallback
        try:
            entities, info = self.entities_extractor.perform(query)
        except Exception as e:
            entities = [query]
            import re
            words = re.findall(r'[A-Z][a-z]+', query)
            if words:
                entities.extend(words)
            entities = list(set(entities))
            
        if not entities:
            entities = [query]

        # 2. Match to nodes (Names and Mapped IDs)
        # We'll search for original entities AND their mapped IDs
        mapped_ids = []
        for ent in entities:
            wd_id = self.mapper.get_id(ent)
            if wd_id:
                mapped_ids.append(wd_id)
        
        # Combine everything for search
        search_candidates = list(set(entities + mapped_ids))
        
        all_matched_nodes = []

        # Optimization: Try literal lookup for mapped IDs first (Perfect Match)
        for mid in mapped_ids:
            # We need to find the internal ID for this WD ID
            # In InMemoryGraphConnector, we can check strid_nodes_index
            try:
                # This is a bit of a hack to access the connector directly, but efficient
                connector = self.kg_model.graph_struct.db_conn
                internal_ids = connector.strid_nodes_index.get(mid)
                if internal_ids:
                    for iid in internal_ids:
                        if iid in connector.nodes:
                            all_matched_nodes.append(connector.nodes[iid])
            except Exception:
                pass

        # Match to KG nodes using vector search/matcher for the rest
        matched_nodes_dict, info = self.nodes_matcher.perform(search_candidates)
        for nodes in matched_nodes_dict.values():
            # Resolve VectorDBInstance to Graph Node
            connector = self.kg_model.graph_struct.db_conn
            for n in nodes:
                if hasattr(n, 'id') and n.id in connector.nodes:
                    all_matched_nodes.append(connector.nodes[n.id])
                elif hasattr(n, 'name'): # Already a Node
                     all_matched_nodes.append(n)
                # If it's a VectorDBInstance but NOT in graph (shouldn't happen with aligned IDs), we ignore it 
                # because we can't traverse from it.
        
        # Deduplicate nodes by ID
        unique_nodes = {}
        for n in all_matched_nodes:
            unique_nodes[n.id] = n
        all_matched_nodes = list(unique_nodes.values())


        # DEBUG: Store mapped info for UI
        self.last_extraction = {
            'entities': entities,
            'mapped_ids': mapped_ids,
            'matched_node_ids': [n.id for n in all_matched_nodes],
            'matched_node_names': [n.name for n in all_matched_nodes]
        }

        if not all_matched_nodes:
            # Last resort: try to find anything in the vector DB that matches the query significantly
            # We bypass the matcher and go straight to the vector DB
            print(f"DEBUG: Triggering vector fallback for query: '{query}'")
            query_emb = self.kg_model.embeddings_struct.embedder.encode_queries([query])[0]
            raw_node_search = self.kg_model.embeddings_struct.vectordbs['nodes'].retrieve(
                query_instances=[VectorDBInstance(embedding=query_emb)],
                n_results=10, includes=['documents'])[0]
            
            # results are list of (distance, Node)
            # We pick those with distance < 0.6 (fine-tuned E5 usually gives low distance for good matches)
            # Relaxed threshold to 0.75 for better recall
            all_matched_nodes = [res[1] for res in raw_node_search if res[0] < 0.75]
            if all_matched_nodes:
                 print(f"DEBUG: Vector fallback found nodes: {[n.id for n in all_matched_nodes]}")
                 self.last_extraction['fallback_triggered'] = True
                 self.last_extraction['matched_node_ids'] = [n.id for n in all_matched_nodes]

        if not all_matched_nodes:
            return []

        # 3. Retrieve relevant triplets
        node_ids = [n.id for n in all_matched_nodes]
        nav = KGNavigator(self.kg_model)
        candidate_triplets = nav.get_neighborhood(node_ids, depth=1)
        
        if not candidate_triplets:
            return []

        # Remove duplicates
        seen_t_ids = set()
        unique_candidates = []
        for t in candidate_triplets:
            if t.id not in seen_t_ids:
                unique_candidates.append(t)
                seen_t_ids.add(t.id)

        # 4. Rank using E5
        query_emb = self.kg_model.embeddings_struct.embedder.encode_queries([query])[0]
        
        # Stringify triplets for ranking
        triplet_texts = []
        for t in unique_candidates:
            _, text = TripletCreator.stringify(t)
            triplet_texts.append(text)
            
        triplet_embs = self.kg_model.embeddings_struct.embedder.encode_passages(triplet_texts)
        
        results = []
        for t, text, emb in zip(unique_candidates, triplet_texts, triplet_embs):
            # Cosine similarity
            score = np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb))
            # Normalize score to approx confidence [0, 1]
            confidence = float(max(0, score)) 
            
            results.append({
                'triplet': t,
                'text': text,
                'confidence': confidence
            })
            
        # Sort by confidence
        results.sort(key=lambda x: x['confidence'], reverse=True)
        return results[:top_k]
