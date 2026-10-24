"""Template-based stage texture browser. No geometry or animation editing."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageOps
from artwork import compose, decode, checker
from stage_model import textures, extract, replace_texture, encode_texture, apply_stage_assets, afb_regions


def open_editor(app):
    root = app.root()
    if root.tag != 'StageData':
        raise ValueError('Select a Stage item.')
    win = tk.Toplevel(app)
    win.title('ChuniVaina · Stage texture editor')
    win.geometry(f'1060x{min(860,win.winfo_screenheight()-90)}')
    win.minsize(900,650)
    win.transient(app)
    win.grab_set()
    win.columnconfigure(0,weight=1)
    win.rowconfigure(2,weight=1)
    header = ttk.Frame(win,padding=12)
    header.grid(row=0,column=0,sticky='ew')
    ttk.Label(header,text='Stage · '+root.findtext('name/str',''),font=('Helvetica',18,'bold')).pack(side='left')
    paths = [('baseFile/path','Base stage'),('notesFieldFile/path','Note field'),('objectFile/path','Objects (optional)')]
    bundles = {path:app.assets[root.findtext(path)] for path,_ in paths if root.findtext(path) in app.assets}
    applied = dict(bundles)
    active = [paths[0][0]]
    items = []
    source = [None]
    photo = [None]
    pending = [None]
    controls_loading = [False]
    replacement = [None]
    mode = tk.StringVar(value='Crop')
    zoom = tk.DoubleVar(value=1)
    x = tk.DoubleVar(value=.5)
    y = tk.DoubleVar(value=.5)
    dirty = [False]
    status = tk.StringVar(value='Import a stage XML with its AFB files beside it, or attach bundles below. Replacements remain a draft until Apply stage bundles.')
    details = tk.StringVar()
    ttk.Label(win,text='Replace template textures; geometry, animation, resource names and effects behavior are preserved. Preview shows one texture, not a rendered game scene.',wraplength=1000,padding=(12,0,12,10)).grid(row=1,column=0,sticky='w')
    body = ttk.Frame(win,padding=12)
    body.grid(row=2,column=0,sticky='nsew')
    body.columnconfigure(0,weight=1)
    body.columnconfigure(1,weight=2)
    body.rowconfigure(1,weight=1)
    bundle_box = ttk.Combobox(body,state='readonly',values=[label for _,label in paths])
    bundle_box.grid(row=0,column=0,sticky='ew',padx=(0,14),pady=(0,8))
    bundle_box.current(0)
    tree = ttk.Treeview(body,columns=('size','format'),show='tree headings',height=7,selectmode='browse')
    tree.heading('#0',text='Embedded texture')
    tree.column('#0',width=105)
    tree.heading('size',text='Dimensions'); tree.column('size',width=100)
    tree.heading('format',text='Format'); tree.column('format',width=65)
    tree.grid(row=1,column=0,sticky='nsew',padx=(0,14))
    left_actions = ttk.Frame(body)
    left_actions.grid(row=2,column=0,sticky='ew',padx=(0,14),pady=8)
    right = ttk.Frame(body)
    right.grid(row=0,column=1,rowspan=3,sticky='nsew')
    preview = ttk.Label(right,anchor='center')
    preview.pack(fill='both',expand=True)
    ttk.Label(right,textvariable=details,wraplength=540).pack(fill='x',pady=4)
    framing = ttk.Frame(right); framing.pack(fill='x')
    ttk.Label(framing,text='PNG framing').pack(side='left')
    ttk.Combobox(framing,textvariable=mode,values=['Fit','Crop'],state='readonly',width=8).pack(side='left',padx=8)
    for label,var,low,high in [('Zoom',zoom,.25,3),('Horizontal',x,0,1),('Vertical',y,0,1)]:
        row=ttk.Frame(right);row.pack(fill='x')
        ttk.Label(row,text=label,width=12).pack(side='left')
        ttk.Scale(row,variable=var,from_=low,to=high).pack(side='left',fill='x',expand=True)
    actions=ttk.Frame(win,padding=(12,4))
    actions.grid(row=3,column=0,sticky='ew')
    ttk.Label(win,textvariable=status,wraplength=1000,padding=12).grid(row=4,column=0,sticky='ew')

    def guard(fn):
        def run():
            try: return fn()
            except Exception as exc: messagebox.showerror('Stage editor',str(exc),parent=win)
        return run

    def selected():
        selection=tree.selection()
        if not selection: raise ValueError('Select an embedded texture first.')
        return items[int(selection[0])]

    def discard_pending():
        if source[0] is None and replacement[0] is None: return True
        return messagebox.askyesno('Pending texture','Discard the uncommitted texture replacement? Use Replace selected texture to keep it in the stage draft.',parent=win)

    def reset_pending():
        source[0]=None;replacement[0]=None
        controls_loading[0]=True
        mode.set('Crop');zoom.set(1);x.set(.5);y.set(.5)
        controls_loading[0]=False

    def refresh_preview():
        pending[0]=None
        if not tree.selection():
            preview.configure(image='');details.set('Attach an AFB for this slot to begin.' if active[0] not in bundles else 'No supported embedded textures. Some bundles contain scene resources without editable textures.')
            return
        texture=selected()
        if source[0] is not None:
            image=compose(source[0],(texture.width,texture.height),mode.get(),zoom.get(),x.get(),y.get())
        else:
            image=decode(replacement[0] if replacement[0] is not None else extract(bundles[active[0]],texture))
        photo[0]=ImageTk.PhotoImage(checker(image,310),master=win)
        preview.configure(image=photo[0])
        details.set(f'Texture {tree.selection()[0]} · {texture.width}×{texture.height} · {texture.format} · {texture.mips} mip level(s)'+ (' · Pending replacement' if source[0] is not None or replacement[0] is not None else ''))

    def schedule(*_):
        if controls_loading[0]: return
        if pending[0] is not None: win.after_cancel(pending[0])
        pending[0]=win.after(100,guard(refresh_preview))
    for var in (mode,zoom,x,y): var.trace_add('write',schedule)

    previous=[None]
    def select(_=None):
        selection=tree.selection()
        if selection and selection[0]==previous[0]: return
        if not discard_pending():
            if previous[0] is not None: tree.selection_set(previous[0])
            return
        previous[0]=selection[0] if selection else None
        reset_pending();refresh_preview()
    tree.bind('<<TreeviewSelect>>',lambda _:guard(select)())

    def populate():
        previous[0]=None
        reset_pending()
        tree.delete(*tree.get_children())
        items[:]=textures(bundles[active[0]]) if active[0] in bundles else []
        for i,texture in enumerate(items):
            tree.insert('', 'end',iid=str(i),text=f'Texture {i}',values=(f'{texture.width}×{texture.height}',texture.format))
        if items:
            tree.selection_set('0');previous[0]='0'
        refresh_preview()

    def switch(_=None):
        if not discard_pending():
            bundle_box.current(next(i for i,(p,_) in enumerate(paths) if p==active[0]));return
        active[0]=paths[bundle_box.current()][0]
        populate()
    bundle_box.bind('<<ComboboxSelected>>',lambda _:guard(switch)())

    def attach():
        file=filedialog.askopenfilename(parent=win,title='Attach '+paths[bundle_box.current()][1]+' AFB',filetypes=[('AFB bundle','*.afb')])
        if not file or not discard_pending(): return
        data=Path(file).read_bytes()
        afb_regions(data);textures(data)
        bundles[active[0]]=data;dirty[0]=True
        populate();status.set('Bundle attached to draft. Apply stage bundles to keep it in the project.')

    def choose_image():
        selected()
        file=filedialog.askopenfilename(parent=win,title='Choose replacement artwork',filetypes=[('Images','*.png *.webp *.jpg *.jpeg')])
        if not file: return
        with Image.open(file) as image:
            image.load();source[0]=ImageOps.exif_transpose(image).convert('RGBA')
        replacement[0]=None
        refresh_preview();status.set('Adjust framing, then Replace selected texture. Alpha is preserved by the template compression format.')

    def choose_dds():
        texture=selected()
        file=filedialog.askopenfilename(parent=win,title='Choose matching DDS',filetypes=[('DDS texture','*.dds')])
        if not file: return
        data=Path(file).read_bytes()
        replace_texture(bundles[active[0]],texture,data)
        decode(data)
        source[0]=None;replacement[0]=data
        refresh_preview();status.set('Matching DDS loaded. Click Replace selected texture to commit it to the draft.')

    def replace():
        texture=selected()
        if source[0] is not None:
            image=compose(source[0],(texture.width,texture.height),mode.get(),zoom.get(),x.get(),y.get())
            data=encode_texture(image,texture)
        elif replacement[0] is not None: data=replacement[0]
        else: raise ValueError('Choose a replacement image or DDS first.')
        bundles[active[0]]=replace_texture(bundles[active[0]],texture,data)
        dirty[0]=True;reset_pending();refresh_preview()
        status.set('Texture replaced in draft. Preview now shows DDS compression. Apply stage bundles to keep it in the project.')

    def export_texture(png):
        texture=selected()
        extension='.png' if png else '.dds'
        file=filedialog.asksaveasfilename(parent=win,defaultextension=extension,initialfile=f'texture_{tree.selection()[0]}{extension}',filetypes=[('Texture','*'+extension)])
        if file:
            data=extract(bundles[active[0]],texture)
            if png: decode(data).save(file,format='PNG')
            else: Path(file).write_bytes(data)
            status.set('Exported committed draft texture. Uncommitted replacements are excluded.')

    def reset_bundle():
        if not discard_pending(): return
        if active[0] in applied: bundles[active[0]]=applied[active[0]]
        else: bundles.pop(active[0],None)
        dirty[0]=bundles!=applied;populate()
        status.set('Restored this bundle to its last applied project state.')

    def apply():
        if source[0] is not None or replacement[0] is not None: replace()
        count=apply_stage_assets(root,app.docs,app.assets,bundles)
        if not count: raise ValueError('Attach the stage bundles first.')
        applied.clear();applied.update(bundles)
        dirty[0]=False;app.dirty=True;app.show()
        status.set(f'Applied {count} stage bundle(s). Close this editor and Save project to keep them on disk.')

    def close():
        if (dirty[0] or source[0] is not None or replacement[0] is not None) and not messagebox.askyesno('Unapplied stage changes','Discard changes since the last Apply stage bundles?',parent=win): return
        if pending[0] is not None: win.after_cancel(pending[0])
        win.destroy()

    for label,fn in [('Attach AFB…',attach),('Restore bundle',reset_bundle),('Export PNG…',lambda:export_texture(True)),('Export DDS…',lambda:export_texture(False))]:
        ttk.Button(left_actions,text=label,command=guard(fn)).pack(fill='x',pady=2)
    for label,fn in [('Choose image…',choose_image),('Import matching DDS…',choose_dds),('Replace selected texture',replace)]:
        ttk.Button(actions,text=label,command=guard(fn)).pack(side='left',padx=3)
    ttk.Button(header,text='Apply stage bundles',command=guard(apply)).pack(side='right')
    ttk.Button(actions,text='Close',command=close).pack(side='right')
    win.bind('<Command-s>',lambda _:guard(apply)())
    win.bind('<Control-s>',lambda _:guard(apply)())
    win.protocol('WM_DELETE_WINDOW',close)
    populate()
