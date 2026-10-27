"""Song studio: UGC conversion, jacket and prepared audio-bank import."""
from pathlib import Path
import copy,threading,queue
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from chart_converter import parse_ugc
from song_model import build_song,DIFFICULTIES
from core import parse,identity,binary_slots
from song_versions import version_options,version_label

def open_editor(app,base,new=False):
    from song_notice import show_notice
    show_notice(app)
    current=app.root() if not new and app.current is not None and app.root().tag=='MusicData' else None
    template=copy.deepcopy(current) if current is not None else parse((base/'templates/Music.xml').read_text())
    cue_template=parse((base/'templates/CueFile.xml').read_text())
    old_cue=next((r for r in app.docs if current is not None and r.tag=='CueFileData' and r.findtext('name/id')==current.findtext('cueFileName/id')),None)
    win=tk.Toplevel(app);win.title('ChuniVaina · Song studio');win.geometry('820x760');win.transient(app);win.grab_set()
    body=ttk.Frame(win,padding=16);body.pack(fill='both',expand=True)
    ttk.Label(body,text='Custom song · UGC conversion',font=('Helvetica',20,'bold')).pack(anchor='w')
    ttk.Label(body,text='Add the chart difficulties, jacket and audio. Apply adds a Song and its audio bank to the project.',wraplength=760).pack(anchor='w',pady=8)
    grid=ttk.Frame(body);grid.pack(fill='x');grid.columnconfigure(1,weight=1)
    values={}
    fields=[('id','Song ID',template.findtext('name/id')),('title','Title',template.findtext('name/str')),('artist','Artist',template.findtext('artistName/str')),
            ('genre','Genre ID (POPS & ANIME = 0; VARIETY = 3)',template.findtext('genreNames/list/StringID/id','0')),
            ('stage','Stage ID (-1 = version default)',template.findtext('stageName/id','-1'))]
    for row,(key,label,initial) in enumerate(fields):
        values[key]=tk.StringVar(value=initial);ttk.Label(grid,text=label).grid(row=row,column=0,sticky='w',pady=3)
        ttk.Entry(grid,textvariable=values[key],state='normal').grid(row=row,column=1,sticky='ew',padx=8,pady=3)
    versions=version_options(getattr(app,'source_definitions',[])+app.docs,template)
    version=tk.StringVar()
    choices=['Keep current release tag']+[version_label(tag) for tag in versions]
    selected=next((i+1 for i,tag in enumerate(versions) if tag.findtext('id')==template.findtext('releaseTagName/id') and tag.findtext('str')==template.findtext('releaseTagName/str')),0)
    ttk.Label(grid,text='Game version').grid(row=len(fields),column=0,sticky='w',pady=3)
    picker=ttk.Combobox(grid,textvariable=version,values=choices,state='readonly')
    picker.grid(row=len(fields),column=1,sticky='ew',padx=8,pady=3);picker.current(selected)
    ttk.Label(body,text='Versions come from imported songs. Rescan A000/Axxx sources to populate this list. Stage -1 uses the game’s default; a special Stage ID takes precedence.',wraplength=760).pack(anchor='w',pady=4)
    conflict=tk.StringVar();ttk.Label(body,textvariable=conflict,foreground='#b25718',wraplength=760).pack(anchor='w',pady=5)
    def conflicts(*_):
        try:n=int(values['id'].get())
        except ValueError:conflict.set('Enter a numeric ID.');return
        hits=[f'{kind} {n}' for kind in ('MusicData','CueFileData') if (kind,n) in app.index]
        conflict.set('ID conflict in imported sources: '+', '.join(hits) if hits else 'No indexed song/audio-bank conflict. Avoid official IDs and likely future official song ranges; scans cannot predict future IDs.' if app.folders else 'Import A000/Axxx to check IDs. Do not reuse official song IDs or likely future official ranges.')
    values['id'].trace_add('write',conflicts);conflicts()
    charts={};jacket=[None];pair=[None];busy=[False];messages=queue.Queue()
    if current is not None:
        for f in current.findall('fumens/MusicFumenData'):
            name=f.findtext('file/path','');diff=int(f.findtext('type/id','-1'))
            if f.findtext('enable')=='true' and name in app.assets:
                charts[diff]=(app.assets[name],str(int(f.findtext('level','0'))+int(f.findtext('levelDecimal','0'))/100),f.findtext('notesDesigner',''))
        jacket[0]=app.assets.get(current.findtext('jaketFile/path'))
        if old_cue is not None:
            a=app.assets.get(old_cue.findtext('acbFile/path'));w=app.assets.get(old_cue.findtext('awbFile/path'))
            if a is not None and w is not None:pair[0]=(a,w)
    listing=tk.StringVar();status=tk.StringVar(value='Choose your files. No source files will be changed.')
    ttk.Label(body,textvariable=listing,justify='left',font=('Menlo',11)).pack(anchor='w',pady=8)
    buttons=[]
    def button(parent,label,fn):
        b=ttk.Button(parent,text=label,command=lambda:guard(fn));b.pack(side='left',padx=3,pady=4);buttons.append(b)
    def guard(fn):
        try:fn()
        except Exception as exc:messagebox.showerror('Song studio',str(exc),parent=win)
    def refresh():
        listing.set('\n'.join(f'{label}: '+('attached' if i in charts else 'not included') for i,label in enumerate(DIFFICULTIES))+f'\nJacket: {"attached" if jacket[0] else "missing"}\nAudio: '+('prepared ACB/AWB pair' if pair[0] else 'missing'))
    def load_charts():
        paths=filedialog.askopenfilenames(parent=win,title='Select UGC difficulties for one song',filetypes=[('Margrete text export','*.ugc')])
        pending={};meta=[]
        for path in paths:
            text=Path(path).read_text(encoding='utf-8-sig');chart=parse_ugc(text);diff=int(chart.value('DIFF','3'))
            slot=4 if diff==5 else diff
            if diff not in (0,1,2,3,5):raise ValueError("WORLD'S END is not supported yet.")
            if slot in pending:raise ValueError('Two files selected for the same difficulty.')
            pending[slot]=text;meta.append(chart)
        if meta:
            if len({c.value('SONGID') for c in meta})>1 or len({c.value('BGM') for c in meta})>1:raise ValueError('Select difficulties from one song at a time.')
            charts.update(pending);values['title'].set(meta[0].value('TITLE'));values['artist'].set(meta[0].value('ARTIST'))
            refresh()
    def clear_charts():charts.clear();refresh()
    def load_jacket():
        from PIL import Image
        from artwork import compose,encode_world_dds
        p=filedialog.askopenfilename(parent=win,filetypes=[('Artwork','*.png *.jpg *.jpeg *.webp *.dds')])
        if not p:return
        with Image.open(p) as image:jacket[0]=encode_world_dds(compose(image,(300,300),'Crop'))
        refresh()
    def load_pair():
        p=filedialog.askopenfilename(parent=win,title='Choose prepared ACB (matching AWB alongside it)',filetypes=[('ACB','*.acb')])
        if p:
            from cri_audio import require_hca_bank
            a=Path(p).read_bytes();w=Path(p).with_suffix('.awb').read_bytes();require_hca_bank(a,w);pair[0]=(a,w);refresh()
    row=ttk.Frame(body);row.pack(anchor='w');button(row,'Add UGC difficulties…',load_charts);button(row,'Clear difficulties',clear_charts);button(row,'Choose jacket…',load_jacket)
    row=ttk.Frame(body);row.pack(anchor='w');button(row,'Attach prepared ACB/AWB…',load_pair)
    def fix_pair():
        from audio_repair_editor import open_fixer
        def use(repaired):pair[0]=repaired;refresh();status.set('Repaired pair attached. Apply song to project, then Save project.')
        open_fixer(win,pair[0],use,'music'+values['id'].get())
    button(row,'ACB/AWB fixer…',fix_pair)
    ttk.Label(body,textvariable=status,wraplength=760).pack(anchor='w',pady=8)
    ttk.Label(body,text='Chart constants: some public servers require low values for custom charts to protect ratings and leaderboards. Check your server’s rules; imported difficulty constants may need lowering before export.',foreground='#b25718',wraplength=760).pack(anchor='w',pady=4)
    def apply():
        config={k:v.get() for k,v in values.items()};num=int(config['id']);stage=int(config['stage']);genre=int(config['genre'])
        release_tag=copy.deepcopy(versions[picker.current()-1]) if picker.current()>0 else None
        if not charts or jacket[0] is None:raise ValueError('Attach chart difficulties and a jacket first.')
        if pair[0] is None:raise ValueError('Attach your prepared ACB/AWB pair first. See Audio preparation guide for audio preparation instructions.')
        if any(r is not current and r is not old_cue and identity(r) in (('MusicData',num),('CueFileData',num)) for r in app.docs):raise ValueError('This song/audio-bank ID already exists in the project.')
        hits=[kind for kind in ('MusicData','CueFileData') if (kind,num) in app.index]
        if hits and not messagebox.askyesno('ID conflict',f'ID {num} already exists in imported sources ({", ".join(hits)}). Use it anyway?',parent=win):return
        busy[0]=True
        for b in buttons:b.configure(state='disabled')
        status.set('Converting charts and importing prepared audio…')
        def work():
            try:
                result=build_song(template,cue_template,num,config['title'],config['artist'],charts,jacket[0],pair[0],stage,genre,release_tag)
                messages.put(('ok',result))
            except Exception as exc:messages.put(('error',str(exc)))
        threading.Thread(target=work,daemon=True).start()
    def poll():
        try:kind,result=messages.get_nowait()
        except queue.Empty:
            if win.winfo_exists():win.after(100,poll)
            return
        busy[0]=False
        for b in buttons:b.configure(state='normal')
        if kind=='error':status.set(result);return
        root,cue,new_assets,reports=result
        allowed=set()
        for r in (current,old_cue):
            if r is not None:
                from core import asset_slots
                allowed.update(r.findtext(path) for path,_,_ in asset_slots(r)+binary_slots(r))
        for name,b in new_assets.items():
            if name in app.assets and name not in allowed and app.assets[name]!=b:
                status.set('Asset filename already belongs to another item: '+name);return
        app.docs[:]=[r for r in app.docs if r is not current and r is not old_cue]
        app.docs.extend((root,cue));app.assets.update(new_assets);app.current=len(app.docs)-2;app.dirty=True;app.refresh()
        warnings=[w for report in reports for w in report['warnings']]
        detail='\n\nConversion notes:\n'+'\n'.join(warnings[:8]) if warnings else ''
        messagebox.showinfo('Song applied','Song, converted charts, jacket and audio bank added to the project. Save project, then Export Axxx folder.'+detail,parent=win);win.destroy()
    def close():
        if busy[0]:status.set('Wait for the current conversion to finish.');return
        win.destroy()
    row=ttk.Frame(body);row.pack(side='bottom',fill='x');button(row,'Apply song to project',apply);ttk.Button(row,text='Close',command=close).pack(side='right')
    win.protocol('WM_DELETE_WINDOW',close);refresh();poll()
