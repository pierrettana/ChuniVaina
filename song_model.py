"""Song assembly, metadata and converter boundaries; independent of Tk."""
from pathlib import Path
import copy,re,math,xml.etree.ElementTree as ET
from chart_converter import parse_ugc,convert

DIFFICULTIES=('BASIC','ADVANCED','EXPERT','MASTER','ULTIMA')
CHART_CONSTANT_WARNING=(
    'Check your server’s current custom-chart rules before playing or uploading. '
    'Some public instances allow custom songs only with low chart constants to avoid '
    'advantages in player rating or leaderboards. A chart’s intended difficulty does '
    'not automatically make its constant appropriate for a public server. '
    'Set each enabled difficulty to the value required by your server; there is no universal safe constant. '
    'ChuniVaina preserves your chosen constants and does not enforce a server policy.'
)
def validate_c2s(data):
    text=data.decode('utf-8-sig')
    headers={};notes=0
    types={'TAP','CHR','FLK','MNE','HLD','HXD','SLD','SLC','SXD','SXC','AIR','AUR','AUL','ADW','ADR','ADL','AHD','AHX','ASD','ASC','ALD','SLA'}
    for line in text.splitlines():
        p=line.split('\t');k=p[0]
        if k in types:
            if len(p)<5:raise ValueError('Truncated C2S note.')
            bar,tick,x,w=map(int,p[1:5])
            if bar<0 or tick<0 or not 0<=x<16 or not 1<=w<=16-x:raise ValueError('Invalid C2S position.')
            notes+=1
        else:headers[k]=p[1:]
    if not notes or 'VERSION' not in headers or 'BPM' not in headers or 'RESOLUTION' not in headers:raise ValueError('Not a supported C2S chart.')
    return notes

def level_parts(value):
    v=float(value)
    if not math.isfinite(v) or v<0 or v>=100:raise ValueError('Chart constant must be between 0 and 100.')
    hundred=round(v*100)
    return str(hundred//100),str(hundred%100)

def build_song(template,cue_template,number,title,artist,charts,jacket,audio_pair,stage=-1,genre=0,release_tag=None):
    """Prepare XMLs+assets together; caller commits only after all checks pass."""
    from core import set_identity,validate,artwork_files
    from cri_audio import validate_bank,retarget_bank,require_hca_bank
    number=int(number)
    if not 1<=number<=999999:raise ValueError('Use a song ID from 1 to 999999.')
    if not title.strip() or not artist.strip():raise ValueError('Song title and artist are required.')
    if not charts:raise ValueError('Attach at least one difficulty.')
    root=copy.deepcopy(template);cue=copy.deepcopy(cue_template)
    from song_versions import set_song_version
    set_song_version(root,release_tag)
    set_identity(root,number,title);set_identity(cue,number,f'music{number}')
    root.find('artistName/id').text=str(number);root.find('artistName/str').text=artist
    root.find('sortName').text=re.sub(r'[\W_]','',title.upper())
    root.find('cueFileName/id').text=str(number);root.find('cueFileName/str').text=f'music{number}'
    root.find('stageName/id').text=str(int(stage));root.find('stageName/str').text='Invalid' if int(stage)<0 else str(stage)
    genre_ref=root.find('genreNames/list/StringID')
    genre_ref.find('id').text=str(int(genre));genre_ref.find('str').text={0:'POPS & ANIME',1:'niconico',2:'東方Project',3:'VARIETY',4:'イロドリミドリ',5:'ゲキマイ',6:'ORIGINAL'}.get(int(genre),str(genre))
    root.find('firstLock').text='false';root.find('disableFlag').text='false'
    jacket_name=f'CHU_UI_Jacket_{number}.dds';root.find('jaketFile/path').text=jacket_name
    acb_name=f'music{number}.acb';awb_name=f'music{number}.awb'
    cue.find('acbFile/path').text=acb_name;cue.find('awbFile/path').text=awb_name
    audio_pair=retarget_bank(*audio_pair,number)
    require_hca_bank(*audio_pair)
    assets={jacket_name:jacket,acb_name:audio_pair[0],awb_name:audio_pair[1]};reports=[]
    enabled=set()
    for f in root.findall('fumens/MusicFumenData'):
        diff=int(f.findtext('type/id'));f.find('enable').text='false';f.find('file/path').text=''
        if diff not in charts:continue
        if diff not in range(5):raise ValueError("WORLD'S END conversion is not supported yet.")
        item=charts[diff]
        if isinstance(item,str):
            chart=parse_ugc(item)
            ugc_diff=int(chart.value('DIFF','3'));expected=5 if diff==4 else diff
            if ugc_diff!=expected:raise ValueError('UGC difficulty does not match its selected slot.')
            text,report=convert(chart,number);constant=chart.value('CONST',chart.value('LEVEL','0').replace('+','.7'))
            designer=chart.value('DESIGN');data=text.encode('utf-8');reports.append(report)
        else:
            data,constant,designer=item
        validate_c2s(data);name=f'{number}_{diff:02d}.c2s';assets[name]=data
        f.find('file/path').text=name;f.find('enable').text='true';enabled.add(diff)
        f.find('level').text,f.find('levelDecimal').text=level_parts(constant)
        f.find('notesDesigner').text=designer;f.find('defaultBpm').text='0'
    if enabled!=set(charts):raise ValueError('Unsupported or missing difficulty slot in Music template.')
    root.find('enableUltima').text='true' if 4 in enabled else 'false'
    for r in (root,cue):validate(r);artwork_files(r,assets)
    return root,cue,assets,reports

