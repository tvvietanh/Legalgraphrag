"""Validate the Task4 proposed law records; no legal approval or runtime migration."""
from datetime import date,datetime
import hashlib
import json
import re
from pathlib import Path
import unicodedata
from jsonschema import Draft202012Validator,FormatChecker

ROOT=Path(__file__).resolve().parents[2]
SCHEMA=ROOT/'schemas/law-v1-draft/law-record.schema.json'

def validate_bundle(records,sources):
    schema=json.loads(SCHEMA.read_text());Draft202012Validator.check_schema(schema)
    validator=Draft202012Validator(schema,format_checker=FormatChecker())
    hashes={k:hashlib.sha256(v.encode()).hexdigest() for k,v in sources.items()}
    def evidence(items):
        for e in items:
            text=sources[e['source_id']]
            if hashes[e['source_id']]!=e['text_sha256'] or not 0<=e['start']<e['end']<=len(text) or text[e['start']:e['end']]!=e['quote']:raise ValueError('Evidence hash/span/quote mismatch')
    docs={};units={};notes={};identifiers=set()
    for r in records:
        json.dumps(r,allow_nan=False);validator.validate(r)
        stamp=r['review']['reviewed_at']
        if stamp is not None:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})',stamp) or datetime.fromisoformat(stamp.replace('Z','+00:00')).tzinfo is None:raise ValueError('Review timestamp needs RFC3339 timezone')
        kind=r['record_type']
        key=r[{'document':'document_id','legal_unit':'unit_id','guidance':'guidance_id','footnote':'footnote_id'}[kind]]
        if key in identifiers:raise ValueError('Duplicate ID')
        identifiers.add(key)
        if kind=='document':docs[key]=r
        if kind=='legal_unit':units[key]=r
        if kind=='footnote':notes[key]=r
        if kind!='document':
            evidence(r['evidence'])
            if r['text']!='\n\n'.join(e['quote'] for e in r['evidence']):raise ValueError('Text must equal ordered source quotes')
            if not unicodedata.is_normalized('NFC',r['text']):raise ValueError('Text not NFC')
        temporal=r.get('temporal')
        if temporal and temporal['status']=='verified':
            evidence(temporal['basis_evidence'])
            start=date.fromisoformat(temporal['effective_from'])
            if temporal['effective_to'] and date.fromisoformat(temporal['effective_to'])<=start:raise ValueError('Invalid effective range')
            if kind in ['document','legal_unit'] and not r['legal_version_id']:raise ValueError('Verified temporal mapping needs legal version ID')
        if kind=='document':
            if (r['relations_status']=='not_processed')!=(r['relations'] is None):raise ValueError('Relations null/status mismatch')
            for link in r['relations'] or []:evidence(link['evidence'])
    snapshot_parts={}
    for doc in docs.values():
        snapshot=doc['text_snapshot'];seen_parts=set();parts={}
        for p in snapshot['ordered_parts']:
            if p['part_id'] in seen_parts:raise ValueError('Duplicate snapshot part')
            seen_parts.add(p['part_id'])
            if hashes.get(p['text_path'])!=p['text_sha256']:raise ValueError('Snapshot source hash mismatch')
            parts[p['text_path']]=p['text_sha256']
        if snapshot['text_review_status']=='approved' and not snapshot['text_approval_record']:raise ValueError('Missing text approval reference')
        snapshot_parts[(doc['document_id'],snapshot['snapshot_id'])]=parts
    for r in records:
        if r['record_type']=='document':continue
        k=(r['document_id'],r['snapshot_id'])
        if k not in snapshot_parts:raise ValueError('Unknown document snapshot')
        for e in r['evidence']:
            if snapshot_parts[k].get(e['source_id'])!=e['text_sha256']:raise ValueError('Evidence belongs to another snapshot')
        if r['record_type']=='legal_unit':
            label={'article':r'^Điều\s+'+re.escape(r['article_number'])+r'\.',
                   'clause':r'^[“]?'+re.escape(r['clause_number'] or '')+r'\.',
                   'point':r'^[“]?'+re.escape(r['point_label'] or '')+r'\)'}[r['unit_type']]
            if not re.match(label,r['text']):raise ValueError('Source label does not match unit numbers')
            for context in r['structure_context'].values():
                if context:
                    evidence(context['evidence'])
                    for e in context['evidence']:
                        if snapshot_parts[k].get(e['source_id'])!=e['text_sha256']:raise ValueError('Context belongs to another snapshot')
                    if context['label']!='\n\n'.join(e['quote'] for e in context['evidence']):raise ValueError('Context label not exact source quote')
            expected=r['snapshot_id']+':article:'+r['article_number']
            if r['clause_number'] is not None:expected+=':clause:'+r['clause_number']
            if r['point_label'] is not None:expected+=':point:'+r['point_label']
            if r['unit_id']!=expected:raise ValueError('ID does not match level/number')
            if r['parent_unit_id']:
                parent=units.get(r['parent_unit_id'])
                if not parent or parent['unit_type']!=('clause' if r['unit_type']=='point' else 'article'):raise ValueError('Invalid parent level')
                if any(parent[x]!=r[x] for x in ['document_id','snapshot_id','article_number']):raise ValueError('Cross-document/version parent')
                if r['unit_type']=='point' and parent['clause_number']!=r['clause_number']:raise ValueError('Wrong parent clause')
                for e in r['evidence']:
                    if not any(p['source_id']==e['source_id'] and p['start']<=e['start']<e['end']<=p['end'] for p in parent['evidence']):raise ValueError('Child span outside parent')
            for ref in r['footnote_refs']:
                if ref not in notes or notes[ref]['snapshot_id']!=r['snapshot_id']:raise ValueError('Unresolved footnote reference')
        if r['record_type']=='footnote':
            if not r['text'].startswith('[^'+r['label']+']:'):raise ValueError('Footnote label mismatch')
            if r['footnote_id']!=r['snapshot_id']+':part:'+r['part_id']+':footnote:'+r['label']:raise ValueError('Footnote identity mismatch')
            parts=[p for p in docs[r['document_id']]['text_snapshot']['ordered_parts'] if p['part_id']==r['part_id']]
            if len(parts)!=1 or any(e['source_id']!=parts[0]['text_path'] for e in r['evidence']):raise ValueError('Footnote source part mismatch')
        if r['record_type']=='guidance':
            expected_role='amending_instructions' if docs[r['document_id']]['document_kind']=='amendment' else 'implementation_resolution'
            if r['source_role']!=expected_role:raise ValueError('Guidance role/document mismatch')
            if (r['target_mapping_status']=='unresolved')!=(r['target_unit_ids'] is None):raise ValueError('Guidance null/status mismatch')
            for target in r['target_unit_ids'] or []:
                if target not in units:raise ValueError('Unknown guidance target')
    return dict(status='passed',records=len(records),documents=len(docs),legal_units=len(units),footnotes=len(notes),schema_status='proposal_not_user_accepted')
