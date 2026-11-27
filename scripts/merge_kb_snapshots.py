"""Assemble graph layers. Explicit output path, refuses overwrite of an existing run."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from vnlegal.kb_snapshot import merge_snapshots

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('inputs',nargs='+');p.add_argument('--output',required=True);a=p.parse_args()
    target=Path(a.output).resolve()
    if not target.is_relative_to(ROOT):raise ValueError('Output must be inside repository')
    if target.exists():raise FileExistsError(target)
    graph=merge_snapshots(a.inputs);graph.save(target);print(graph.validate())
