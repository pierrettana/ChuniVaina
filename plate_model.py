"""Portable, non-destructive 576×228 nameplate documents."""
import base64
import copy
import io
import math
import re
import uuid
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont, ImageOps

SIZE=(576,228)

def image_payload(image):
    output=io.BytesIO();image.convert('RGBA').save(output,format='PNG')
    return base64.b64encode(output.getvalue()).decode('ascii')

@lru_cache(maxsize=24)
def read_image(payload):
    data=base64.b64decode(payload,validate=True)
    with Image.open(io.BytesIO(data)) as image:
        if image.width*image.height>20000000:raise ValueError('Source images must be 20 megapixels or smaller.')
        return ImageOps.exif_transpose(image).convert('RGBA')

def layer(kind,name,**properties):
    result=dict(id=uuid.uuid4().hex,kind=kind,name=name,x=0,y=0,width=576,height=228,
                rotation=0,opacity=100,visible=True,locked=False,flip_x=False,flip_y=False)
    result.update(properties);return result

def image_layer(image,name='Image'):
    image=ImageOps.exif_transpose(image).convert('RGBA')
    factor=min(576/image.width,228/image.height,1)
    w,h=max(1,round(image.width*factor)),max(1,round(image.height*factor))
    return layer('image',name,source=image_payload(image),width=w,height=h,x=(576-w)/2,y=(228-h)/2)

def starter():
    return dict(version=1,width=576,height=228,layers=[
        layer('gradient','Midnight background',color='#14233D',color2='#3C2362',locked=True),
        layer('shape','Portrait / artwork zone',x=14,y=14,width=132,height=200,color='#6557A8',radius=20),
        layer('shape','Accent line',x=162,y=44,width=4,height=140,color='#75E3D0',radius=2),
        layer('text','Title',x=188,y=62,width=356,height=54,text='YOUR NAMEPLATE',font_size=29,color='#FFFFFF',align='left'),
        layer('text','Subtitle',x=190,y=123,width=340,height=40,text='EDIT  /  MOVE  /  CREATE',font_size=15,color='#B6D6E9',align='left'),
        layer('shape','Bottom accent',x=190,y=177,width=120,height=3,color='#75E3D0',radius=1),
    ])

def blank():return dict(version=1,width=576,height=228,layers=[])

def validate_layout(document):
    if not isinstance(document,dict) or document.get('version')!=1 or (document.get('width'),document.get('height'))!=SIZE:
        raise ValueError('Expected a version-1, 576×228 nameplate layout.')
    layers=document.get('layers')
    if not isinstance(layers,list) or len(layers)>64:raise ValueError('A layout supports up to 64 layers.')
    ids=set()
    for item in layers:
        if not isinstance(item,dict) or not isinstance(item.get('id'),str) or item['id'] in ids:raise ValueError('Layer IDs must be unique strings.')
        ids.add(item['id'])
        if item.get('kind') not in ('image','text','shape','gradient'):raise ValueError('Unknown layer kind.')
        for key in ('x','y','width','height','rotation','opacity'):
            value=item.get(key)
            if not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('Invalid layer '+key)
        if not 1<=item['width']<=4096 or not 1<=item['height']<=4096:raise ValueError('Layer dimensions must be 1–4096 pixels.')
        if abs(item['x'])>8192 or abs(item['y'])>8192:raise ValueError('Layer position is out of range.')
        if not 0<=item['opacity']<=100:raise ValueError('Opacity must be 0–100.')
        for key in ('color','color2'):
            if key in item and not re.fullmatch(r'#[0-9a-fA-F]{6}',item[key]):raise ValueError('Use a #RRGGBB color.')
        if item['kind']=='image':read_image(item['source'])
        if item['kind']=='text':
            if not isinstance(item.get('text'),str) or len(item['text'])>10000:raise ValueError('Text must be 10,000 characters or less.')
            if not 1<=float(item.get('font_size',24))<=512:raise ValueError('Font size must be 1–512.')
            if item.get('font_data'):
                ImageFont.truetype(io.BytesIO(base64.b64decode(item['font_data'],validate=True)),round(item['font_size']))
    return document

def tile(item):
    w,h=round(item['width']),round(item['height']);kind=item['kind']
    if kind=='image': image=read_image(item['source']).resize((w,h),Image.Resampling.LANCZOS)
    elif kind=='text':
        image=Image.new('RGBA',(w,h));draw=ImageDraw.Draw(image)
        size=round(item.get('font_size',24))
        font=ImageFont.truetype(io.BytesIO(base64.b64decode(item['font_data'])),size) if item.get('font_data') else ImageFont.load_default(size=size)
        text=item.get('text','');bounds=draw.multiline_textbbox((0,0),text,font=font,spacing=4)
        align=item.get('align','left');span=bounds[2]-bounds[0]
        x=0 if align=='left' else (w-span)/2 if align=='center' else w-span
        draw.multiline_text((x-bounds[0],-bounds[1]),text,font=font,fill=item.get('color','#FFFFFF'),spacing=4,align=align)
    elif kind=='gradient':
        image=Image.new('RGBA',(w,h));draw=ImageDraw.Draw(image)
        a=tuple(int(item.get('color','#14233D')[i:i+2],16) for i in (1,3,5))
        b=tuple(int(item.get('color2','#3C2362')[i:i+2],16) for i in (1,3,5))
        for x in range(w):
            t=x/max(1,w-1);draw.line((x,0,x,h),fill=tuple(round(c*(1-t)+d*t) for c,d in zip(a,b))+(255,))
    else:
        image=Image.new('RGBA',(w,h));ImageDraw.Draw(image).rounded_rectangle((0,0,w-1,h-1),radius=max(0,item.get('radius',0)),fill=item.get('color','#FFFFFF'))
    if item.get('flip_x'):image=ImageOps.mirror(image)
    if item.get('flip_y'):image=ImageOps.flip(image)
    if item.get('rotation'):image=image.rotate(-item['rotation'],resample=Image.Resampling.BICUBIC,expand=True)
    if item['opacity']!=100:image.putalpha(image.getchannel('A').point(lambda alpha:round(alpha*item['opacity']/100)))
    x=round(item['x']+(w-image.width)/2);y=round(item['y']+(h-image.height)/2)
    return image,x,y

def render(document):
    validate_layout(document);canvas=Image.new('RGBA',SIZE)
    for item in document['layers']:
        if item.get('visible',True):
            image,x,y=tile(item);canvas.alpha_composite(image,(x,y))
    return canvas

def hit_test(document,x,y):
    for item in reversed(document['layers']):
        if not item.get('visible',True) or item.get('locked'):continue
        image,left,top=tile(item);px,py=math.floor(x-left),math.floor(y-top)
        if 0<=px<image.width and 0<=py<image.height and image.getpixel((px,py))[3]>8:return item['id']
    return None

class History:
    def __init__(self,document):self.document=copy.deepcopy(document);self.undo_stack=[];self.redo_stack=[]
    def checkpoint(self):
        self.undo_stack.append(copy.deepcopy(self.document));self.undo_stack=self.undo_stack[-40:];self.redo_stack=[]
    def undo(self):
        if self.undo_stack:self.redo_stack.append(copy.deepcopy(self.document));self.document=self.undo_stack.pop()
    def redo(self):
        if self.redo_stack:self.undo_stack.append(copy.deepcopy(self.document));self.document=self.redo_stack.pop()
