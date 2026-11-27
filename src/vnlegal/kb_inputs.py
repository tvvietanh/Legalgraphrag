"""Literal, source-spanned legal units. This module does not decide applicability."""
import hashlib
import re

VERSION = 'kb-literal-law-inputs-0.1'
ARTICLE = re.compile(r'(?m)^Điều\s+(\d+[a-zđ]?)\.\s*([^\n]*)')
CLAUSE = re.compile(r'(?m)^[“]?(\d+)\.(?:\[\^\d+\])?\s+')
POINT = re.compile(r'(?m)^[“]?([a-zđ])\)(?:\[\^\d+\])?\s*')
SECTION = re.compile(r'(?m)^(?:Chương\s+[IVXLCDM]+|Mục\s+\d+|Phần thứ)\b')

def sha_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def legal_units(text, document_id, version_id, source_path, source_hash, provenance):
    """Return article/clause/point candidates with exact offsets in the supplied TXT.

    Footnotes are separate from body; brackets in superscripts are not clause
    digits. Chapter headings following an article are not part of that article.
    """
    body_end=text.find('CHÚ THÍCH GỐC')
    if body_end<0:body_end=len(text)
    heads=list(ARTICLE.finditer(text,0,body_end));rows=[]
    def row(start,end,article,clause=None,point=None,parent=None,title=None):
        while end>start and text[end-1].isspace():end-=1
        identifier=version_id+':article:'+article
        if clause is not None:identifier+=':clause:'+clause
        if point is not None:identifier+=':point:'+point
        quote=text[start:end]
        return dict(schema_version=VERSION,article_version_id=identifier,
                    law_document_id=document_id,law_version_id=version_id,
                    article_number=article,clause_number=clause,point_number=point,
                    parent_article_version_id=parent,title=title,text=quote,
                    effective_from=None,effective_to=None,temporal_status='unresolved',
                    amending_document_ids=None,review_status='needs_review',
                    reviewer_id=None,reviewed_at=None,verified=False,
                    provenance=provenance,
                    evidence=[dict(source_id=source_path,text_revision=source_hash,
                                   text_sha256=source_hash,start=start,end=end,quote=quote)])
    for i,head in enumerate(heads):
        end=heads[i+1].start() if i+1<len(heads) else body_end
        structural=SECTION.search(text,head.end(),end)
        if structural:end=structural.start()
        article=row(head.start(),end,head[1],title=head[2]);rows.append(article)
        clauses=list(CLAUSE.finditer(text,head.end(),end))
        # Sequence anomalies are visible; no ordinal or label is silently repaired.
        clause_sequence=[m[1] for m in clauses]
        article['clause_sequence_status']='sequential' if clause_sequence==list(map(str,range(1,len(clauses)+1))) else 'needs_review'
        for j,cm in enumerate(clauses):
            ce=clauses[j+1].start() if j+1<len(clauses) else end
            cr=row(cm.start(),ce,head[1],cm[1],parent=article['article_version_id']);rows.append(cr)
            pts=list(POINT.finditer(text,cm.end(),ce))
            for k,pm in enumerate(pts):
                pe=pts[k+1].start() if k+1<len(pts) else ce
                rows.append(row(pm.start(),pe,head[1],cm[1],pm[1],cr['article_version_id']))
    return rows

def validate_units(rows,sources):
    seen=set()
    for r in rows:
        if r['article_version_id'] in seen:raise ValueError('Duplicate legal unit '+r['article_version_id'])
        seen.add(r['article_version_id'])
        for e in r['evidence']:
            text=sources[e['source_id']]
            if sha_text(text)!=e['text_sha256'] or text[e['start']:e['end']]!=e['quote']:
                raise ValueError('Invalid evidence span')
        if r['verified'] or r['review_status']!='needs_review' or r['temporal_status']!='unresolved':
            raise ValueError('Literal extraction cannot approve legal meaning')
    for r in rows:
        if r['parent_article_version_id'] and r['parent_article_version_id'] not in seen:
            raise ValueError('Missing parent')
