"""Merge immutable graph layer snapshots without promoting candidate evidence."""
import hashlib
from pathlib import Path
from .graph import GraphSnapshot

def merge_snapshots(paths):
    paths=[Path(p) for p in paths]
    if not paths:raise ValueError('At least one layer snapshot is required')
    layers=[GraphSnapshot.load(p) for p in paths]
    # Production is an explicit conjunction, never inferred from a nonempty graph.
    present={g.metadata.get('layer') for g in layers}
    ready={'fact','ontology','rule'}<=present and all(
        g.metadata.get('production_ready') is True and bool(g.nodes)
        and all(n['verified'] and n['properties'].get('temporal_status')!='unresolved' for n in g.nodes.values())
        and all(e['verified'] for e in g.edges.values()) for g in layers)
    graph=GraphSnapshot(metadata={'layer':'merged','production_ready':ready,
        'status':'ready' if ready else 'candidate_only',
        'source_snapshots':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                             'metadata':g.metadata} for p,g in zip(paths,layers)]})
    for layer in layers:
        for node in layer.nodes.values():graph.add_node(node)
    for layer in layers:
        for edge in layer.edges.values():graph.add_edge(edge)
    graph.validate()
    return graph
