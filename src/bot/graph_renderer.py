"""Render a KG subgraph to a PNG BytesIO using matplotlib (non-interactive, thread-safe)."""
import matplotlib
matplotlib.use('Agg')  # Must be first — non-interactive backend

import io
import textwrap
import networkx as nx
import matplotlib.pyplot as plt
from typing import List

MAX_EDGES = 15  # Cap to keep graph readable and prevent overcrowding

def render_subgraph(quadruplets: List) -> io.BytesIO:
    """Convert quadruplets → NetworkX graph → PNG bytes using an advanced dark theme.

    Returns a BytesIO with the PNG image, seeked to position 0.
    """
    if not quadruplets:
        return _empty_image("No graph data to display.")

    G = nx.DiGraph()

    # Build the graph
    for q in quadruplets[:MAX_EDGES]:
        s_id = q.start_node.id
        o_id = q.end_node.id
        s_label = q.start_node.name or s_id
        o_label = q.end_node.name or o_id
        rel = q.relation.name or ""
        
        t_name = q.time.name if q.time else ""
        
        # Wrap long relation text
        r_wrapped = "\n".join(textwrap.wrap(rel, width=20))
        edge_label = f"{r_wrapped}\n({t_name})" if t_name and t_name != 'Always' else r_wrapped
        
        # Add edges and nodes (store full label for rendering)
        G.add_edge(s_label, o_label, label=edge_label)

    if len(G) == 0:
        return _empty_image("Graph built but no nodes found.")

    # --- ADVANCED STYLING (Dark Theme with Adaptive Capsules) ---
    BG_COLOR = "#0D1117"         # GitHub Dark background
    TEXT_COLOR = "#E6EDF3"       # Light text
    NODE_BG = "#1F2428"          # Dark gray capsules
    NODE_BORDER = "#444C56"      # Capsule border
    EDGE_COLOR = "#58A6FF"       # Neon blue edges
    EDGE_TEXT_BG = "#0D1117"     # Edge text background (matches main BG)
    EDGE_TEXT_COLOR = "#8B949E"  # Muted edge text

    plt.figure(figsize=(14, 10), facecolor=BG_COLOR)
    
    # Layout (k=2.0 spaces nodes out more)
    pos = nx.spring_layout(G, k=2.0, seed=42)
    
    # 1. Draw Edges with curved lines
    nx.draw_networkx_edges(
        G, pos, 
        edge_color=EDGE_COLOR, 
        alpha=0.6, 
        arrows=True,
        arrowsize=20, 
        width=1.5, 
        connectionstyle="arc3,rad=0.15",
        node_size=10  # minimize distance of arrow from center
    )
    
    # 2. Draw Edge Labels with background boxes
    edge_labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(
        G, pos, 
        edge_labels=edge_labels, 
        font_size=9, 
        font_color=EDGE_TEXT_COLOR,
        font_family="sans-serif",
        bbox=dict(
            boxstyle="round,pad=0.3", 
            facecolor=EDGE_TEXT_BG, 
            edgecolor="none", 
            alpha=0.9
        )
    )
    
    # 3. Draw Nodes as pure text with bounding boxes (creating perfect capsules)
    for node, (x, y) in pos.items():
        wrapped_name = "\n".join(textwrap.wrap(node, width=25))
        
        plt.text(
            x, y, 
            wrapped_name,
            fontsize=11,
            fontweight="medium",
            color=TEXT_COLOR,
            ha='center', 
            va='center',
            family='sans-serif',
            bbox=dict(
                boxstyle="round,pad=0.5",
                facecolor=NODE_BG,
                edgecolor=NODE_BORDER,
                linewidth=1,
                alpha=1.0
            )
        )

    plt.axis("off")
    plt.tight_layout()
    
    buf = io.BytesIO()
    # High DPI for crisp text
    plt.savefig(buf, format='png', dpi=250, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()
    buf.seek(0)
    return buf


def _empty_image(message: str) -> io.BytesIO:
    BG_COLOR = "#0D1117"
    TEXT_COLOR = "#8B949E"
    
    fig, ax = plt.subplots(figsize=(6, 2), facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.text(0.5, 0.5, message, ha='center', va='center', fontsize=12, color=TEXT_COLOR)
    ax.axis('off')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close(fig)
    buf.seek(0)
    return buf
