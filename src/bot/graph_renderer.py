"""Render a KG subgraph to a PNG BytesIO using matplotlib (non-interactive, thread-safe)."""
import matplotlib
matplotlib.use('Agg')  # Must be first — non-interactive backend

import io
import networkx as nx
import matplotlib.pyplot as plt
from typing import List


MAX_EDGES = 30  # Cap to keep graph readable


def render_subgraph(quadruplets: List) -> io.BytesIO:
    """Convert quadruplets → NetworkX graph → PNG bytes.

    Returns a BytesIO with the PNG image, seeked to position 0.
    """
    G = nx.DiGraph()

    for q in quadruplets[:MAX_EDGES]:
        s_id = q.start_node.id
        o_id = q.end_node.id
        s_label = q.start_node.name or s_id
        o_label = q.end_node.name or o_id
        rel = q.relation.name or ""
        time_str = ""
        if q.time and q.time.name not in ("Always", "", None):
            time_str = f"\n({q.time.name})"

        G.add_node(s_id, label=s_label, ntype=str(q.start_node.type))
        G.add_node(o_id, label=o_label, ntype=str(q.end_node.type))
        G.add_edge(s_id, o_id, label=f"{rel}{time_str}")

    if len(G) == 0:
        return _empty_image("No graph data to display.")

    node_colors = [
        "#2ECC71" if G.nodes[n].get('ntype') == "object" else "#3498DB"
        for n in G.nodes()
    ]
    labels = {n: G.nodes[n].get('label', n) for n in G.nodes()}
    edge_labels = {(u, v): d['label'] for u, v, d in G.edges(data=True)}

    fig, ax = plt.subplots(figsize=(12, 8), facecolor='#1a1a2e')
    ax.set_facecolor('#1a1a2e')

    pos = nx.spring_layout(G, seed=42, k=2.0)
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=800,
                           alpha=0.9, ax=ax)
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8,
                            font_color='white', ax=ax)
    nx.draw_networkx_edges(G, pos, edge_color='#F1C40F', arrows=True,
                           arrowsize=15, ax=ax)
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels,
                                 font_size=6, font_color='#F1C40F', ax=ax)

    ax.axis('off')
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf


def _empty_image(message: str) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(6, 2))
    ax.text(0.5, 0.5, message, ha='center', va='center', fontsize=12)
    ax.axis('off')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=80, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf
