"""Structural and source-span checks; never certifies legal meaning."""
from jsonschema import Draft202012Validator


def validate_enrichment(value,kind,schema,passage,source_text):
    if kind not in ('features','decision'):raise ValueError('Unknown extraction kind')
    Draft202012Validator(schema).validate(value)
    if value['case_id']!=passage['case_id']:raise ValueError('Case mismatch')
    a,b=passage['source_start'],passage['source_end']
    if type(a) is not int or type(b) is not int or not 0<=a<b<=len(source_text):
        raise ValueError('Invalid input passage bounds')
    if source_text[a:b]!=passage['text']:raise ValueError('Stale input passage')
    if any(not warning.strip() for warning in value['warnings']):raise ValueError('Blank warning')
    if kind=='features':
        groups=value['features'];field='dimension'
        if any(not text.strip() for group in groups.values() for text in group):raise ValueError('Blank feature')
        literals=None
    else:
        groups={name:value[name] for name in ('defendants','charges','law_mentions')};field='collection'
        ids=[item['local_id'] for item in groups['defendants']]
        if len(ids)!=len(set(ids)) or any(not i.strip() for i in ids):raise ValueError('Duplicate or blank defendant ID')
        for name in ('charges','law_mentions'):
            if any(item['defendant_local_id'] not in ids for item in groups[name]):
                raise ValueError('Unknown defendant reference')
        literals={'defendants':'name_as_written','charges':'charge_as_written','law_mentions':'mention_as_written'}
        if any(not item[literals[name]].strip() for name,items in groups.items() for item in items):
            raise ValueError('Blank literal extraction')
    required={(name,index) for name,items in groups.items() for index in range(len(items))}
    covered=set();seen=set()
    for evidence in value['evidence']:
        name,index=evidence[field],evidence['index'];start,end=evidence['start'],evidence['end']
        if (name,index) not in required:raise ValueError('Evidence index does not resolve')
        if not a<=start<end<=b:raise ValueError('Evidence outside approved input passage')
        if not source_text[start:end].strip():raise ValueError('Whitespace-only evidence')
        identity=(name,index,start,end)
        if identity in seen:raise ValueError('Duplicate evidence')
        seen.add(identity);covered.add((name,index))
        if literals and groups[name][index][literals[name]] not in source_text[start:end]:
            raise ValueError('Literal extraction does not match its evidence')
    if covered!=required:raise ValueError('Extraction item without evidence')
    if not required and not value['warnings']:raise ValueError('Empty extraction requires warning')
    return {'status':'technical_checks_passed','item_count':len(required),
            'evidence_count':len(seen),'semantic_review_required':True,'verified':False}
