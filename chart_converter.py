"""Strict UGC v8 -> C2S 1.15 conversion. Unsupported gameplay never vanishes."""
from dataclasses import dataclass,field
from fractions import Fraction
from collections import Counter
import math,re

class ConversionError(ValueError):pass

@dataclass
class Note:
    time:Fraction
    code:str
    line:int
    children:list=field(default_factory=list)
    timeline:int=0

@dataclass
class Chart:
    header:dict
    notes:list
    bpms:list
    meters:list
    ticks:int
    warnings:list
    def value(self,key,default=''):
        return self.header.get(key,[[default]])[-1][0]

def finite(s):
    v=float(s)
    if not math.isfinite(v):raise ConversionError('Numeric values must be finite.')
    return v

def parse_ugc(text):
    header={};raw=[];parent=None;timeline=0;ended=False
    for line,s in enumerate(text.lstrip('\ufeff').splitlines(),1):
        s=s.strip()
        if not s or s.startswith("'"):continue
        if s.startswith('@'):
            p=s.split('\t');key=p[0][1:]
            if key=='ENDHEAD':ended=True;continue
            if key=='USETIL':timeline=int(p[1]);continue
            if ended:raise ConversionError(f'Line {line}: unsupported body directive {key}.')
            header.setdefault(key,[]).append(p[1:]);continue
        if not s.startswith('#'):continue
        m=re.fullmatch(r"#(\d+)'(\d+):(.+)",s)
        if m:
            parent=Note((int(m[1]),int(m[2])),m[3],line,timeline=timeline);raw.append(parent);continue
        m=re.fullmatch(r'#(\d+)[>:]([sc].*)',s)
        if m and parent is not None:parent.children.append((int(m[1]),m[2],line));continue
        raise ConversionError(f'Line {line}: malformed UGC note.')
    if not ended or header.get('VER')!=[['8']]:raise ConversionError('Export a text .ugc v8 chart from Margrete first. Binary .mgxc is not supported.')
    ticks=int(header.get('TICKS',[['480']])[-1][0])
    if ticks<=0 or ticks>100000:raise ConversionError('Invalid UGC tick resolution.')
    beats=sorted((int(p[0]),int(p[1]),int(p[2])) for p in header.get('BEAT',[['0','4','4']]))
    if beats[0][0]!=0 or len({b for b,_,_ in beats})!=len(beats) or any(n<=0 or d<=0 for _,n,d in beats):raise ConversionError('Invalid meter map.')
    def time(bar,tick):
        result=Fraction(0)
        for i,(at,n,d) in enumerate(beats):
            stop=beats[i+1][0] if i+1<len(beats) else bar
            count=max(0,min(bar,stop)-at)
            result+=count*Fraction(n,d)
        return result+Fraction(tick,ticks*4)
    for note in raw:note.time=time(*note.time)
    bpms=[]
    for p in header.get('BPM',[]):
        m=re.fullmatch(r"(\d+)'(\d+)",p[0])
        if not m:raise ConversionError('BPM needs bar\'tick time.')
        value=finite(p[1])
        if value<=0:raise ConversionError('BPM must be positive.')
        bpms.append((time(int(m[1]),int(m[2])),value))
    bpms.sort()
    if not bpms or bpms[0][0]!=0 or len({t for t,_ in bpms})!=len(bpms):raise ConversionError('BPM map must start at zero and have unique times.')
    if not raw:raise ConversionError('Chart has no notes.')
    for p in header.get('TIL',[]):
        if p!=['0',"0'0",'7.00000'] and not (len(p)==3 and int(p[0])==0 and p[1]=="0'0" and finite(p[2])==7):
            raise ConversionError('Custom timelines/speeds are not supported yet. Export a chart with one standard timeline (speed 7).')
    for key in ('SPDMOD','SPDDEF','SPDFLD'):
        if key in header:raise ConversionError(f'{key} speed effects are not supported yet.')
    if any(n.timeline!=0 for n in raw):raise ConversionError('Multiple timelines are not supported yet.')
    if finite(header.get('BGMOFS',[['0']])[-1][0])!=0:raise ConversionError('Set BGMOFS to zero and bake the offset into your audio before importing.')
    flags={p[0]:p[1] for p in header.get('FLAG',[]) if len(p)==2}
    if flags.get('SOFFSET','FALSE')!='FALSE':raise ConversionError('Disable SOFFSET in Margrete before converting; automatic audio shifting is not enabled.')
    warnings=[]
    if flags.get('DIFFTTL')=='TRUE':raise ConversionError('Tutorial charts are not supported.')
    longs={(n.time,n.code[1:3]) for n in raw if n.code[0] in 'hs'}
    if any(n.code[0]=='x' and (n.time,n.code[1:3]) in longs for n in raw):
        raise ConversionError('Overlapping ExTAP + long-note carriers are not supported yet; separate them before converting.')
    return Chart(header,raw,bpms,[(time(b,0),n,d) for b,n,d in beats],ticks,warnings)

def convert(chart,music_id=0):
    """Round absolute endpoints once; subtract rounded endpoints for durations."""
    if isinstance(chart,str):chart=parse_ugc(chart)
    def q(t):return round(t*384)
    def bt(t):return divmod(q(t),384)
    def lane(code):
        if len(code)<3:raise ConversionError('Missing lane/width.')
        x,w=int(code[1],36),int(code[2],36)
        if not 0<=x<16 or not 1<=w<=16-x:raise ConversionError('Lane/width outside the 16-lane field.')
        return x,w
    def height(s):return (int(s,36)/(10 if len(s)==2 else 1))/2+1 if s else 5.
    def color(s,crush=False,down=False):
        if crush:
            colors=dict(zip('0123456789AYBCDZ',['DEF','RED','ORN','YEL','LIM','GRN','AQA','CYN','DGR','BLU','VLT','PPL','PNK','GRY','BLK','NON']))
            if s not in colors:raise ConversionError('Unknown AIR-CRUSH color.')
            return colors[s]
        if s=='N':return 'DEF'
        if s=='I':return 'GRN' if down else 'PPL'
        raise ConversionError('Unknown AIR color.')
    ex={'U':'UP','D':'DW','C':'CE','L':'LS','R':'RS','A':'RC','W':'LC','I':'BS'}
    air={'UC':'AIR','UL':'AUL','UR':'AUR','DC':'ADW','DL':'ADL','DR':'ADR'}
    records=[];counts=Counter();endpoints=[];previous=None;targets=[]
    def emit(tag,t,x,w,*rest):
        records.append((q(t),len(records),'\t'.join(map(str,(tag,*bt(t),x,w,*rest)))))
    for n in chart.notes:
        try:
            c=n.code;k=c[0]
            if k=='c':chart.warnings.append(f'Line {n.line}: metronome CLICK omitted (not a gameplay note).');continue
            if k not in 'txfdhsHaSC':raise ConversionError(f'Unsupported note type {k}.')
            x,w=lane(c);t=n.time;target=None
            if k in 'aHS':
                if previous is None or previous[:3]!=(t,x,w):raise ConversionError('AIR note has no matching preceding ground/long-note endpoint.')
                target=previous[3]
            if k in 'txfd':
                if n.children:raise ConversionError('A tap cannot have child points.')
                tag={'t':'TAP','x':'CHR','f':'FLK','d':'MNE'}[k]
                rest=() if k in 'td' else (ex[c[3:]],) if k=='x' else ('L',)
                if k=='f' and c[3:] not in ('A','L','R'):raise ConversionError('Invalid flick direction.')
                emit(tag,t,x,w,*rest);previous=(t,x,w,tag);counts[k]+=1;endpoints.append(t)
            elif k=='a':
                if len(c)!=6 or c[3:5] not in air:raise ConversionError('Invalid AIR direction.')
                tag=air[c[3:5]];emit(tag,t,x,w,target,color(c[5],down=c[3]=='D'))
                counts[k]+=1;endpoints.append(t)
                # AIR does not replace the ground carrier for an attached long.
            else:
                if not n.children:raise ConversionError('Long note has no endpoint.')
                if k in 'SC':
                    raw=c[3:].split(',');shape=raw[0]
                    h=height(shape[:-1]);col=color(shape[-1],crush=k=='C')
                else:h=5.;col=color(c[-1]) if k=='H' else 'DEF'
                interval=0
                if k=='C':
                    if len(raw)!=2:raise ConversionError('AIR-CRUSH needs a tick interval.')
                    interval=9600 if raw[1]=='$' else round(Fraction(int(raw[1]),chart.ticks*4)*384)
                    if interval<0:raise ConversionError('Negative AIR-CRUSH interval.')
                last=0;tag='';prev_tag=target
                for off,child,line in n.children:
                    if off<=last:raise ConversionError('Long-note points must have increasing offsets.')
                    dest=t+Fraction(off,chart.ticks*4);dur=q(dest)-q(t+Fraction(last,chart.ticks*4))
                    if dur<=0:raise ConversionError('Points collapse at C2S resolution. Separate them by at least five UGC ticks.')
                    control=child[0]=='c'
                    if k in 'sSC':nx,nw=lane(child)
                    else:nx,nw=x,w
                    nh=height(child[3:]) if k in 'SC' and len(child)>3 else h
                    at=t+Fraction(last,chart.ticks*4)
                    if k=='h':
                        if control or len(n.children)!=1:raise ConversionError('HOLD supports one ordinary endpoint.')
                        tag='HLD';emit(tag,at,x,w,dur)
                    elif k=='s':tag='SLC' if control else 'SLD';emit(tag,at,x,w,dur,nx,nw,'SLD')
                    elif k=='H':
                        if control:raise ConversionError('AIR-HOLD endpoints without an action are not supported yet.')
                        tag='AHD';emit(tag,at,x,w,prev_tag,dur,col)
                    elif k=='S':
                        tag='ASC' if control else 'ASD';emit(tag,at,x,w,prev_tag,f'{h:.3f}',dur,nx,nw,f'{nh:.3f}',col)
                    else:tag='ALD';emit(tag,at,x,w,interval,f'{h:.3f}',dur,nx,nw,f'{nh:.3f}',col,'DEF')
                    x,w,h=nx,nw,nh;last=off;prev_tag=tag
                previous=(dest,x,w,'SLD' if k=='s' else tag)
                counts[k]+=1;endpoints.append(dest)
        except (ValueError,IndexError,KeyError) as e:
            raise ConversionError(f'Line {n.line}: {e}') from e
    bpms=[v for _,v in chart.bpms];b=bpms[0]
    lines=[f'VERSION\t1.15.00\t1.15.00',f'MUSIC\t{int(music_id)}','SEQUENCEID\t0',
           f'DIFFICULT\t{4 if chart.value("DIFF","3")=="5" else int(chart.value("DIFF","3")):02d}',f'LEVEL\t{finite(chart.value("CONST","0")):.1f}',
           'CREATOR\t'+chart.value('DESIGN'),f'BPM_DEF\t{b:.6f}\t{b:.6f}\t{max(bpms):.6f}\t{min(bpms):.6f}',
           'MET_DEF\t4\t4','RESOLUTION\t384','CLK_DEF\t384','PROGJUDGE_BPM\t240.000','PROGJUDGE_AER\t0.999','TUTORIAL\t0','']
    for t,b in chart.bpms:lines.append(f'BPM\t{bt(t)[0]}\t{bt(t)[1]}\t{b:.6f}')
    for t,num,den in chart.meters:lines.append(f'MET\t{bt(t)[0]}\t{bt(t)[1]}\t{den}\t{num}')
    lines+=['']+[s for _,_,s in sorted(records)]
    report={'title':chart.value('TITLE'),'difficulty':int(chart.value('DIFF','3')),'source_parents':len(chart.notes),
            'converted_types':dict(counts),'c2s_records':len(records),'warnings':list(chart.warnings),
            'last_tick':max(q(t) for t in endpoints),'resolution':384,'max_rounding_ms':max(60/v/96/2*1000 for v in bpms)}
    return '\r\n'.join(lines)+'\r\n',report
