import re, os, pyphen
dic = pyphen.Pyphen(lang='en_US')

def parse_lyrics(path):
    raw = open(path).read().splitlines()
    # drop everything up to and including the dashed separator (header/style block)
    start = 0
    for i,l in enumerate(raw):
        if set(l.strip()) == {'-'} and len(l.strip())>5:
            start = i+1; break
    sections=[]; cur=None
    for l in raw[start:]:
        s=l.strip()
        if not s: continue
        m=re.match(r'^\((.+)\)$', s)
        if m:
            cur={'name':m.group(1),'lines':[]}; sections.append(cur); continue
        if cur is not None:
            cur['lines'].append(s)
    return sections

def syllables(word):
    core=re.sub(r"[^A-Za-z']",'',word)
    if not core: return [word]
    parts=dic.inserted(core).split('-')
    parts=[p for p in parts if p]
    return parts if parts else [core]

def line_syllables(line):
    out=[]
    for w in line.split():
        sy=syllables(w)
        # attach leading/trailing punctuation to nearest syllable for display
        out.extend(sy)
    return out

if __name__=="__main__":
    secs=parse_lyrics(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","teresa_and_ijooz_lyrics.txt"))
    total_syl=0; total_lines=0
    for sec in secs:
        print(f"\n[{sec['name']}]  ({len(sec['lines'])} lines)")
        for ln in sec['lines']:
            sy=line_syllables(ln); total_syl+=len(sy); total_lines+=1
            print(f"   {len(sy):2d}  {ln}")
            print(f"       -> {'·'.join(sy)}")
    print(f"\nTOTAL: {len(secs)} sections, {total_lines} lines, {total_syl} syllables")
