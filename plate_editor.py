"""Layered desktop nameplate composer; original templates are drawn in code."""
import base64
import copy
import json
import uuid
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from PIL import Image, ImageTk, ImageDraw
from plate_model import SIZE, History, blank, starter, layer, image_layer, validate_layout, render, tile, hit_test
from artwork import decode, encode_nameplate_dds, generated_name
from core import asset_slots

class Composer(tk.Toplevel):
    def __init__(self,app):
        super().__init__(app);self.app=app;self.root=app.root()
        if self.root.tag!='NamePlateData':self.destroy();raise ValueError('Select a nameplate first.')
        self.title('ChuniVaina · Layered nameplate composer')
        self.geometry(f'{min(1280,self.winfo_screenwidth()-60)}x{min(850,self.winfo_screenheight()-90)}')
        self.minsize(980,650);self.transient(app);self.grab_set()
        # Reserve action rows before giving the editor its remaining height.
        # Packing an expanding Panedwindow before the footer can starve the
        # footer completely on short displays and macOS scaled resolutions.
        self.columnconfigure(0,weight=1);self.rowconfigure(2,weight=1)
        saved=app.nameplate_layouts.get(id(self.root))
        if saved:document=copy.deepcopy(saved)
        else:
            name=self.root.findtext('image/path','')
            if name in app.assets:
                document=blank();document['layers']=[image_layer(decode(app.assets[name]),'Existing DDS (flattened)')]
            else:document=starter()
        validate_layout(document)
        self.history=History(document);self.applied=copy.deepcopy(document);self.selected=None;self.drag=None;self.pending=None
        self.loading=False;self.property_dirty=False
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.status=tk.StringVar(value='Select a layer; drag on canvas or edit properties. Apply DDS & layers, then Save project to keep your work.')
        title=ttk.Frame(self,padding=10);title.grid(row=0,column=0,sticky='ew')
        ttk.Label(title,text='Nameplate composer',font=('Helvetica',19,'bold')).pack(side='left')
        ttk.Button(title,text='Apply DDS & layers',command=lambda:self.safe(self.apply)).pack(side='right',padx=(8,0))
        ttk.Label(title,text='576 × 228  ·  DXT5 / alpha / 1 mip').pack(side='right')
        bar=ttk.Frame(self,padding=(10,0,10,8));bar.grid(row=1,column=0,sticky='ew')
        for text,fn in [('Import images…',self.import_images),('Add text',self.add_text),('Add shape',self.add_shape),('Undo',self.undo),('Redo',self.redo)]:
            ttk.Button(bar,text=text,command=lambda f=fn:self.safe(f)).pack(side='left',padx=2)
        self.zoom=tk.StringVar(value='Fit');box=ttk.Combobox(bar,textvariable=self.zoom,values=['Fit','100%','150%','200%','300%'],state='readonly',width=7);box.pack(side='left',padx=8);box.bind('<<ComboboxSelected>>',lambda e:self.refresh())
        self.guides=tk.BooleanVar(value=True);ttk.Checkbutton(bar,text='Design guides',variable=self.guides,command=self.refresh).pack(side='left')
        self.compressed=tk.BooleanVar(value=False);ttk.Checkbutton(bar,text='DDS preview',variable=self.compressed,command=self.refresh).pack(side='left',padx=6)
        body=ttk.Panedwindow(self,orient='horizontal');body.grid(row=2,column=0,sticky='nsew',padx=10)
        left=ttk.Frame(body,padding=5);body.add(left,weight=1)
        ttk.Label(left,text='LAYERS · topmost first').pack(anchor='w')
        self.listing=tk.Listbox(left,width=24,exportselection=False);self.listing.pack(fill='both',expand=True,pady=5);self.listing.bind('<<ListboxSelect>>',self.select_list)
        actions=ttk.Frame(left);actions.pack(fill='x')
        for i,(text,fn) in enumerate([('Raise',lambda:self.reorder(1)),('Lower',lambda:self.reorder(-1)),('Duplicate',self.duplicate),('Delete',self.delete)]):
            ttk.Button(actions,text=text,command=lambda f=fn:self.safe(f)).grid(row=i//2,column=i%2,sticky='ew',padx=1,pady=2)
        center=ttk.Frame(body);body.add(center,weight=4)
        self.canvas=tk.Canvas(center,background='#242733',highlightthickness=0)
        sx=ttk.Scrollbar(center,orient='horizontal',command=self.canvas.xview);sy=ttk.Scrollbar(center,orient='vertical',command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=sx.set,yscrollcommand=sy.set)
        sy.pack(side='right',fill='y');sx.pack(side='bottom',fill='x');self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.schedule());self.canvas.bind('<ButtonPress-1>',self.press);self.canvas.bind('<B1-Motion>',self.move);self.canvas.bind('<ButtonRelease-1>',self.release)
        for key,dx,dy in [('Left',-1,0),('Right',1,0),('Up',0,-1),('Down',0,1)]:
            self.canvas.bind('<'+key+'>',lambda e,x=dx,y=dy:self.safe(lambda:self.nudge(x,y)))
            self.canvas.bind('<Shift-'+key+'>',lambda e,x=dx,y=dy:self.safe(lambda:self.nudge(x*10,y*10)))
        self.canvas.bind('<BackSpace>',lambda e:self.safe(self.delete));self.canvas.bind('<Delete>',lambda e:self.safe(self.delete))
        right=ttk.Frame(body,padding=5);body.add(right,weight=1)
        tabs=ttk.Notebook(right);tabs.pack(fill='both',expand=True)
        transform=ttk.Frame(tabs,padding=8);style=ttk.Frame(tabs,padding=8);tabs.add(transform,text='Transform');tabs.add(style,text='Text / style')
        self.vars={}
        for name,label in [('name','Layer name'),('x','X'),('y','Y'),('width','Width'),('height','Height'),('rotation','Rotation ° clockwise'),('opacity','Opacity 0–100')]:
            ttk.Label(transform,text=label).pack(anchor='w');var=tk.StringVar();self.vars[name]=var;ttk.Entry(transform,textvariable=var,width=22).pack(fill='x',pady=(0,5))
        self.visible=tk.BooleanVar(value=True);self.locked=tk.BooleanVar(value=False);self.aspect=tk.BooleanVar(value=True)
        ttk.Checkbutton(transform,text='Visible',variable=self.visible).pack(anchor='w');ttk.Checkbutton(transform,text='Lock layer',variable=self.locked).pack(anchor='w');ttk.Checkbutton(transform,text='Keep image aspect ratio',variable=self.aspect).pack(anchor='w')
        ttk.Label(style,text='Text (text layers only)').pack(anchor='w');self.text=tk.Text(style,height=4,width=23,wrap='word');self.text.pack(fill='x',pady=5)
        for name,label in [('font_size','Font size'),('color','Text / shape / gradient color'),('color2','Gradient end color'),('radius','Shape corner radius')]:
            ttk.Label(style,text=label).pack(anchor='w');var=tk.StringVar();self.vars[name]=var;ttk.Entry(style,textvariable=var,width=22).pack(fill='x',pady=(0,5))
        self.align=tk.StringVar(value='left');ttk.Combobox(style,textvariable=self.align,values=['left','center','right'],state='readonly',width=12).pack(anchor='w',pady=4)
        for text,fn in [('Pick primary color…',self.pick_color),('Choose font…',self.choose_font),('Use built-in font',self.reset_font)]:ttk.Button(style,text=text,command=lambda f=fn:self.safe(f)).pack(fill='x',pady=2)
        ttk.Label(style,text='Custom fonts are embedded in the layout. Choose a font with the glyphs you need. Text clips at its layer bounds.',wraplength=215).pack(pady=8)
        ttk.Button(right,text='Apply properties',command=lambda:self.safe(self.apply_properties)).pack(fill='x',pady=6)
        more=ttk.Frame(right);more.pack(fill='x')
        for text,fn in [('Center',self.center),('Fit',lambda:self.fit(False)),('Fill',lambda:self.fit(True)),('Flip H',lambda:self.flip('flip_x')),('Flip V',lambda:self.flip('flip_y'))]:ttk.Button(more,text=text,width=6,command=lambda f=fn:self.safe(f)).pack(side='left',padx=1)
        footer=ttk.Frame(self,padding=10);footer.grid(row=3,column=0,sticky='ew')
        for i,(text,fn) in enumerate([('Starter template',lambda:self.replace(starter())),('Blank canvas',lambda:self.replace(blank())),('Save layout…',self.save_layout),('Load layout…',self.load_layout),('Export PNG…',self.export_png)]):
            ttk.Button(footer,text=text,command=lambda f=fn:self.safe(f)).grid(row=0,column=i,sticky='ew',padx=2)
            footer.columnconfigure(i,weight=1)
        ttk.Label(self,textvariable=self.status,wraplength=900,padding=(10,0,10,8)).grid(row=4,column=0,sticky='ew')
        self.bind('<Command-s>',lambda e:self.safe(self.apply))
        self.bind('<Control-s>',lambda e:self.safe(self.apply))
        for variable in list(self.vars.values())+[self.visible,self.locked,self.align]:variable.trace_add('write',self.property_changed)
        self.text.bind('<<Modified>>',self.text_changed)
        self.after_idle(self.refresh)

    @property
    def doc(self):return self.history.document
    def safe(self,fn):
        try:
            if self.property_dirty and fn!=self.apply_properties:self.apply_properties()
            fn()
        except Exception as exc:messagebox.showerror('Nameplate composer',str(exc),parent=self)
    def property_changed(self,*_):
        if not self.loading and self.selected:self.property_dirty=True
    def text_changed(self,_=None):
        if self.text.edit_modified():self.property_changed();self.text.edit_modified(False)
    def current(self,editable=False):
        item=next((item for item in self.doc['layers'] if item['id']==self.selected),None)
        if item is None:raise ValueError('Select a layer first.')
        if editable and item.get('locked'):raise ValueError('Unlock this layer before editing it.')
        return item
    def checkpoint(self):self.history.checkpoint()
    def schedule(self):
        if self.pending is not None:self.after_cancel(self.pending)
        self.pending=self.after(25,lambda:self.safe(self.refresh))
    def refresh(self):
        if self.pending is not None:self.after_cancel(self.pending);self.pending=None
        self.canvas.delete('all')
        cw,ch=max(100,self.canvas.winfo_width()),max(100,self.canvas.winfo_height())
        self.scale=max(.1,min((cw-40)/576,(ch-40)/228)) if self.zoom.get()=='Fit' else float(self.zoom.get().rstrip('%'))/100
        w,h=round(576*self.scale),round(228*self.scale)
        self.origin=(20,20);self.canvas.configure(scrollregion=(0,0,max(cw,w+40),max(ch,h+40)))
        image=render(self.doc)
        if self.compressed.get():image=decode(encode_nameplate_dds(image))
        bg=Image.new('RGBA',SIZE,'#D0D0D0');draw=ImageDraw.Draw(bg)
        for yy in range(0,228,12):
            for xx in range(0,576,12):
                if (xx//12+yy//12)%2:draw.rectangle((xx,yy,xx+11,yy+11),fill='#A0A0A0')
        bg=Image.alpha_composite(bg,image).resize((w,h),Image.Resampling.LANCZOS)
        self.photo=ImageTk.PhotoImage(bg,master=self);self.canvas.create_image(20,20,image=self.photo,anchor='nw')
        if self.guides.get():
            s=self.scale
            self.canvas.create_rectangle(20+16*s,20+16*s,20+560*s,20+212*s,outline='#65E8DE',dash=(4,4))
            self.canvas.create_line(20+176*s,20,20+176*s,20+h,fill='#65E8DE',dash=(4,4))
        if self.selected:
            try:
                item=self.current();im,x,y=tile(item);s=self.scale
                self.canvas.create_rectangle(20+x*s,20+y*s,20+(x+im.width)*s,20+(y+im.height)*s,outline='#F5C76A',width=2)
            except ValueError:self.selected=None
        self.ids=[item['id'] for item in reversed(self.doc['layers'])];self.listing.delete(0,'end')
        for item in reversed(self.doc['layers']):
            self.listing.insert('end',('○ ' if not item.get('visible',True) else '● ')+('🔒 ' if item.get('locked') else '')+item['name'])
        if self.selected in self.ids:self.listing.selection_set(self.ids.index(self.selected))
    def populate(self):
        try:item=self.current()
        except ValueError:return
        self.loading=True
        for key,var in self.vars.items():var.set(item.get(key,24 if key=='font_size' else '#FFFFFF' if key in ('color','color2') else 0))
        self.visible.set(item.get('visible',True));self.locked.set(item.get('locked',False));self.align.set(item.get('align','left'))
        self.text.delete('1.0','end');self.text.insert('1.0',item.get('text',''));self.text.edit_modified(False)
        self.loading=False;self.property_dirty=False
    def select_list(self,_=None):
        if self.listing.curselection():
            target=self.ids[self.listing.curselection()[0]]
            if target==self.selected:return
            def change():self.selected=target;self.populate();self.refresh()
            self.safe(change)
    def coords(self,event):return ((self.canvas.canvasx(event.x)-20)/self.scale,(self.canvas.canvasy(event.y)-20)/self.scale)
    def press(self,event):
        if self.property_dirty:
            try:self.apply_properties()
            except Exception as exc:messagebox.showerror('Properties',str(exc),parent=self);return
        self.canvas.focus_set();x,y=self.coords(event)
        self.selected=hit_test(self.doc,x,y);self.drag=None
        if self.selected:
            item=self.current();self.drag=(x,y,item['x'],item['y'],False);self.populate()
        self.refresh()
    def move(self,event):
        if not self.drag:return
        x,y=self.coords(event);sx,sy,ox,oy,started=self.drag
        if not started and abs(x-sx)+abs(y-sy)<1:return
        if not started:self.checkpoint();self.drag=(sx,sy,ox,oy,True)
        item=self.current();item['x']=max(-8192,min(8192,round(ox+x-sx,1)));item['y']=max(-8192,min(8192,round(oy+y-sy,1)))
        self.loading=True;self.vars['x'].set(item['x']);self.vars['y'].set(item['y']);self.loading=False;self.schedule()
    def release(self,event):self.drag=None
    def changed(self):self.populate();self.refresh();self.status.set('Layout changed. Apply DDS & layers, then Save project to persist it. Guides are suggestions, not verified game-safe zones.')
    def import_images(self):
        files=filedialog.askopenfilenames(parent=self,title='Add image layers',filetypes=[('Images','*.png *.webp *.jpg *.jpeg *.dds'),('All files','*')])
        if not files:return
        added=[]
        for file in files:
            with Image.open(file) as image:added.append(image_layer(image,Path(file).stem))
        candidate=copy.deepcopy(self.doc);candidate['layers'].extend(added);validate_layout(candidate)
        self.checkpoint();self.history.document=candidate;self.selected=added[-1]['id'];self.changed()
    def add(self,item):
        candidate=copy.deepcopy(self.doc);candidate['layers'].append(item);validate_layout(candidate)
        self.checkpoint();self.history.document=candidate;self.selected=item['id'];self.changed()
    def add_text(self):self.add(layer('text','New text',x=170,y=80,width=370,height=70,text='YOUR TEXT',font_size=32,color='#FFFFFF',align='left'))
    def add_shape(self):self.add(layer('shape','New shape',x=50,y=50,width=150,height=90,color='#75E3D0',radius=12))
    def delete(self):
        item=self.current(True);self.checkpoint();self.doc['layers'].remove(item);self.selected=None;self.changed()
    def duplicate(self):
        item=copy.deepcopy(self.current());item.update(id=uuid.uuid4().hex,name=item['name']+' copy',x=item['x']+8,y=item['y']+8,locked=False);self.add(item)
    def reorder(self,direction):
        item=self.current(True);index=self.doc['layers'].index(item);target=max(0,min(len(self.doc['layers'])-1,index+direction))
        self.checkpoint();self.doc['layers'].pop(index);self.doc['layers'].insert(target,item);self.changed()
    def undo(self):self.history.undo();self.changed()
    def redo(self):self.history.redo();self.changed()
    def nudge(self,dx,dy):
        item=self.current(True);self.checkpoint();item['x']+=dx;item['y']+=dy;self.changed()
    def apply_properties(self):
        item=self.current();candidate=copy.deepcopy(item)
        candidate['locked']=self.locked.get();candidate['visible']=self.visible.get()
        if not item.get('locked'):
            candidate['name']=self.vars['name'].get().strip() or 'Layer'
            for key in ('x','y','width','height','rotation','opacity'):candidate[key]=float(self.vars[key].get())
            if self.aspect.get() and item['kind']=='image':
                if candidate['width']!=item['width']:candidate['height']=candidate['width']*item['height']/item['width']
                elif candidate['height']!=item['height']:candidate['width']=candidate['height']*item['width']/item['height']
            if item['kind'] in ('text','shape','gradient'):candidate['color']=self.vars['color'].get().strip()
            if item['kind']=='gradient':candidate['color2']=self.vars['color2'].get().strip()
            if item['kind']=='shape':candidate['radius']=max(0,min(2048,float(self.vars['radius'].get())))
            if item['kind']=='text':candidate.update(text=self.text.get('1.0','end-1c'),font_size=float(self.vars['font_size'].get()),align=self.align.get())
        trial=copy.deepcopy(self.doc);index=self.doc['layers'].index(item);trial['layers'][index]=candidate;validate_layout(trial)
        self.checkpoint();self.history.document=trial;self.changed()
    def center(self):
        item=self.current(True);self.checkpoint();item['x']=(576-item['width'])/2;item['y']=(228-item['height'])/2;self.changed()
    def fit(self,fill):
        item=self.current(True)
        if item['kind']!='image':raise ValueError('Fit/Fill apply to image layers.')
        from plate_model import read_image
        source=read_image(item['source']);factor=(max if fill else min)(576/source.width,228/source.height)
        width,height=source.width*factor,source.height*factor
        if max(width,height)>4096:raise ValueError('This source aspect ratio exceeds the transform limit; crop it externally first.')
        self.checkpoint();item.update(width=width,height=height,x=(576-width)/2,y=(228-height)/2,rotation=0);self.changed()
    def flip(self,key):
        item=self.current(True);self.checkpoint();item[key]=not item.get(key,False);self.changed()
    def pick_color(self):
        color=colorchooser.askcolor(parent=self)[1]
        if color:self.vars['color'].set(color)
    def choose_font(self):
        item=self.current(True)
        if item['kind']!='text':raise ValueError('Select a text layer.')
        file=filedialog.askopenfilename(parent=self,filetypes=[('Font','*.ttf *.otf *.ttc')])
        if file:
            data=Path(file).read_bytes()
            if len(data)>20000000:raise ValueError('Font must be under 20 MB.')
            candidate=copy.deepcopy(self.doc);index=self.doc['layers'].index(item);candidate['layers'][index]['font_data']=base64.b64encode(data).decode('ascii');validate_layout(candidate)
            self.checkpoint();self.history.document=candidate;self.changed()
    def reset_font(self):
        item=self.current(True);self.checkpoint();item.pop('font_data',None);self.changed()
    def replace(self,document):
        if messagebox.askyesno('Replace layout','Replace the canvas with this layout? You can undo this change.',parent=self):self.checkpoint();self.history.document=document;self.selected=None;self.changed()
    def save_layout(self):
        file=filedialog.asksaveasfilename(parent=self,defaultextension='.cvplate',filetypes=[('Layered nameplate','*.cvplate')])
        if file:validate_layout(self.doc);Path(file).write_text(json.dumps(self.doc,ensure_ascii=False),encoding='utf-8');self.status.set('Saved portable layout. Apply DDS & layers separately to update the project.')
    def load_layout(self):
        file=filedialog.askopenfilename(parent=self,filetypes=[('Layered nameplate','*.cvplate')])
        if file:self.replace(validate_layout(json.loads(Path(file).read_text(encoding='utf-8'))))
    def export_png(self):
        file=filedialog.asksaveasfilename(parent=self,defaultextension='.png',filetypes=[('PNG','*.png')])
        if file:render(self.doc).save(file,format='PNG');self.status.set('Exported composited PNG (no guides or selection).')
    def apply(self):
        validate_layout(self.doc);name=generated_name(self.root,0);data=encode_nameplate_dds(render(self.doc))
        others=[r for r in self.app.docs if r is not self.root and any(r.findtext(path)==name for path,_,_ in asset_slots(r))]
        if others and name in self.app.assets and self.app.assets[name]!=data:raise ValueError('This DDS filename is shared with another item. Change the nameplate ID before applying.')
        node=self.root.find('image/path')
        if node is None:raise ValueError('Nameplate XML is missing image/path.')
        self.app.assets[name]=data;node.text=name;self.app.nameplate_layouts[id(self.root)]=copy.deepcopy(self.doc);self.app.dirty=True
        self.applied=copy.deepcopy(self.doc);self.app.show();self.status.set('Applied DDS and editable layers. Close the composer, then Save project to persist both.')
    def close(self):
        if self.property_dirty:
            try:self.apply_properties()
            except Exception as exc:
                if not messagebox.askyesno('Invalid pending properties',str(exc)+'\nDiscard pending properties and close?',parent=self):return
                self.property_dirty=False
        if self.doc!=self.applied and not messagebox.askyesno('Unapplied nameplate edits','Close without applying these edits to the project? Apply DDS & layers first to retain them.',parent=self):return
        if self.pending is not None:self.after_cancel(self.pending)
        self.destroy()

def open_composer(app):return Composer(app)
