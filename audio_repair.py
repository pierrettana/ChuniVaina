"""Repair supported single-stream HCA banks for CHUNITHM.

No WAV/MP3 encoding. Cipher conversion preserves the decoded PCM exactly.
The public audio-interoperability entry comes from vgmstream (not game binaries).
"""
import copy
import hashlib
import io
import json
import os
import struct
import wave
import zipfile
from pathlib import Path
from cri_audio import require_hca_bank,read_utf,rewrite_utf

CHUNITHM_AUDIO_KEY=32931609366120192
KEY_SOURCE='https://github.com/vgmstream/vgmstream/blob/master/src/meta/hca_keys.h'
MAX_STREAM_BYTES=128*1024*1024

def _crc_table():
    result=[]
    for value in range(256):
        c=value<<8
        for _ in range(8):c=((c<<1)^0x8005 if c&0x8000 else c<<1)&65535
        result.append(c)
    return result
_CRC=_crc_table()

def crc16(data):
    c=0
    for b in data:c=((c<<8)^_CRC[(c>>8)^b])&65535
    return c

def hca_info(stream):
    if len(stream)<96 or len(stream)>MAX_STREAM_BYTES:raise ValueError('Unsupported HCA size.')
    if bytes(b&127 for b in stream[:4])!=b'HCA\0':raise ValueError('This fixer requires HCA audio.')
    version,head=struct.unpack_from('>HH',stream,4)
    if version!=0x200 or head!=96:
        raise ValueError('This fixer supports the HCA 2.0 / 96-byte header with the fmt/comp/ciph layout. Prepare other layouts externally.')
    header=bytes(b&127 for b in stream[:head])
    if header[8:12]!=b'fmt\0' or header[24:28]!=b'comp' or header[40:44]!=b'ciph':
        raise ValueError('Unsupported HCA header layout. Prepare this bank externally.')
    packed,frames,delay,pad=struct.unpack_from('>IIHH',stream,12)
    channels=packed>>24;rate=packed&0xffffff;samples=frames*1024-delay-pad
    frame_size=struct.unpack_from('>H',stream,28)[0]
    cipher=struct.unpack_from('>H',stream,44)[0]
    if channels!=2 or rate not in (44100,48000) or samples<=0 or samples>rate*1800:
        raise ValueError('Supported audio: stereo 44.1/48 kHz HCA, up to 30 minutes.')
    if cipher not in (0,56):raise ValueError('Only plain (type 0) and encrypted (type 56) HCA are supported.')
    if frame_size<8 or head+frames*frame_size!=len(stream):raise ValueError('HCA frame size/count does not match its payload.')
    if crc16(stream[:head]) or any(crc16(stream[head+i*frame_size:head+(i+1)*frame_size]) for i in range(frames)):
        raise ValueError('HCA checksum failure. The fixer cannot repair damaged audio frames.')
    return dict(sample_rate=rate,channels=channels,samples=samples,frames=frames,header_size=head,frame_size=frame_size,cipher_type=cipher)

def _pcm(decoded,info):
    with wave.open(io.BytesIO(decoded)) as wav:
        if (wav.getframerate(),wav.getnchannels(),wav.getsampwidth(),wav.getnframes())!=(info['sample_rate'],info['channels'],2,info['samples']):
            raise ValueError('Decoded audio does not match the HCA header.')
        return wav.readframes(wav.getnframes())

def repair_bank(acb,awb):
    """Return verified copies; retain stream IDs, offsets, cues and playback graph."""
    root,streams=require_hca_bank(acb,awb)
    if len(streams)!=1:raise ValueError('This fixer supports one streaming HCA waveform. Multi-stream banks require external work.')
    row=root['rows'][0];original=copy.deepcopy(row)
    source=streams[0][1];info=hca_info(source)
    waves=read_utf(row['WaveformTable']);wave_row=waves['rows'][0]
    if wave_row.get('Streaming')!=1 or wave_row.get('StreamAwbId')!=streams[0][0]:
        raise ValueError('Unsupported streaming waveform mapping.')
    if info['cipher_type']==0 and struct.unpack_from('<H',awb,14)[0]!=0:
        raise ValueError('This AWB uses a per-bank subkey. Prepare it externally; this profile requires subkey zero.')
    # Preserve the cue graph; only the explicitly named music cue gets a length change.
    names=read_utf(row['CueNameTable'])['rows']
    music=[n['CueIndex'] for n in names if n.get('CueName')=='music']
    cues=read_utf(row['CueTable'])
    if len(music)!=1 or not isinstance(music[0],int) or not 0<=music[0]<len(cues['rows']):
        raise ValueError('A single named music cue is required for this repair.')
    output=source
    if info['cipher_type']==0:
        try:from cricodecs import hca
        except ImportError as exc:
            raise ValueError('Install this version’s requirements and rebuild ChuniVaina to enable the ACB/AWB fixer.') from exc
        before=_pcm(hca.decode(source),info)
        output=hca.encrypt(source,cipher_type=56,keycode=CHUNITHM_AUDIO_KEY)
        if len(output)!=len(source) or _pcm(hca.decode(output,keycode=CHUNITHM_AUDIO_KEY),info)!=before:
            raise ValueError('Cipher conversion failed decoded-audio verification; no changes applied.')
        checked=hca_info(output)
        if checked!={**info,'cipher_type':56}:raise ValueError('Cipher conversion changed HCA properties.')
        verification='Decoded PCM is byte-identical before/after cipher conversion.'
    else:
        verification='Existing type-56 stream preserved byte-for-byte; its key compatibility is not inferred.'
    # Replace in the original AWB at its existing aligned offset, preserving padding/subkey.
    count,alignment=struct.unpack_from('<IH',awb,8)
    offset_width,id_width=awb[5],awb[6]
    raw_start=int.from_bytes(awb[16+count*id_width:16+count*id_width+offset_width],'little')
    start=(raw_start+alignment-1)//alignment*alignment
    if awb[start:start+len(source)]!=source:raise ValueError('Could not locate the original stream safely.')
    new_awb=awb[:start]+output+awb[start+len(source):]
    old_metadata={k:wave_row[k] for k in ('SamplingRate','NumSamples','NumChannels')}
    wave_row.update(SamplingRate=info['sample_rate'],NumSamples=info['samples'],NumChannels=info['channels'])
    row['WaveformTable']=rewrite_utf(row['WaveformTable'],waves)
    old_length=cues['rows'][music[0]]['Length']
    cues['rows'][music[0]]['Length']=info['samples']*1000//info['sample_rate']
    row['CueTable']=rewrite_utf(row['CueTable'],cues)
    hashes=read_utf(row['StreamAwbHash'])
    if len(hashes['rows'])!=1:raise ValueError('Multiple AWB ports are not supported.')
    hashes['rows'][0]['Hash']=hashlib.md5(new_awb).digest()
    row['StreamAwbHash']=rewrite_utf(row['StreamAwbHash'],hashes)
    new_acb=rewrite_utf(acb,root)
    if len(new_acb)!=len(acb):raise ValueError('Repair would change the ACB layout; prepare this bank externally.')
    changed={k for k in original if row[k]!=original[k]}
    if not changed<={'WaveformTable','CueTable','StreamAwbHash'}:raise ValueError('Unexpected playback metadata change.')
    verified,stored=require_hca_bank(new_acb,new_awb)
    if verified!=root or stored!=[(streams[0][0],output)]:raise ValueError('Repaired bank verification failed.')
    report={**info,'cipher_type_after':56,'bank_name_preserved':row.get('Name',''),
        'metadata_before':old_metadata,'music_cue_length_ms_before':old_length,
        'music_cue_length_ms_after':cues['rows'][music[0]]['Length'],
        'verification':verification,'playback_graph_preserved':True,
        'awb_sha256':hashlib.sha256(new_awb).hexdigest(),
        'changed':new_acb!=acb or new_awb!=awb,'audio_entry_source':KEY_SOURCE}
    return new_acb,new_awb,report

def save_repaired_zip(path,stem,acb,awb,report):
    if not stem or stem in ('.','..') or any(c in stem for c in '/\\:'):
        raise ValueError('Use a plain bank filename.')
    path=Path(path)
    # Exclusive creation refuses any overwrite, including the input bank/project.
    with path.open('xb') as out:
        try:
            with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
                z.writestr(stem+'.acb',acb);z.writestr(stem+'.awb',awb)
                z.writestr('repair-report.json',json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        except Exception:
            out.close();path.unlink();raise

def apply_project_pair(app,cue,pair):
    if not any(r is cue for r in app.docs):raise ValueError('The selected audio-bank item is no longer in this project.')
    require_hca_bank(*pair)
    a=cue.findtext('acbFile/path','');w=cue.findtext('awbFile/path','')
    if not a or not w or a==w:raise ValueError('The CueFile needs distinct ACB and AWB filenames.')
    from core import binary_slots,validate_asset
    changes={a:pair[0],w:pair[1]}
    for name,data in changes.items():
        validate_asset(name,data)
        if name in app.assets and app.assets[name]!=data:
            if any(root is not cue and any(root.findtext(path)==name for path,_,_ in binary_slots(root)) for root in app.docs):
                raise ValueError(name+' is shared with another item. Use a separate bank filename before replacing it.')
    app.assets.update(changes);app.dirty=True
