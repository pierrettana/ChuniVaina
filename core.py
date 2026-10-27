"""XML model and read-only option index. No third-party dependencies."""
import copy
import re
from pathlib import Path
import xml.etree.ElementTree as ET

KINDS = {'CharaData': ('Character', 'chara', 'Chara.xml', 6),
         'CharaWorksData': ('Category', 'charaWorks', 'CharaWorks.xml', 6),
         'TrophyData': ('Trophy', 'trophy', 'Trophy.xml', 6),
         'QuestData': ('Quest', 'quest', 'Quest.xml', 8),
         'DDSImageData': ('Character artwork', 'ddsImage', 'DDSImage.xml', 6),
         'RewardData': ('Reward', 'reward', 'Reward.xml', 9),
         'EventData': ('Event', 'event', 'Event.xml', 8),
         'MapData': ('Map', 'map', 'Map.xml', 8),
         'MapAreaData': ('Map area', 'mapArea', 'MapArea.xml', 8),
         'MapBonusData': ('Map bonus', 'mapBonus', 'MapBonus.xml', 8),
         'DDSMapData': ('Map artwork', 'ddsMap', 'DDSMap.xml', 8),
         'NamePlateData': ('Nameplate', 'namePlate', 'NamePlate.xml', 8),
         'StageData': ('Stage', 'stage', 'Stage.xml', 6),
         'RightsInfoData': ('Rights information', 'rightsInfo', 'RightsInfo.xml', 6),
         'MusicData': ('Song', 'music', 'Music.xml', 4),
         'CueFileData': ('Song audio bank', 'cueFile', 'CueFile.xml', 6)}

def kind_label(kind):
    return "Song" if kind=="MusicData" else KINDS[kind][0]


def parse(text, index_only=False):
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('DTD and entity declarations are not supported.')
    root = ET.fromstring(text)
    if root.tag not in KINDS and not (index_only and root.tag=='MusicData'):
        raise ValueError('Unsupported content type: ' + root.tag)
    return root

def identity(root):
    return root.tag, int(root.findtext('name/id', ''))

def serialize(root):
    root = copy.deepcopy(root)
    root.set('xmlns:xsd', 'http://www.w3.org/2001/XMLSchema')
    root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    ET.indent(root, space='  ')
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='unicode') + '\n'

def set_identity(root, number, name):
    number = int(number)
    if number < 0:
        raise ValueError('Content ID must be nonnegative.')
    _, prefix, _, width = KINDS[root.tag]
    root.find('name/id').text = str(number)
    root.find('name/str').text = name
    root.find('dataName').text = prefix + str(number).zfill(width)

def validate(root):
    _, number = identity(root)
    if number < 0: raise ValueError('Content ID must be nonnegative.')
    if not root.findtext('name/str', '').strip(): raise ValueError('Display name is required.')
    _, prefix, _, width = KINDS[root.tag]
    if root.findtext('dataName') != prefix + str(number).zfill(width):
        raise ValueError('dataName does not match ID. Use Apply identity to synchronize it.')
    validate_map_structure(root)
    if root.tag=='EventData':
        code=root.findtext('substances/type')
        if code=='2' and int(root.findtext('substances/map/mapName/id','-1'))<0:
            raise ValueError('Map-opening event needs a map target. Use Link event target.')
        if code=='11' and not root.findall('substances/rightsInfo/rightsNames/list/StringID'):
            raise ValueError('Rights-information event needs at least one rights target. Use Link event target.')
        if code=='8' and not root.findall('substances/quest/questNames/list/StringID'):
            raise ValueError('Quest-opening event needs at least one quest target. Use Link event target.')
    for el in root.iter():
        if el.tag == 'id': int(el.text or '')
        if el.tag in ('disableFlag', 'defaultHave', 'ranking', 'hideInfo', 'changeImg', 'alwaysOpen', 'teamOnly', 'isKop', 'isHard', 'netDispPeriod', 'enablePlate', 'isReward', 'dispNet'):
            if el.text not in ('true', 'false'): raise ValueError(el.tag + ' must be true or false.')

def scan(folders, definitions=None):
    index, errors, seen = {}, [], set()
    for folder in folders:
        base = Path(folder)
        if not base.is_dir():
            errors.append(str(base) + ': folder is missing'); continue
        for path in base.rglob('*'):
            if path.suffix.lower() != '.xml' or path.is_symlink(): continue
            resolved = str(path.resolve())
            if resolved in seen: continue
            seen.add(resolved)
            try:
                text = path.read_text(encoding='utf-8-sig')
                # Index definitions only, never IDs in nested references.
                if not any('<' + kind in text for kind in list(KINDS)+['MusicData']): continue
                root = parse(text,index_only=True)
                index.setdefault(identity(root), []).append((root.findtext('name/str', ''), resolved))
                if definitions is not None and root.tag in ('RewardData','MapData','MapAreaData','QuestData','EventData'):
                    definitions.append(root)
                if definitions is not None and root.tag=='MusicData':
                    metadata=ET.Element('MusicData')
                    for tag in ('name','artistName','disableFlag','releaseTagName'):
                        el=root.find(tag)
                        if el is not None: metadata.append(copy.deepcopy(el))
                    definitions.append(metadata)
            except (OSError, ValueError, ET.ParseError) as exc:
                errors.append(str(path) + ': ' + str(exc))
    return index, errors

def export_path(folder, root):
    validate(root)
    _, _, filename, _ = KINDS[root.tag]
    return Path(folder) / root.findtext('dataName') / filename


def discover_sources(parent):
    """Find Axxx directories recursively, without descending into option contents."""
    import os
    found, errors = [], []
    def onerror(exc): errors.append(str(exc))
    for current, dirs, _ in os.walk(parent, followlinks=False, onerror=onerror):
        path = Path(current)
        if re.fullmatch(r'A[0-9A-Za-z]{3}', path.name):
            found.append(str(path.resolve()))
            dirs[:] = []
        else:
            dirs[:] = sorted(d for d in dirs if not d.startswith('.') and not (path/d).is_symlink())
    return sorted(found), errors


def export_option(parent, folder_name, documents, assets=None, version=None):
    """Export project XMLs to a new option directory; stage before publishing."""
    import os
    import shutil
    import tempfile
    if not re.fullmatch(r'A[0-9A-Za-z]{3}', folder_name):
        raise ValueError('Folder name must be A followed by three letters or digits, e.g. A900.')
    if not documents: raise ValueError('The project has no content to export.')
    if version is not None:
        if (not isinstance(version, (tuple, list)) or len(version) != 3
                or any(type(v) is not int or v < 0 for v in version)):
            raise ValueError('Version must contain three nonnegative integers.')
    assets = assets or {}
    seen=set()
    for root in documents:
        validate(root)
        key=identity(root)
        if key in seen: raise ValueError(f'Duplicate project ID: {KINDS[root.tag][0]} {key[1]}. Resolve it before exporting.')
        seen.add(key)
        artwork_files(root, assets)
    destination=Path(parent)/folder_name
    if destination.exists() or destination.is_symlink():
        raise ValueError('That output folder already exists. Choose a different name or location.')
    staging=Path(tempfile.mkdtemp(prefix='.chunivaina-', dir=parent))
    try:
        for root in documents:
            _, category, filename, _=KINDS[root.tag]
            target=staging/category/root.findtext('dataName')/filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(serialize(root), encoding='utf-8')
            for filename, data in artwork_files(root, assets): (target.parent/filename).write_bytes(data)
        if version is not None:
            major, minor, release = version
            (staging/'data.conf').write_text(
                f'[Version]\nName = CHUNITHM\nVerMajor   = {major}\nVerMinor   = {minor}\nVerRelease = {release}\n', encoding='utf-8')
        if destination.exists(): raise ValueError('Output folder was created by another process; export cancelled.')
        os.rename(staging,destination)
    finally:
        if staging.exists(): shutil.rmtree(staging)
    return destination


def dds_info(data):
    import struct
    if len(data)<128 or data[:4]!=b'DDS ' or struct.unpack_from('<I',data,4)[0]!=124:
        raise ValueError('Not a valid DDS header.')
    height,width=struct.unpack_from('<II',data,12)
    if not width or not height: raise ValueError('DDS dimensions must be positive.')
    return width,height,struct.unpack_from('<I',data,28)[0]


def asset_slots(root):
    """(XML leaf path, required, reference size) for supported artwork."""
    if root.tag=='DDSImageData': return [(f'ddsFile{i}/path',True,(n,n)) for i,n in enumerate((1080,512,128))]
    if root.tag=='DDSMapData': return [('ddsFile/path',True,(1220,680))]
    if root.tag=='EventData': return [('substances/information/image/path',False,(1152,648))]
    if root.tag=='NamePlateData': return [('image/path',True,(576,228))]
    if root.tag=='StageData': return [('image/path',True,(960,450))]
    if root.tag=='RightsInfoData': return [('image/path',True,(512,48))]
    if root.tag=='MusicData': return [('jaketFile/path',True,(300,300))]
    return []


def binary_slots(root):
    if root.tag=='MusicData':
        return [(f'fumens/MusicFumenData[{i+1}]/file/path',True,None) for i,f in enumerate(root.findall('fumens/MusicFumenData')) if f.findtext('enable')=='true']
    if root.tag=='CueFileData':return [('acbFile/path',True,None),('awbFile/path',True,None)]
    if root.tag=='StageData':
        return [('notesFieldFile/path',True,None),('baseFile/path',True,None),('objectFile/path',False,None)]
    return []


def validate_asset(filename, data):
    if not filename or '/' in filename or '\\' in filename or ':' in filename or filename in ('.','..'):
        raise ValueError('Assets require plain filenames.')
    if filename.lower().endswith('.afb'):
        from stage_model import afb_regions
        afb_regions(data)
    elif filename.lower().endswith('.dds'): dds_info(data)
    elif filename.lower().endswith('.acb'):
        from cri_audio import read_utf
        read_utf(data)
    elif filename.lower().endswith('.awb'):
        from cri_audio import read_awb
        read_awb(data)
    elif filename.lower().endswith('.c2s'):
        from song_model import validate_c2s
        validate_c2s(data)
    else: raise ValueError('Supported assets: DDS, AFB, C2S, ACB and AWB.')


def artwork_files(root, assets):
    result=[]
    for path,required,_ in asset_slots(root):
        filename=root.findtext(path,'')
        if not filename and not required: continue
        if not filename or '/' in filename or '\\' in filename or ':' in filename or filename in ('.','..'):
            raise ValueError('Each artwork slot requires a plain DDS filename.')
        if filename not in assets: raise ValueError('Missing attached artwork: '+filename)
        data=assets[filename]; dimensions=dds_info(data)
        if root.tag=='RightsInfoData' and dimensions[:2]!=(512,48): raise ValueError('Rights artwork must be 512×48 pixels.')
        result.append((filename,data))
    for path,required,_ in binary_slots(root):
        filename=root.findtext(path,'')
        if not filename and not required: continue
        if not filename: raise ValueError('Missing binary asset reference: '+path)
        expected='.afb' if root.tag=='StageData' else '.c2s' if root.tag=='MusicData' else '.acb' if path.startswith('acb') else '.awb'
        if not filename.lower().endswith(expected):raise ValueError('This slot requires '+expected)
        if filename not in assets: raise ValueError(('Missing attached stage bundle: ' if root.tag=='StageData' else 'Missing attached asset: ')+filename)
        data=assets[filename]; validate_asset(filename,data); result.append((filename,data))
    if root.tag=='CueFileData':
        from cri_audio import require_hca_bank
        require_hca_bank(assets[root.findtext('acbFile/path')],assets[root.findtext('awbFile/path')])
    if len({name for name,_ in result})!=len(result): raise ValueError('Asset slots must have distinct filenames.')
    return result


def configure_reward(substance, target):
    """Set one reward substance to a trophy or character definition."""
    mapping={'TrophyData':('2','trophy/trophyName'), 'CharaData':('3','chara/charaName'), 'NamePlateData':('5','namePlate/namePlateName'), 'StageData':('13','stage/stageName')}
    if target.tag not in mapping: raise ValueError('Choose a trophy, character, nameplate, or stage.')
    code,path=mapping[target.tag]
    ref=substance.find(path)
    if ref is None or substance.find('type') is None: raise ValueError('Reward substance is missing required fields.')
    # Inactive StringID references are reset to the sample Invalid sentinel.
    for element in substance.iter():
        if element.find('id') is not None and element.find('str') is not None:
            element.find('id').text='-1'; element.find('str').text='Invalid'
    substance.find('type').text=code
    ref.find('id').text=target.findtext('name/id')
    ref.find('str').text=target.findtext('name/str')


def add_quest_reward(milestone, reward):
    if milestone.tag!='QuestRewardDataInfo' or reward.tag!='RewardData': raise ValueError('Select a quest milestone and a reward.')
    container=milestone.find('rewardName/list')
    if container is None: raise ValueError('Milestone has no rewardName/list field.')
    num=reward.findtext('name/id')
    if any(ref.findtext('id')==num for ref in container): raise ValueError('This milestone already contains that reward.')
    ref=ET.SubElement(container,'StringID')
    ET.SubElement(ref,'id').text=num
    ET.SubElement(ref,'str').text=reward.findtext('name/str')
    ET.SubElement(ref,'data')


REFERENCE_TYPES={
    'mapAreaName':'MapAreaData','ddsMapName':'DDSMapData','mapBonusName':'MapBonusData',
    'mapName':'MapData','rewardName':'RewardData','charaWorksName':'CharaWorksData',
    'works':'CharaWorksData','charaName':'CharaData','keyCharaName':'CharaData',
    'trophyName':'TrophyData','keyTrophyName':'TrophyData','defaultImages':'DDSImageData',
    'stopReleaseEventName':'EventData','namePlateName':'NamePlateData','keyNamePlateName':'NamePlateData','musicName':'MusicData','stageName':'StageData','keyStageName':'StageData','cueFileName':'CueFileData','rightsInfoName':'RightsInfoData',
}
LIST_REFERENCE_TYPES={'musicNames':'MusicData','rightsNames':'RightsInfoData','questNames':'QuestData','charaWorks':'CharaWorksData','charas':'CharaData','rewardName':'RewardData'}


def set_reference(ref, target):
    if ref.find('id') is None or ref.find('str') is None: raise ValueError('Select an ID/name reference.')
    ref.find('id').text=target.findtext('name/id')
    ref.find('str').text=target.findtext('name/str')


def reference_report(documents, index):
    """Report resolvable typed links, allowing external definitions from the index."""
    known={identity(r) for r in documents}|set(index)
    names={identity(r):r.findtext('name/str') for r in documents}
    issues=[]
    for root in documents:
        label=f'{KINDS[root.tag][0]} {root.findtext("name/id")}'
        parents={c:p for p in root.iter() for c in p}
        for ref in root.iter():
            kind=REFERENCE_TYPES.get(ref.tag)
            if ref.tag=='StringID':
                parent=parents.get(ref); outer=parents.get(parent)
                kind=LIST_REFERENCE_TYPES.get(outer.tag) if outer is not None else None
            if not kind or ref.find('id') is None: continue
            try: number=int(ref.findtext('id','-1'))
            except ValueError: continue
            if number<0: continue
            key=(kind,number)
            if key not in known: issues.append(f'{label}: {ref.tag} → {kind_label(kind)} {number} is not in this project or the imported index.')
            elif key in names and ref.findtext('str','')!=names[key]: issues.append(f'{label}: {ref.tag} {number} uses a different name from its project target.')
        if root.tag=='EventData' and root.findtext('substances/type')=='1' and root.findtext('substances/map/mapName/id','-1')!='-1':
            issues.append(f'{label}: an announcement (type 1) has a map reference; use a separate map-opening event (type 2) to configure map availability.')
    return issues


def validate_map_structure(root):
    if root.tag=='MapAreaData':
        grids=root.findall('grids/MapAreaGridData')
        positions=[int(g.findtext('index','-1')) for g in grids]
        if len(positions)!=len(set(positions)) or any(n<0 for n in positions): raise ValueError('Map area grid indices must be unique and nonnegative.')
        if positions!=sorted(positions): raise ValueError('Map area grid entries must be in ascending index order.')
    elif root.tag=='MapData':
        locations=[(int(e.findtext('pageIndex','-1')),int(e.findtext('indexInPage','-1'))) for e in root.findall('infos/MapDataAreaInfo')]
        if any(min(pair)<0 for pair in locations) or len(locations)!=len(set(locations)): raise ValueError('Map entries need unique, nonnegative page/index pairs.')


def configure_activation(event, target):
    """Link map, quest and rights-information event targets."""
    code={'MapData':'2','QuestData':'8','RightsInfoData':'11'}.get(target.tag)
    if code is None: raise ValueError('Activation target must be a map, quest or rights entry.')
    if event.findtext('substances/type')!=code: raise ValueError('Choose the matching map, quest or rights event preset first.')
    if code=='2': set_reference(event.find('substances/map/mapName'),target)
    else:
        container=event.find('substances/rightsInfo/rightsNames/list' if code=='11' else 'substances/quest/questNames/list')
        if container is None: raise ValueError('Missing event target reference list.')
        if any(r.findtext('id')==target.findtext('name/id') for r in container): return
        ref=ET.SubElement(container,'StringID')
        ET.SubElement(ref,'id');ET.SubElement(ref,'str');ET.SubElement(ref,'data')
        set_reference(ref,target)


def character_unlock_warnings(documents, external=()):
    """Trace known reward grants; conditions/bonus references do not unlock characters.

    Imported definitions are included, with project definitions taking precedence.
    Unknown unlock mechanisms are reported as unverified, never declared impossible.
    """
    definitions={identity(r):r for r in external}
    definitions.update({identity(r):r for r in documents})
    used_rewards=set()
    def add_ids(root,path):
        for el in root.findall(path):
            try:
                num=int(el.text or '-1')
                if num>=0: used_rewards.add(num)
            except ValueError: pass
    # Only map areas actually linked by a map are considered reachable checkpoints.
    linked_areas=set()
    for root in definitions.values():
        if root.tag=='MapData':
            add_ids(root,'infos/MapDataAreaInfo/rewardName/id')
            for el in root.findall('infos/MapDataAreaInfo/mapAreaName/id'):
                try: linked_areas.add(int(el.text or '-1'))
                except ValueError: pass
        elif root.tag=='QuestData': add_ids(root,'info/QuestRewardDataInfo/rewardName/list/StringID/id')
    for root in definitions.values():
        if root.tag=='MapAreaData' and identity(root)[1] in linked_areas:
            add_ids(root,'grids/MapAreaGridData/reward/rewardName/id')
    grants={}
    for root in definitions.values():
        if root.tag!='RewardData': continue
        reward_id=identity(root)[1]
        for substance in root.findall('substances/list/RewardSubstanceData'):
            if substance.findtext('type')!='3': continue
            try: num=int(substance.findtext('chara/charaName/id','-1'))
            except ValueError: continue
            if num>=0: grants.setdefault(num,set()).add(reward_id)
    warnings=[]
    for chara in documents:
        if chara.tag!='CharaData' or chara.findtext('defaultHave')!='false': continue
        number=identity(chara)[1]; rewards=grants.get(number,set())
        if rewards & used_rewards: continue
        label=f'{chara.findtext("name/str")} (ID {number})'
        if rewards:
            reason='A character-granting reward exists, but no map completion, linked area checkpoint, or quest milestone uses it.'
        else: reason='No character-granting reward was found in this project or the scanned supported definitions.'
        warnings.append(label+': defaultHave is false. '+reason)
    return warnings


def song_catalog(definitions, index):
    songs={}
    for (kind,num),entries in index.items():
        if kind=='MusicData' and entries: songs[num]=(num,entries[0][0],'')
    for root in definitions:
        if root.tag=='MusicData':
            number=identity(root)[1]
            songs[number]=(number,root.findtext('name/str',''),root.findtext('artistName/str',root.findtext('artistName','')))
    return sorted(songs.values(),key=lambda song:(song[1].casefold(),song[0]))


def search_songs(catalog, query):
    import unicodedata
    def normalized(text):
        return ''.join(ch for ch in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(ch))
    tokens=normalized(query).split()
    return [song for song in catalog if all(token in normalized(' '.join(map(str,song))) for token in tokens)]


def set_task_track(entry, song=None):
    if entry.tag!='MapDataAreaInfo': raise ValueError('Select a map entry.')
    ref=entry.find('musicName')
    if ref is None:
        ref=ET.SubElement(entry,'musicName');ET.SubElement(ref,'id');ET.SubElement(ref,'str');ET.SubElement(ref,'data')
    ref.find('id').text=str(song[0]) if song is not None else '-1'
    ref.find('str').text=song[1] if song is not None else 'Invalid'
