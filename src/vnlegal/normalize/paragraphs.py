"""Conservative paragraph reconstruction with exact source ranges and NFC audit."""
from collections import Counter
from functools import lru_cache
import re
import statistics
import unicodedata

def compact(s):return ' '.join(unicodedata.normalize('NFC',s).split())
def chars(s):return ''.join(unicodedata.normalize('NFC',s).split())
MARKER=re.compile(r'^[“"\s]*(?:\[\d+[a-z]?\]|\d+[.)]\s|[a-zđ][)]\s|[-–•]\s)')
HEAD=re.compile(r'^(?:[“"]?Điều\s+\d+[a-zđ]?\.|CHƯƠNG\b|Chương\b|MỤC\b|Mục\b|PHẦN\b|Phần\b|NỘI DUNG|NHẬN ĐỊNH|NHẬN THẤY|XÉT THẤY|QUYẾT ĐỊNH|Nguồn án lệ|Vị trí nội dung|Khái quát nội dung|Quy định của pháp luật|Từ khóa|Từ khoá|Căn cứ\b|Nơi nhận\b)')
@lru_cache(maxsize=8192)
def heading(s):
    plain=re.sub(r'\[\^[^\]]+\]','',s)
    return bool(HEAD.match(s)) or bool(re.match(r'^Án lệ số\b',s)) or (len(plain)<180 and plain.isupper() and sum(c.isalpha() for c in plain)>3)

def text_paragraphs(source):
    """CBBA: preserve wording; only remove verified page markers/adjacent folios."""
    lines=[];cursor=0;page=None;page_window=0;removed=[]
    for number,raw in enumerate(source.splitlines(keepends=True),1):
        line=dict(line=number,start=cursor,end=cursor+len(raw),raw=raw,text=compact(raw),indent=len(raw)-len(raw.lstrip(' \t')))
        cursor+=len(raw);match=re.fullmatch(r'##\s*Page\s+(\d+)',line['text'])
        if match:
            page=int(match[1]);page_window=3;removed.append(dict(line,reason='cbba_page_marker',page=page));continue
        line['page_marker']=page
        if line['text'] and page_window:
            if line['text']==str(page):removed.append(dict(line,reason='matching_adjacent_page_folio'));page_window=0;continue
            page_window-=1
        lines.append(line)
    widths=[len(l['text']) for l in lines if len(l['text'])>45 and not heading(l['text'])]
    typical=statistics.median(widths) if widths else 100
    paras=[];current=[];blank=False
    def flush():
        if not current:return
        value=compact(' '.join(l['text'] for l in current));ranges=[]
        for l in current:
            if ranges and ranges[-1][1]==l['start']:ranges[-1][1]=l['end']
            else:ranges.append([l['start'],l['end']])
        paras.append(dict(text=value,source_ranges=ranges,kind='heading' if heading(current[0]['text']) else ('list_or_numbered' if MARKER.match(current[0]['text']) else 'paragraph')))
        current.clear()
    for line in lines:
        if not line['text']:blank=True;continue
        s=line['text'];new=heading(s) or bool(MARKER.match(s))
        if current:
            prev=current[-1];terminal=bool(re.search(r'[.;:!?][”"\)]?$',prev['text']))
            # Physical line ends alone are not paragraph boundaries.
            boundary=new or heading(current[0]['text']) or (terminal and (blank or line['indent']>=4 or len(prev['text'])<typical*.72))
            if boundary:flush()
        current.append(line);blank=False
    flush();output,maprows=assemble(paras)
    retained=''.join(source[a:b] for p in maprows for a,b in p['source_ranges'])
    if chars(retained)!=chars(output):raise ValueError('Paragraph reconstruction changed content')
    expected=Counter((l['start'],l['end']) for l in lines if l['text'])
    covered=Counter();ranges=[r for p in maprows for r in p['source_ranges']];j=0
    for l in lines:
        if not l['text']:continue
        while j<len(ranges) and ranges[j][1]<=l['start']:j+=1
        if j<len(ranges) and ranges[j][0]<=l['start'] and l['end']<=ranges[j][1]:covered[(l['start'],l['end'])]+=1
    if covered!=expected:raise ValueError('Missing or duplicated source line')
    return output,maprows,removed,dict(source_lines=len(lines)+len(removed),paragraphs=len(paras),removed_page_lines=len(removed),nfc_changed=unicodedata.normalize('NFC',source)!=source)

def assemble(paras):
    pieces=[];offset=0
    for n,p in enumerate(paras):
        p['paragraph_id']=f'p{n+1:05}';p['start']=offset;p['end']=offset+len(p['text']);pieces.append(p['text']);offset=p['end']+2
    return '\n\n'.join(pieces)+'\n',paras

def native_paragraphs(lines):
    """PDF geometric lines or authoritative OOXML paragraphs; all units accounted."""
    body=[];notes=[];current=None;previous=None
    margins=[l['bbox'][0] for l in lines if l['role']=='body' and l.get('bbox') and len(l['text'])>50]
    margin=min(margins) if margins else 0
    for l in lines:
        if l['role']=='removed':continue
        target=notes if l['role']=='note' else body
        s=l['text']
        if not s:continue
        last=target[-1] if target else None
        force=l.get('authoritative_paragraph',False)
        titlewrap=last and previous and l.get('bold') and previous.get('bold') and previous['role']==l['role'] and not heading(s) and not s.startswith('Về ') and last['text'].startswith('Về ')
        if last and l['role']=='note':
            new=bool(re.match(r'^\[\^',s)) or force
        else:
            indented=bool(l.get('bbox') and l['bbox'][0]>margin+18)
            cross=last and previous and l.get('page')!=previous.get('page') and not re.search(r'[.;:!?][”"\)]?$',last['text'])
            new=not last or force or heading(s) or (s.startswith('Về ') and l.get('bold')) or bool(MARKER.match(s)) or (indented and not cross) or (last and last['kind']=='heading')
            if titlewrap:new=False
        if not last or new:
            target.append(dict(text=s,line_ids=[l['id']],pages=[l.get('page')] if l.get('page') else [],kind='footnote' if l['role']=='note' else ('heading' if heading(s) or s.startswith('Về ') else 'paragraph')))
        else:
            last['text']+=' '+s;last['line_ids'].append(l['id'])
            if l.get('page') and l['page'] not in last['pages']:last['pages'].append(l['page'])
        previous=l
    out,paragraphs=assemble(body+([dict(text='CHÚ THÍCH NGUỒN',line_ids=[],pages=[],kind='generated_heading')] if notes else [])+notes)
    expected=Counter(l['id'] for l in lines if l['role']!='removed' and l['text'])
    if Counter(i for p in paragraphs for i in p['line_ids'])!=expected:raise ValueError('Native line coverage mismatch')
    return out,paragraphs
