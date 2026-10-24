"""Conservative AFB texture replacement; never resize or relocate bundle data.

Supports FILS/FILE bundles containing AFRC resource payloads.
All non-texture bytes, resource names, geometry and animation remain untouched.
"""
from dataclasses import dataclass
import io
import math
import struct


def afb_regions(data):
    """Validate the outer container and find AFRC payloads inside FILE chunks."""
    def chunk(position, limit):
        if position + 12 > limit:
            raise ValueError('Truncated AFB chunk header.')
        size, header = struct.unpack_from('<II', data, position + 4)
        if header < 32 or header % 16 or position + header + size > limit:
            raise ValueError('Invalid AFB chunk bounds.')
        return position + header, position + header + size
    if len(data) < 64 or data[:4] != b'FILS':
        raise ValueError('Unsupported AFB: expected a FILS container.')
    start, end = chunk(0, len(data))
    regions = []
    position = start
    while position < end:
        if data[position:position+4] != b'FILE':
            raise ValueError('Unsupported AFB layout: expected FILE chunks.')
        child, next_position = chunk(position, end)
        while child < next_position:
            payload, child_end = chunk(child, next_position)
            if data[child:child+4] == b'AFRC':
                regions.append((payload, child_end))
            if child_end <= child:
                raise ValueError('Invalid AFB chunk length.')
            child = child_end
        position = next_position
    if not regions:
        raise ValueError('Unsupported AFB: no AFRC resource chunk found.')
    return regions


@dataclass(frozen=True)
class Texture:
    offset: int
    length: int
    width: int
    height: int
    mips: int
    format: str


def textures(data):
    result = []
    for start, end in afb_regions(data):
        position = start
        while True:
            position = data.find(b'DDS ', position, end)
            if position < 0:
                break
            if position + 128 > end or struct.unpack_from('<I', data, position+4)[0] != 124:
                position += 4
                continue
            height, width = struct.unpack_from('<II', data, position+12)
            mips = max(1, struct.unpack_from('<I', data, position+28)[0])
            fourcc = data[position+84:position+88]
            if struct.unpack_from('<I',data,position+76)[0] != 32 or struct.unpack_from('<I',data,position+112)[0] != 0 or struct.unpack_from('<I',data,position+24)[0] > 1:
                raise ValueError('Only standard 2D embedded DDS textures are supported.')
            if not (0 < width <= 16384 and 0 < height <= 16384) or mips > 1 + int(math.log2(max(width, height))):
                raise ValueError('Invalid embedded DDS dimensions/mip count.')
            if fourcc not in (b'DXT1', b'DXT3', b'DXT5'):
                raise ValueError('This bundle contains an unsupported DDS format. V1 supports DXT1/DXT3/DXT5 textures.')
            block = 8 if fourcc == b'DXT1' else 16
            length = 128 + sum(((max(1,width>>i)+3)//4)*((max(1,height>>i)+3)//4)*block for i in range(mips))
            if position + length > end:
                raise ValueError('Embedded DDS extends beyond its resource chunk.')
            result.append(Texture(position, length, width, height, mips, fourcc.decode('ascii')))
            position += length
    return result


def extract(data, texture):
    if texture not in textures(data):
        raise ValueError('Texture is not part of this bundle.')
    return data[texture.offset:texture.offset+texture.length]


def replace_texture(data, texture, replacement):
    """Require matching DDS layout and preserve the original DDS header as well."""
    original = extract(data, texture)
    if len(replacement) != texture.length or replacement[:4] != b'DDS ':
        raise ValueError('Replacement DDS byte length must match the embedded texture.')
    if struct.unpack_from('<I', replacement, 4)[0] != 124:
        raise ValueError('Replacement DDS has an invalid header.')
    h, w = struct.unpack_from('<II', replacement, 12)
    mips = max(1, struct.unpack_from('<I', replacement, 28)[0])
    if (w,h,mips,replacement[84:88]) != (texture.width,texture.height,texture.mips,texture.format.encode()):
        raise ValueError('Replacement must match texture dimensions, compression, and mip count.')
    start = texture.offset + 128
    end = texture.offset + texture.length
    return data[:start] + replacement[128:] + data[end:]


def encode_texture(image, texture):
    """Encode all mip levels using the template's compression and dimensions."""
    from PIL import Image
    image = image.convert('RGBA')
    if image.size != (texture.width, texture.height):
        raise ValueError('Frame the image to the texture dimensions first.')
    levels = []
    header = None
    for i in range(texture.mips):
        mip = image if i == 0 else image.resize((max(1,image.width>>i), max(1,image.height>>i)), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        mip.save(output, format='DDS', pixel_format=texture.format)
        encoded = output.getvalue()
        if header is None:
            header = bytearray(encoded[:128])
            struct.pack_into('<I', header, 28, texture.mips)
        levels.append(encoded[128:])
    result = bytes(header) + b''.join(levels)
    if len(result) != texture.length:
        raise ValueError('Encoder output length differs from the template texture.')
    return result


def apply_stage_assets(root, documents, assets, bundles):
    """Commit a dialog's draft bundles atomically under filenames for this stage."""
    from core import binary_slots, validate_asset
    changes = []
    number = int(root.findtext('name/id', '-1'))
    if number < 0:
        raise ValueError('Apply a valid stage ID first.')
    for path, prefix in (('notesFieldFile/path','nf'),('baseFile/path','st'),('objectFile/path','ob')):
        data = bundles.get(path)
        if data is None:
            continue
        name = f'{prefix}_{number}.afb'
        validate_asset(name, data)
        if root.find(path) is None:
            raise ValueError('Missing stage XML field: '+path)
        if name in assets and assets[name] != data:
            if any(r is not root and any(r.findtext(p) == name for p,_,_ in binary_slots(r)) for r in documents):
                raise ValueError(name+' is used by another stage. Choose a unique stage ID first.')
        changes.append((path,name,data))
    for path,name,data in changes:
        root.find(path).text = name
        assets[name] = data
    return len(changes)
