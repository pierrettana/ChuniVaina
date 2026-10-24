"""Render rights text in the 512×48, single-mip DXT5 rights-image format."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from artwork import encode_nameplate_dds,generated_name

SIZE=(512,48)

def default_font_path():
    candidates=[
        '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
        '/System/Library/Fonts/Hiragino Sans GB.ttc',
        '/System/Library/Fonts/Supplemental/Arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        'C:/Windows/Fonts/meiryo.ttc',
    ]
    return next((p for p in candidates if Path(p).is_file()),'')

def render_text(text,font_path='',font_size=16,align='left',color='#000000',fit=True):
    if not text.strip():raise ValueError('Enter the rights text first.')
    if len(text)>4096:raise ValueError('Rights text is too long (maximum 4096 characters).')
    if align not in ('left','center','right'):raise ValueError('Choose left, center or right alignment.')
    size=int(font_size)
    if not 6<=size<=96:raise ValueError('Font size must be from 6 to 96 pixels.')
    canvas=Image.new('RGBA',SIZE);draw=ImageDraw.Draw(canvas)
    def measure(n):
        font=ImageFont.truetype(font_path,n) if font_path else ImageFont.load_default(size=n)
        box=draw.multiline_textbbox((0,0),text,font=font,spacing=2,align=align)
        return font,box
    font,box=measure(size)
    while fit and (box[2]-box[0]>504 or box[3]-box[1]>40) and size>6:
        size-=1;font,box=measure(size)
    width,height=box[2]-box[0],box[3]-box[1]
    if width>504 or height>40:
        raise ValueError('Text does not fit 512×48. Shorten it, add a line break, or reduce the font size.')
    x={'left':4,'center':(512-width)/2,'right':508-width}[align]
    draw.multiline_text((x-box[0],(48-height)/2-box[1]),text,font=font,fill=color,spacing=2,align=align)
    return canvas,size

def apply_artwork(root,assets,documents,text,image):
    if root.tag!='RightsInfoData':raise ValueError('Select Rights information first.')
    if image.size!=SIZE:raise ValueError('Rights artwork must be 512×48 pixels.')
    if not text.strip():raise ValueError('Rights text is required.')
    name=generated_name(root,0);data=encode_nameplate_dds(image)
    if name in assets and assets[name]!=data:
        from core import asset_slots
        if any(r is not root and any(r.findtext(path)==name for path,_,_ in asset_slots(r)) for r in documents):
            raise ValueError(name+' is used by another item. Choose a different rights ID before applying.')
    root.find('rightsText').text=text;root.find('image/path').text=name;assets[name]=data
    return name
