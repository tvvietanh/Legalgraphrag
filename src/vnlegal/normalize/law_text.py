"""Conservative OCR layout cleanup; changes remain reviewable."""
import re
import unicodedata


def fold(text):
    return ''.join(c for c in unicodedata.normalize('NFD',text.lower()) if not unicodedata.combining(c)).replace('đ','d')


def normalize_layout(source):
    edits, blocks, current = [], [], []
    pos = 0
    def flush():
        if current:
            blocks.append(dict(source_start=current[0][0],source_end=current[-1][1],
                               text=' '.join(x[2] for x in current)))
            current.clear()
    for page_number,page in enumerate(source.split('\f'),1):
        lines=page.splitlines(keepends=True)
        nonempty=[i for i,line in enumerate(lines) if line.strip()]
        for i,line in enumerate(lines):
            start=pos;pos+=len(line)
            text=unicodedata.normalize('NFC',line.strip())
            margin=i in nonempty[:6] or i in nonempty[-4:]
            ascii_line=fold(text)
            reason=None
            if margin and re.search(r'cong\s*b[aăâ]?o\s*[/|]?\s*so\b',ascii_line):
                reason='publication_header_footer'
            elif i in nonempty[:3]+nonempty[-3:] and re.fullmatch(r'\d{1,4}',text):
                # Only standalone page-like numeral; retain as review operation.
                reason='standalone_margin_number'
            elif page_number==1 and i in nonempty[:10] and re.match(r'(ky boi:|email:|co quan:|.*thoi gian ky:)',ascii_line):
                reason='digital_signature_margin'
            elif margin and re.fullmatch(r'[\W_]{2,}',text):
                reason='punctuation_only_margin_noise'
            if reason:
                edits.append(dict(start=start,end=pos,before=line,after='',reason=reason,page=page_number))
                continue
            if not text:
                if current and (re.search(r'[.;:!?]$',current[-1][2]) or re.match(r'^Điều\s+\d+',current[0][2])):flush()
                continue
            old=text
            text=re.sub(r'\bQH[!Il]([345])\b',r'QH1\1',text)
            text=re.sub(r'^(\d+)[ILl!]\.\s*',r'\1. ',text)
            text=re.sub(r'^([“"\s]*)([a-zđ])[\]}]\s+',r'\1\2) ',text)
            text=re.sub(r'^([“"\s]*)([a-zđ])[.]\s+',r'\1\2) ',text)
            text=re.sub(r'[ \t\u00a0]+',' ',text)
            if text!=old:
                edits.append(dict(start=start,end=pos,before=old,after=text,reason='identifier_marker_spacing',page=page_number))
            starts=bool(re.match(r'^(?:[“"]?\d+[.)]\s|[“"]?[a-zđ][)]\s|Điều\s+\d+|PHẦN\b|Phần\b|CHƯƠNG\b|Chương\b|MỤC\b|Mục\b)',text))
            title=text.isupper() and len(text)>5
            if starts or title:flush()
            current.append((start,pos,text))
            if title:flush()
        pos+=1 if page_number<len(source.split('\f')) else 0
    flush()
    return blocks,edits


PROTECTED=re.compile(r'\b(?:không|chưa|phải|được|bị|hoặc|và|trên|dưới|từ|đến|ít|nhất|nhiều|tối|đa|rất|tất|tội|tù|tiền|án|treo|miễn|giảm|tử|hình|khoản|điểm|điều|chung|thân)\b',re.I)


def preserve_continuation_case(before,after):
    if before and after and before[0].islower() and after[0].isupper() and fold(before[0])==fold(after[0]):
        return after[0].lower()+after[1:]
    return after


def accept_prediction(before,after):
    import difflib
    if not after.strip():return False,'empty_prediction'
    if before.isupper():return False,'preserve_uppercase_heading'
    if re.findall(r'\w+',before.lower())==re.findall(r'\w+',after.lower()):
        return False,'no_lexical_correction'
    if re.search(r'[;:][.]|[.][;:]',after) and not re.search(r'[;:][.]|[.][;:]',before):
        return False,'new_punctuation_artifact'
    if re.findall(r'\d+',before)!=re.findall(r'\d+',after):return False,'numeric_change'
    if [x.lower() for x in PROTECTED.findall(before)]!=[x.lower() for x in PROTECTED.findall(after)]:
        return False,'protected_word_change'
    if re.findall(r'\b[A-Z]{2,}\d*\b',before)!=re.findall(r'\b[A-Z]{2,}\d*\b',after):
        return False,'identifier_change'
    a,b=before.split(),after.split()
    if abs(len(a)-len(b))>2:return False,'token_count_change'
    changes=[(i1,i2,j1,j2) for op,i1,i2,j1,j2 in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes() if op!='equal']
    if sum(max(i2-i1,j2-j1) for i1,i2,j1,j2 in changes)>max(2,int(len(a)*0.12)):
        return False,'large_edit'
    for i1,i2,j1,j2 in changes:
        old=' '.join(a[i1:i2]);new=' '.join(b[j1:j2])
        if fold(old)!=fold(new) and difflib.SequenceMatcher(None,old.lower(),new.lower()).ratio()<0.75:
            return False,'semantic_or_large_spelling_change'
    return True,'small_spelling_candidate'
