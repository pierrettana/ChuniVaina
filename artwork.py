"""Artwork sizing, lossless BGRA DDS mip generation, and desktop preview."""
import io
import math
import re
import struct
from PIL import Image, ImageOps, ImageDraw

SIZES=(1080,512,128)

def compose(source, size, mode='Fit', zoom=1.0, x=0.5, y=0.5):
    source=ImageOps.exif_transpose(source).convert('RGBA')
    if mode not in ('Fit','Crop'): raise ValueError('Unknown resize mode.')
    width,height=(size,size) if isinstance(size,int) else size
    scale=(min if mode=='Fit' else max)(width/source.width,height/source.height)*float(zoom)
    scaled=source.resize((max(1,round(source.width*scale)),max(1,round(source.height*scale))),Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(width,height))
    canvas.paste(scaled,(round((width-scaled.width)*float(x)),round((height-scaled.height)*float(y))))
    return canvas

def encode_dds(image):
    """Match the samples: 32-bit A8R8G8B8 masks, BGRA bytes, full mip chain."""
    image=image.convert('RGBA'); w,h=image.size
    count=1+int(math.log2(max(w,h)))
    header=bytearray(128); header[:4]=b'DDS '
    struct.pack_into('<7I',header,4,124,0x2100F,h,w,w*4,0,count)
    struct.pack_into('<8I',header,76,32,0x41,0,32,0xff0000,0xff00,0xff,0xff000000)
    struct.pack_into('<I',header,108,0x401008)
    levels=[]
    for level in range(count):
        mip=image if level==0 else image.resize((max(1,w>>level),max(1,h>>level)),Image.Resampling.LANCZOS)
        levels.append(mip.tobytes('raw','BGRA'))
    return bytes(header)+b''.join(levels)

def opaque(image):
    result=Image.new('RGBA',image.size,(0,0,0,255))
    return Image.alpha_composite(result,image.convert('RGBA'))


def encode_world_dds(image):
    """Match supplied event/map art: opaque DXT1, a single mip level."""
    out=io.BytesIO()
    opaque(image).convert('RGB').save(out,format='DDS',pixel_format='DXT1')
    data=bytearray(out.getvalue())
    struct.pack_into('<I',data,20,((image.width+3)//4)*((image.height+3)//4)*8)
    struct.pack_into('<I',data,28,1)
    return bytes(data)


def encode_nameplate_dds(image):
    out=io.BytesIO();image.convert('RGBA').save(out,format='DDS',pixel_format='DXT5')
    data=bytearray(out.getvalue())
    struct.pack_into('<I',data,20,((image.width+3)//4)*((image.height+3)//4)*16)
    struct.pack_into('<I',data,28,1)
    return bytes(data)


def decode(data):
    with Image.open(io.BytesIO(data)) as im:
        im.load(); return im.convert('RGBA')

def checker(image, size=280):
    bg=Image.new('RGB',(size,size),'#dddddd'); draw=ImageDraw.Draw(bg)
    for y in range(0,size,16):
        for x in range(0,size,16):
            if (x//16+y//16)%2: draw.rectangle((x,y,x+15,y+15),fill='#aaaaaa')
    im=image.copy(); im.thumbnail((size,size),Image.Resampling.LANCZOS)
    bg.paste(im,((size-im.width)//2,(size-im.height)//2),im)
    return bg

def generated_name(root, slot):
    match=re.fullmatch(r'chara(\d+)_(\d+)',root.findtext('name/str',''))
    if root.tag=='NamePlateData': return f'CHU_UI_NamePlate_{int(root.findtext("name/id")):08d}.dds'
    if root.tag=='RightsInfoData': return f'CHU_UI_Rights_{int(root.findtext("name/id")):04d}.dds'
    if root.tag=='StageData': return f'CHU_UI_Stage_{root.findtext("name/id")}.dds'
    if root.tag=='MusicData': return f'CHU_UI_Jacket_{root.findtext("name/id")}.dds'
    if root.tag=='DDSMapData': return f'CHU_MAP_custom_{root.findtext("name/id")}.dds'
    if root.tag=='EventData': return f'CHU_info_custom_{root.findtext("name/id")}.dds'
    if match: return f'CHU_UI_Character_{match[1]}_{match[2]}_{slot:02}.dds'
    return f'CHU_UI_Artwork_{root.findtext("name/id")}_{slot:02}.dds'


def open_studio(app):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    from PIL import ImageTk
    root=app.root()
    from core import asset_slots
    slots=asset_slots(root)
    if not slots: raise ValueError('Select character artwork, nameplate, map artwork, an event, or a stage preview.')
    world=root.tag in ('DDSMapData','EventData','StageData','MusicData')
    nameplate=root.tag=='NamePlateData'
    def render(card, slot):
        result=compose(card['source'],slots[slot][2],card['mode'].get(),card['zoom'].get(),card['x'].get(),card['y'].get())
        return opaque(result) if world else result
    win=tk.Toplevel(app); win.title('ChuniVaina · Artwork studio'); win.geometry('1000x740' if len(slots)==3 else '640x740')
    win.transient(app); win.grab_set()
    ttk.Label(win,text='PNG → DDS · Live artwork preview',font=('Helvetica',19,'bold'),padding=14).pack(anchor='w')
    ttk.Label(win,text='Fit keeps the whole image; Crop fills the square. Position moves padding or chooses the crop. Changes apply only when you click Apply.',wraplength=930,padding=(14,0,14,10)).pack(anchor='w')
    if nameplate: ttk.Label(win,text='Nameplate output uses DXT5 with alpha and one mip level (576×228).',wraplength=580,padding=(14,0,14,8)).pack(anchor='w')
    if world: ttk.Label(win,text='Map/event/stage previews use DXT1, one mip level, with no alpha. Transparent pixels and Fit padding become black. Stage gameplay textures use Stage texture editor.',wraplength=580,padding=(14,0,14,8)).pack(anchor='w')
    body=ttk.Frame(win,padding=10); body.pack(fill='both',expand=True)
    cards=[]; pending=[None]
    status=tk.StringVar()
    def refresh():
        pending[0]=None
        for slot,card in enumerate(cards):
            try:
                if card['source'] is not None:
                    image=render(card,slot)
                    card['rendered']=image
                else:
                    filename=root.findtext(slots[slot][0],'')
                    image=decode(app.assets[filename]) if filename in app.assets else Image.new('RGBA',slots[slot][2])
                photo=ImageTk.PhotoImage(checker(image,270),master=win)
                card['photo']=photo; card['preview'].configure(image=photo)
            except Exception as exc: status.set(str(exc))
    def schedule(*args):
        if pending[0] is not None: win.after_cancel(pending[0])
        pending[0]=win.after(100,refresh)
    def choose(slot=None):
        path=filedialog.askopenfilename(parent=win,title='Choose PNG artwork',filetypes=[('PNG image','*.png')])
        if not path: return
        try:
            with Image.open(path) as im:
                im.load(); image=ImageOps.exif_transpose(im).convert('RGBA')
            targets=range(len(slots)) if slot is None else [slot]
            for i in targets:
                cards[i]['source']=image.copy(); cards[i]['label'].set(f'{image.width}×{image.height} · {path.split("/")[-1]}')
            status.set('PNG loaded. Adjust each slot, then Apply converted artwork.'); refresh()
        except Exception as exc: messagebox.showerror('PNG import',str(exc),parent=win)
    for slot,(_,_,dimensions) in enumerate(slots):
        width,height=dimensions
        frame=ttk.LabelFrame(body,text=f'Slot {slot} · {width} × {height}',padding=8); frame.grid(row=0,column=slot,sticky='nsew',padx=4); body.columnconfigure(slot,weight=1)
        card={'source':None,'rendered':None,'mode':tk.StringVar(value='Fit'),'zoom':tk.DoubleVar(value=1),'x':tk.DoubleVar(value=.5),'y':tk.DoubleVar(value=.5),'label':tk.StringVar(value=root.findtext(slots[slot][0],'No DDS attached'))}
        cards.append(card)
        card['preview']=ttk.Label(frame); card['preview'].pack()
        ttk.Label(frame,textvariable=card['label'],wraplength=265).pack(pady=6)
        ttk.Button(frame,text='Choose PNG for this slot…',command=lambda i=slot:choose(i)).pack(fill='x')
        ttk.Combobox(frame,textvariable=card['mode'],values=['Fit','Crop'],state='readonly',width=12).pack(pady=6)
        for title,key,low,high in [('Zoom','zoom',.25,3),('Horizontal position','x',0,1),('Vertical position','y',0,1)]:
            ttk.Label(frame,text=title).pack(anchor='w')
            ttk.Scale(frame,from_=low,to=high,variable=card[key],command=schedule).pack(fill='x')
        card['mode'].trace_add('write',schedule)
        def reset(c=card):
            c['mode'].set('Fit'); c['zoom'].set(1); c['x'].set(.5); c['y'].set(.5); schedule()
        ttk.Button(frame,text='Reset framing',command=reset).pack(pady=6)
    controls=ttk.Frame(win,padding=12); controls.pack(fill='x')
    ttk.Button(controls,text='Use one PNG for all slots…',command=choose).pack(side='left')
    def apply():
        try:
            refresh()
            changes=[]
            for slot,card in enumerate(cards):
                if card['source'] is None: continue
                image=render(card,slot)
                data=(encode_nameplate_dds if nameplate else encode_world_dds if world else encode_dds)(image); name=generated_name(root,slot)
                node=root.find(slots[slot][0])
                if node is None: raise ValueError('Missing artwork slot path in XML.')
                changes.append((node,name,data))
            if not changes: raise ValueError('Choose a PNG first. Existing DDS artwork is previewed without conversion.')
            for node,name,data in changes:
                if name in app.assets and data!=app.assets[name]:
                    # Replacing one artwork item must not silently change another item.
                    others=[r for r in app.docs if r is not root and any(r.findtext(path)==name for path,_,_ in asset_slots(r))]
                    if others: raise ValueError(name+' is used by another artwork item. Choose a different artwork ID/reference name first.')
            for node,name,data in changes: app.assets[name]=data; node.text=name
            app.dirty=True
            if app.current is not None and app.root() is root: app.show()
            status.set(f'Applied {len(changes)} slot(s). Save your project to keep the converted artwork.')
        except Exception as exc: messagebox.showerror('Artwork conversion',str(exc),parent=win)
    ttk.Button(controls,text='Apply converted artwork',command=apply).pack(side='right')
    ttk.Label(win,textvariable=status,wraplength=950,padding=12).pack(fill='x')
    def close():
        if pending[0] is not None: win.after_cancel(pending[0])
        win.destroy()
    win.protocol('WM_DELETE_WINDOW',close)
    refresh()
