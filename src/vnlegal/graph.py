"""Versioned, provenance-bearing multigraph interchange shared by all KB layers.

JSON persistence deliberately avoids pickle and implicit node creation. Queries
return copies so retrieval consumers cannot mutate the stored evidence.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from pathlib import Path

SCHEMA_VERSION = 'vnlegal.graph.v1'


class GraphSnapshot:
    def __init__(self, metadata=None, nodes=None, edges=None):
        self.metadata = deepcopy(metadata or {})
        self.nodes = {}
        self.edges = {}
        for node in nodes or []:
            self.add_node(node)
        for edge in edges or []:
            self.add_edge(edge)

    @staticmethod
    def _record(record):
        item = deepcopy(record)
        for key in ['id', 'type']:
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f'Invalid {key}')
        if not isinstance(item.get('verified'), bool):
            raise ValueError('verified must be an explicit boolean')
        if not isinstance(item.get('properties', {}), dict):
            raise ValueError('properties must be an object')
        item.setdefault('properties', {})
        if not isinstance(item.get('provenance'), list) or not item['provenance']:
            raise ValueError('Nonempty provenance is required')
        if not all(isinstance(p, dict) and p for p in item['provenance']):
            raise ValueError('Each provenance item must be a nonempty object')
        # Enforce JSON interoperability and reject NaN/Infinity immediately.
        json.dumps(item, ensure_ascii=False, allow_nan=False)
        return item

    def add_node(self, node):
        item = self._record(node)
        existing = self.nodes.get(item['id'])
        if existing is not None and existing != item:
            raise ValueError('Conflicting node ID: ' + item['id'])
        self.nodes[item['id']] = item
        return item['id']

    def add_edge(self, edge):
        item = deepcopy(edge)
        if 'id' not in item:
            encoded = json.dumps(item, sort_keys=True, ensure_ascii=False, allow_nan=False)
            item['id'] = 'edge:' + hashlib.sha256(encoded.encode()).hexdigest()[:24]
        item = self._record(item)
        for endpoint in ['source', 'target']:
            if item.get(endpoint) not in self.nodes:
                raise ValueError('Unknown edge ' + endpoint)
        if item['verified'] and not all(self.nodes[item[k]]['verified'] for k in ['source','target']):
            raise ValueError('Verified edge cannot depend on candidate endpoints')
        existing = self.edges.get(item['id'])
        if existing is not None and existing != item:
            raise ValueError('Conflicting edge ID: ' + item['id'])
        self.edges[item['id']] = item
        return item['id']

    def get_node(self, node_id):
        return deepcopy(self.nodes.get(node_id))

    def query(self, node_type=None, verified_only=False, **property_filters):
        return [deepcopy(n) for n in self.nodes.values()
                if (node_type is None or n['type'] == node_type)
                and (not verified_only or n['verified'])
                and all(n['properties'].get(k) == v for k,v in property_filters.items())]

    def get_edges(self, source=None, target=None, edge_type=None, verified_only=False):
        return [deepcopy(e) for e in self.edges.values()
                if (source is None or e['source'] == source)
                and (target is None or e['target'] == target)
                and (edge_type is None or e['type'] == edge_type)
                and (not verified_only or (e['verified'] and all(self.nodes[e[k]]['verified'] for k in ['source','target'])))]

    def neighbors(self, node_id, edge_type=None, direction='out', verified_only=False):
        if direction not in ['out', 'in', 'both']:
            raise ValueError('direction must be out, in or both')
        if node_id not in self.nodes:
            return []
        ids = []
        for edge in self.get_edges(edge_type=edge_type, verified_only=verified_only):
            if direction in ['out','both'] and edge['source'] == node_id:
                ids.append(edge['target'])
            if direction in ['in','both'] and edge['target'] == node_id:
                ids.append(edge['source'])
        return [self.get_node(i) for i in dict.fromkeys(ids)]

    def validate(self):
        # Reconstruct through public guards to catch corruption via public dicts.
        GraphSnapshot(self.metadata, list(self.nodes.values()), list(self.edges.values()))
        return {'nodes': len(self.nodes), 'edges': len(self.edges),
                'verified_nodes': sum(n['verified'] for n in self.nodes.values()),
                'verified_edges': sum(e['verified'] for e in self.edges.values())}

    def to_dict(self):
        self.validate()
        return deepcopy({'schema_version': SCHEMA_VERSION, 'metadata': self.metadata,
                         'nodes': sorted(self.nodes.values(), key=lambda n:n['id']),
                         'edges': sorted(self.edges.values(), key=lambda e:e['id'])})

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')

    @classmethod
    def load(cls, path):
        value = json.loads(Path(path).read_text(encoding='utf-8'))
        if value.get('schema_version') != SCHEMA_VERSION:
            raise ValueError('Unsupported graph schema')
        return cls(value.get('metadata'), value['nodes'], value['edges'])
