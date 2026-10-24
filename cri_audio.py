"""CRI UTF/AFS2 inspection and retargeting for user-prepared ACB/AWB pairs."""
import struct
import hashlib

FORMATS={0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'Q',7:'q',8:'f',9:'d',10:'I',11:'II'}

def read_utf(data):
    if len(data)<32 or data[:4]!=b'@UTF':raise ValueError('Invalid CRI UTF table.')
    size=struct.unpack_from('>I',data,4)[0]+8
    if size>len(data):raise ValueError('Truncated UTF table.')
    rows=struct.unpack_from('>H',data,10)[0]+8
    strings,blobs,name=struct.unpack_from('>III',data,12)
    strings+=8;blobs+=8
    ncol,stride,count=struct.unpack_from('>HHI',data,24)
    if ncol>1024 or count>100000 or rows+stride*count>size:raise ValueError('Invalid UTF dimensions.')
    def string(at):
        start=strings+at
        if not strings<=start<blobs:raise ValueError('Invalid UTF string offset.')
        end=data.find(b'\0',start,blobs)
        if end<0:raise ValueError('Unterminated UTF string.')
        return data[start:end].decode('utf-8')
    def value(at,kind):
        fmt='>'+FORMATS[kind];v=struct.unpack_from(fmt,data,at);at+=struct.calcsize(fmt)
        if kind==10:return string(v[0]),at
        if kind==11:
            a,n=v
            if blobs+a+n>size:raise ValueError('Invalid UTF blob offset.')
            return data[blobs+a:blobs+a+n],at
        return v[0],at
    p=32;cols=[]
    for _ in range(ncol):
        flags=data[p];off=struct.unpack_from('>I',data,p+1)[0];p+=5
        storage,kind=flags>>4,flags&15
        if kind not in FORMATS or storage not in (1,3,5):raise ValueError('Unsupported UTF column type.')
        constant=0 if kind<10 else '' if kind==10 else b''
        if storage==3:constant,p=value(p,kind)
        cols.append((string(off),kind,storage,constant))
    result=[]
    for i in range(count):
        p=rows+i*stride;record={}
        for key,kind,storage,constant in cols:
            if storage==5:v,p=value(p,kind)
            else:v=constant
            record[key]=v
        if p>rows+(i+1)*stride:raise ValueError('UTF row stride mismatch.')
        result.append(record)
    return {'name':string(name),'columns':[(k,t) for k,t,_,_ in cols], 'rows':result,'version':struct.unpack_from('>H',data,8)[0]}

def write_utf(table):
    strings=bytearray();offsets={};blobs=bytearray()
    def string(s):
        if s not in offsets:offsets[s]=len(strings);strings.extend(s.encode()+b'\0')
        return offsets[s]
    name=string(table['name']);cols=table['columns']
    definitions=b''.join(bytes([0x50|kind])+struct.pack('>I',string(key)) for key,kind in cols)
    rows=bytearray()
    for row in table['rows']:
        for key,kind in cols:
            v=row[key]
            if kind==10:values=(string(v),)
            elif kind==11:
                while len(blobs)%8:blobs.append(0)
                values=(len(blobs),len(v));blobs.extend(v)
            else:values=(v,)
            rows.extend(struct.pack('>'+FORMATS[kind],*values))
    stride=sum(struct.calcsize('>'+FORMATS[t]) for _,t in cols)
    row_off=32+len(definitions);str_off=row_off+len(rows)
    blob_off=(str_off+len(strings)+7)//8*8
    total=(blob_off+len(blobs)+7)//8*8
    if row_off-8>65535 or stride>65535:raise ValueError('UTF table too wide.')
    header=b'@UTF'+struct.pack('>IHHIIIHHI',total-8,table.get('version',1),row_off-8,str_off-8,blob_off-8,name,len(cols),stride,len(table['rows']))
    out=header+definitions+rows+strings
    out+=bytes(blob_off-len(out))+blobs
    return out+bytes(total-len(out))

def rewrite_utf(original,table):
    """Patch same-sized fields in place, retaining the reference's storage/layout.

    New-length strings/blobs fall back to the general serializer. Fixed-width numeric audio metadata uses same-sized replacements.
    """
    before=read_utf(original)
    if before==table:return original
    if before['columns']!=table['columns'] or len(before['rows'])!=len(table['rows']):return write_utf(table)
    out=bytearray(original);strings,blobs=struct.unpack_from('>II',original,12);strings+=8;blobs+=8
    row_start=struct.unpack_from('>H',original,10)[0]+8;stride=struct.unpack_from('>H',original,26)[0]
    p=32;locations=[]
    for key,kind in before['columns']:
        flags=original[p];p+=5;storage=flags>>4;constant=p
        if storage==3:p+=struct.calcsize('>'+FORMATS[kind])
        locations.append((key,kind,storage,constant))
    changes={}
    for i,(old,new) in enumerate(zip(before['rows'],table['rows'])):
        cursor=row_start+i*stride
        for key,kind,storage,constant in locations:
            pos=cursor if storage==5 else constant
            if storage==5:cursor+=struct.calcsize('>'+FORMATS[kind])
            if old[key]==new[key]:continue
            if storage==1:return write_utf(table)
            value=new[key]
            if kind==10:
                pos=strings+struct.unpack_from('>I',original,pos)[0]
                data=value.encode()
                if len(data)!=len(old[key].encode()):return write_utf(table)
            elif kind==11:
                off,length=struct.unpack_from('>II',original,pos);pos=blobs+off;data=value
                if len(data)!=length:return write_utf(table)
            else:data=struct.pack('>'+FORMATS[kind],value)
            if pos in changes and changes[pos]!=data:return write_utf(table)
            changes[pos]=data
    for pos,data in changes.items():out[pos:pos+len(data)]=data
    if read_utf(bytes(out))!=table:return write_utf(table)
    return bytes(out)

def read_awb(data):
    if len(data)<16 or data[:4]!=b'AFS2':raise ValueError('Invalid AWB bank.')
    version,offset_width,id_width,_=data[4:8]
    count,alignment=struct.unpack_from('<IH',data,8)
    if offset_width not in (2,4,8) or id_width not in (2,4) or count>100000 or alignment==0:raise ValueError('Unsupported AWB header.')
    head=16+count*id_width+(count+1)*offset_width
    if len(data)<head:raise ValueError('Truncated AWB header.')
    ids=[int.from_bytes(data[16+i*id_width:16+(i+1)*id_width],'little') for i in range(count)]
    p=16+count*id_width
    offsets=[int.from_bytes(data[p+i*offset_width:p+(i+1)*offset_width],'little') for i in range(count+1)]
    result=[]
    for i in range(count):
        start=(offsets[i]+alignment-1)//alignment*alignment;end=offsets[i+1]
        if not head<=start<=end<=len(data):raise ValueError('Invalid AWB stream range.')
        result.append((ids[i],data[start:end]))
    return result

def write_awb(streams):
    count=len(streams);head_size=16+count*2+(count+1)*4
    cursor=(head_size+31)//32*32;offsets=[head_size];payload=bytearray(bytes(cursor-head_size))
    for i,stream in enumerate(streams):
        payload.extend(stream);cursor+=len(stream);offsets.append(cursor)
        if i+1<count:
            pad=(-cursor)%32;payload.extend(bytes(pad));cursor+=pad
    header=b'AFS2'+bytes([1,4,2,0])+struct.pack('<IHH',count,32,0)
    header+=b''.join(struct.pack('<H',i) for i in range(count))
    header+=b''.join(struct.pack('<I',i) for i in offsets)
    return header+payload,header

def validate_bank(acb,awb):
    root=read_utf(acb);streams=read_awb(awb)
    if len(root['rows'])!=1:raise ValueError('ACB must have one header row.')
    row=root['rows'][0]
    header=row.get('StreamAwbAfs2Header',b'')
    if header[:4]==b'@UTF':header=read_utf(header)['rows'][0]['Header']
    if not header or header!=awb[:len(header)]:
        raise ValueError('ACB/AWB streaming headers do not match.')
    waves=read_utf(row['WaveformTable'])['rows']
    if len(waves)!=len(streams):raise ValueError('Waveform/stream count mismatch.')
    return root,streams

def retarget_bank(acb,awb,song_id):
    """Rename a prepared bank's sheet identity while preserving its cue names."""
    root,_=validate_bank(acb,awb);row=root['rows'][0]
    if 'Name' in row:row['Name']=f'music{int(song_id)}'
    if row.get('StreamAwbHash',b'')[:4]==b'@UTF':
        hashes=read_utf(row['StreamAwbHash'])
        if len(hashes['rows'])!=1:raise ValueError('Multiple external AWB ports are not supported.')
        hashes['rows'][0].update(Name=f'music{int(song_id)}',Hash=hashlib.md5(awb).digest())
        row['StreamAwbHash']=rewrite_utf(row['StreamAwbHash'],hashes)
    return rewrite_utf(acb,root),awb

def require_hca_bank(acb,awb):
    root,streams=validate_bank(acb,awb)
    row=root['rows'][0]
    name=row.get('Name','')
    number=name[5:] if name.startswith('music') else ''
    if len(streams)==2 and number.isdigit() and row.get('AcbGuid')==hashlib.md5(awb+number.encode()).digest():
        raise ValueError('This dual-stream bank layout is unsupported. Prepare a replacement ACB/AWB pair using CHUNITHM Customs Source and attach it in Song studio.')
    waves=read_utf(root['rows'][0]['WaveformTable'])['rows']
    for wave,(_,stream) in zip(waves,streams):
        magic=bytes(b&0x7f for b in stream[:4])
        if wave.get('EncodeType')!=2 or magic!=b'HCA\0':
            raise ValueError('This audio bank uses the old ADX/unsupported audio path. Prepare an HCA ACB/AWB pair using CHUNITHM Customs Source, then attach it in Song studio.')
    return root,streams

