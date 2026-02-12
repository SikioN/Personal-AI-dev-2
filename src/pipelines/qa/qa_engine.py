import numpy as np
import torch
import os
from typing import List, Dict, Tuple
from src.kg_model.knowledge_graph_model import KnowledgeGraphModel
from src.utils.data_structs import Quadruplet, QuadrupletCreator
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
        # Fix path resolution: use absolute path based on this file's location
        # qa_engine.py is in src/pipelines/qa/, so we go up 3 levels to project root
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
        kg_data_path = os.path.join(project_root, "wikidata_big/kg")
        
        if not os.path.exists(kg_data_path):
             print(f"WARNING: [QAEngine] Wikidata KG path not found at {kg_data_path}")
             # Fallback to CWD just in case
             kg_data_path = os.path.join(os.getcwd(), "wikidata_big/kg")

        print(f"DEBUG: [QAEngine] Initializing WikidataMapper with path: {kg_data_path}")
        self.mapper = WikidataMapper(kg_data_path)
        
        # Initialize Temporal Scorer
        self.temporal_scorer = None
        try:
            from src.kg_model.temporal.temporal_model import TemporalScorer
            self.temporal_scorer = TemporalScorer(device=get_device())
        except Exception as e:
            print(f"Warning: Could not initialize TemporalScorer: {e}")

        # Initialize Ollama Client
        try:
            from src.llm.ollama_client import OllamaClient
            self.ollama_client = OllamaClient(model="llama3.2")
        except Exception as e:
            print(f"Warning: Could not initialize OllamaClient: {e}")
            self.ollama_client = None

    def get_ranked_results(self, query: str, top_k: int = 5) -> List[Dict]:
        """Process query and return ranked quadruplets with confidence scores."""
        # 1. Extract entities with fallback
        # 1. Extract entities (Hybrid: Ollama First, then Regex Fallback)
        query_time = None
        entities = []
        relation_hint = None
        
        if self.ollama_client:
            try:
                ollama_params = self.ollama_client.extract_search_parameters(query)
                # Handle list of entities
                extracted_entities = ollama_params.get("entities", [])
                if isinstance(extracted_entities, list):
                    entities.extend(extracted_entities)
                elif isinstance(extracted_entities, str):
                    entities.append(extracted_entities)
                    
                # Retro-compatibility if 'entity' key is still used
                if ollama_params.get("entity"):
                     entities.append(ollama_params.get("entity"))
                
                # Deduplicate
                entities = list(set(entities))

                if ollama_params.get("time"):  
                    query_time = ollama_params["time"]
                if ollama_params.get("relation"):
                    relation_hint = ollama_params["relation"]
                
                print(f"DEBUG: [Ollama] Entities: {entities}, Time: {query_time}, Relation: {relation_hint}")
            except Exception as e:
                print(f"DEBUG: [Ollama] Extraction failed: {e}")

        # Fallback to Regex / Old Extractor if Ollama missed
        if not entities:
            print("DEBUG: [Fallback] triggering Regex/Legacy extraction...")
            try:
                extraction_result, info = self.entities_extractor.perform(query)
                # Check if result is dict (new format) or list (old/fallback)
                if isinstance(extraction_result, dict):
                    entities = extraction_result.get('entities', [])
                    if not query_time: # Only if not already found by Ollama
                        query_time = extraction_result.get('time')
                else:
                    entities = extraction_result
            except Exception as e:
                entities = [query]
                import re
                words = re.findall(r'[A-Z][a-z]+', query)
                if words:
                    entities.extend(words)
                entities = list(set(entities))
            
            print(f"DEBUG: [Fallback] Entities found: {entities}")
            
            if not entities:
                entities = [query]
                print(f"DEBUG: [Fallback] No entities found, using full query as entity: {entities}")

        # 2. Match to nodes (Names and Mapped IDs)
        # We'll search for original entities AND their mapped IDs
        mapped_ids = []
        for ent in entities:
            wd_id = self.mapper.get_id(ent)
            print(f"DEBUG: [Mapper] '{ent}' -> Wikidata ID: {wd_id}")
            if wd_id:
                mapped_ids.append(wd_id)
        
        # Combine everything for search
        search_candidates = list(set(entities + mapped_ids))
        
        all_matched_nodes = []

        # Optimization: Try literal lookup for mapped IDs first (Perfect Match)
        valid_db_ids = []
        for mid in mapped_ids:
            # We need to find the internal ID for this WD ID
            # In InMemoryGraphConnector, we can check strid_nodes_index
            try:
                # This is a bit of a hack to access the connector directly, but efficient
                connector = self.kg_model.graph_struct.db_conn
                
                # Handling Neo4jConnector which doesn't expose internal index
                if hasattr(connector, 'execute_query'):
                    # Fetch by str_id (which is Wikidata ID)
                    raw_output = connector.execute_query(f'MATCH (n) WHERE n.str_id = "{mid}" RETURN n')
                    if raw_output:
                         matched_nodes = connector.parse_query_nodes_output(raw_output)
                         for node in matched_nodes:
                             all_matched_nodes.append(node)
                             print(f"DEBUG: [Graph Match (Neo4j)] Found node: {node.name} (ID: {node.id})")
                         valid_db_ids.append(mid)
                
                # Handling InMemoryGraphConnector
                elif hasattr(connector, 'strid_nodes_index'):
                    internal_ids = connector.strid_nodes_index.get(mid)
                    print(f"DEBUG: [Graph Lookup] ID '{mid}' -> Internal IDs: {internal_ids}")
                    if internal_ids:
                        for iid in internal_ids:
                            if iid in connector.nodes:
                                node = connector.nodes[iid]
                                all_matched_nodes.append(node)
                                print(f"DEBUG: [Graph Match] Found node: {node.name} (ID: {node.id})")
            except Exception as e:
                print(f"DEBUG: [Graph Lookup Error] {e}")
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

        # 3. Retrieve relevant quadruplets
        if valid_db_ids:
             node_ids = valid_db_ids
        else:
             node_ids = [n.id for n in all_matched_nodes]

        print(f"DEBUG: [QAEngine] Navigating from IDs: {node_ids}")
        nav = KGNavigator(self.kg_model)
        candidate_quadruplets = nav.get_neighborhood(node_ids, depth=1)
        
        if not candidate_quadruplets:
            return []

        # Remove duplicates
        seen_q_ids = set()
        unique_candidates = []
        for q in candidate_quadruplets:
            if q.id not in seen_q_ids:
                unique_candidates.append(q)
                seen_q_ids.add(q.id)

        # 4. Rank using E5
        query_emb = self.kg_model.embeddings_struct.embedder.encode_queries([query])[0]
        
        # Stringify quadruplets for ranking
        quadruplet_texts = []
        for q in unique_candidates:
            _, text = QuadrupletCreator.stringify(q)
            quadruplet_texts.append(text)
            
        quadruplet_embs = self.kg_model.embeddings_struct.embedder.encode_passages(quadruplet_texts)
        
        results = []
        
        # Normalize TComplex score using sigmoid
        def sigmoid(x):
            return 1 / (1 + np.exp(-x))

        for q, text, emb in zip(unique_candidates, quadruplet_texts, quadruplet_embs):
            # Cosine similarity
            score = np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb))
            e5_confidence = float(max(0, score))
            
            final_confidence = e5_confidence
            
            # Temporal Re-ranking
            temporal_debug = None
            
            # Decide which time to score against
            scoring_time = query_time
            if not scoring_time and q.time and q.time.name not in ["Always", "Unknown"]:
                # If query has no time, but the fact has a time, check validity AT THAT TIME
                raw_time = q.time.name
                if ' - ' in raw_time:
                     scoring_time = raw_time.split(' - ')[0]
                else:
                     scoring_time = raw_time
                
            if scoring_time and self.temporal_scorer:
                s_qid = q.start_node.prop.get('wd_id')
                if not s_qid:
                    s_qid = self.mapper.get_id(q.start_node.name)
                
                r_pid = q.relation.prop.get('wd_id')
                # For relations, name might not map directly if it's "spouse" -> P26. Mapper handles this?
                # We assume mapper can handle relation names or we need a relation mapper.
                # Usually mapper.get_id works for entities. For relations it might be trickier if names are "spouse".
                # Let's try mapper.get_id first.
                if not r_pid:
                    r_pid = self.mapper.get_id(q.relation.name)

                o_qid = q.end_node.prop.get('wd_id')
                if not o_qid:
                    o_qid = self.mapper.get_id(q.end_node.name)
                
                if s_qid and r_pid and o_qid:
                    try:
                        # print(f"DEBUG: [TemporalScorer] S:{s_qid}, R:{r_pid}, O:{o_qid}, T:{scoring_time}")
                        t_score_logit = self.temporal_scorer.score(s_qid, r_pid, o_qid, scoring_time)
                        # print(f"DEBUG: [TemporalScorer] Logit: {t_score_logit}")
                        if t_score_logit > -9.0: # Check if entities were known (-10.0 fallback)
                            t_prob = sigmoid(t_score_logit)
                            final_confidence = (e5_confidence * 0.7) + (t_prob * 0.3)
                            temporal_debug = f"{t_prob:.2f} (Logit: {t_score_logit:.2f})"
                        else:
                             # print("DEBUG: [TemporalScorer] Entity/Relation unknown to scorer")
                             temporal_debug = "None (Unknown to Scorer)"
                    except Exception as e:
                        # print(f"Error in temporal scoring: {e}")
                        temporal_debug = "Error"
                else:
                     # print(f"DEBUG: [TemporalScorer] Missing QIDs. S:{s_qid}, R:{r_pid}, O:{o_qid}")
                     pass
            
            # Semantic Boost if Relation matches Ollama hint
            if relation_hint and relation_hint.lower() in q.relation.name.lower():
                 final_confidence = min(1.0, final_confidence * 1.2) # 20% boost
                 semantic_debug = f"{e5_confidence:.2f} (+RelBoost)"
            else:
                 semantic_debug = f"{e5_confidence:.2f}"
                
            results.append({
                'quadruplet': q,
                'text': text,
                'confidence': final_confidence,
                'temporal_score': temporal_debug,
                'semantic_score': semantic_debug
            })
            
        # Sort by confidence
        results.sort(key=lambda x: x['confidence'], reverse=True)
        return results[:top_k]
