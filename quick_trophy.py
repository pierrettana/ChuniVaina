"""Song AJ trophy shortcuts using separate EXPERT/MASTER presets."""
import copy
from core import set_identity,validate,identity,song_catalog

def build_trophies(templates,song,entries):
    number,title,_=song
    number=int(number)
    if number<0 or not title.strip():raise ValueError('Choose a valid song.')
    if not entries:raise ValueError('Choose EXPERT, MASTER, or both.')
    results=[];seen_ids=set();seen_diffs=set()
    for difficulty,trophy_id,text in entries:
        if difficulty not in (2,3):raise ValueError('Quick trophy supports EXPERT and MASTER.')
        trophy_id=int(trophy_id)
        if trophy_id<0:raise ValueError('Trophy IDs must be nonnegative.')
        if trophy_id in seen_ids:raise ValueError('Each trophy needs a different ID.')
        if difficulty in seen_diffs:raise ValueError('Each difficulty can be selected only once.')
        if not text.strip():raise ValueError('Enter the trophy text.')
        root=copy.deepcopy(templates[difficulty]);set_identity(root,trophy_id,text)
        label='EXPERT' if difficulty==2 else 'MASTER'
        root.find('explainText').text=f'{title}/{label}/ALL JUSTICE達成'
        root.find('defaultHave').text='false';root.find('disableFlag').text='false'
        conditions=root.findall('normCondition/conditions/ConditionSubData')
        if [c.findtext('type') for c in conditions]!=['1','3']:raise ValueError('Invalid AJ trophy template.')
        ref=conditions[0].find('playMusicData/musicNames/list/StringID')
        ref.find('id').text=str(number);ref.find('str').text=title
        dif=conditions[0].find('playMusicData/musicDif')
        dif.find('id').text=str(difficulty);dif.find('str').text=label.title();dif.find('data').text=label
        if conditions[1].findtext('playMusicResultData/allJustice')!='true':raise ValueError('Template is missing the All Justice condition.')
        validate(root);results.append(root);seen_ids.add(trophy_id);seen_diffs.add(difficulty)
    return results

def open_editor(app,base):
    import tkinter as tk
    from tkinter import ttk,messagebox
    from core import parse
    from songs import choose_song
    win=tk.Toplevel(app);win.title('ChuniVaina · Quick trophy');win.geometry('760x470');win.transient(app);win.grab_set()
    body=ttk.Frame(win,padding=16);body.pack(fill='both',expand=True)
    ttk.Label(body,text='Quick trophy · ALL JUSTICE',font=('Helvetica',20,'bold')).pack(anchor='w')
    ttk.Label(body,text='Create an EXPERT trophy, a MASTER trophy, or both. Each unlocks separately when that difficulty gets ALL JUSTICE. These presets do not require a map, quest or separate Reward.',wraplength=710).pack(anchor='w',pady=10)
    selected=[None];song_text=tk.StringVar(value='Choose a song from the project or imported sources.')
    ttk.Label(body,textvariable=song_text,wraplength=710).pack(anchor='w')
    rows={};used={n for kind,n in app.index if kind=='TrophyData'}|{identity(r)[1] for r in app.docs if r.tag=='TrophyData'}
    next_id=9000
    while next_id in used:next_id+=1
    def pick():
        def picked(song):
            selected[0]=song;song_text.set(f'{song[1]} · ID {song[0]}')
            for row in rows.values():
                if not row['text'].get().strip():row['text'].set(song[1])
        choose_song(win,song_catalog(getattr(app,'source_definitions',[])+app.docs,app.index),picked)
    ttk.Button(body,text='Choose song…',command=pick).pack(anchor='w',pady=8)
    grid=ttk.Frame(body);grid.pack(fill='x',pady=8);grid.columnconfigure(2,weight=1)
    for col,label in enumerate(('Create','Trophy ID','Trophy text')):ttk.Label(grid,text=label).grid(row=0,column=col,sticky='w',padx=4)
    for i,(diff,label) in enumerate(((2,'EXPERT'),(3,'MASTER')),1):
        while next_id in used:next_id+=1
        row={'enabled':tk.BooleanVar(value=True),'id':tk.StringVar(value=str(next_id)),'text':tk.StringVar()};rows[diff]=row;used.add(next_id);next_id+=1
        ttk.Checkbutton(grid,text=label,variable=row['enabled']).grid(row=i,column=0,sticky='w',padx=4,pady=6)
        ttk.Entry(grid,textvariable=row['id'],width=12).grid(row=i,column=1,sticky='ew',padx=4)
        ttk.Entry(grid,textvariable=row['text']).grid(row=i,column=2,sticky='ew',padx=4)
    ttk.Label(body,text='IDs are editable; suggestions skip current project/imported trophy IDs. Import A000/Axxx sources to check your installation. The presets retain a release reference; review netOpenName for your setup.',wraplength=710).pack(anchor='w',pady=8)
    def create():
        try:
            if selected[0] is None:raise ValueError('Choose a song first.')
            entries=[(diff,int(r['id'].get()),r['text'].get()) for diff,r in rows.items() if r['enabled'].get()]
            templates={diff:parse((base/'templates'/file).read_text()) for diff,file in ((2,'Trophy-AJ-expert.xml'),(3,'Trophy-AJ-master.xml'))}
            results=build_trophies(templates,selected[0],entries)
            keys={identity(r) for r in results};existing={identity(r) for r in app.docs}
            if keys&existing:raise ValueError('A trophy with one of these IDs already exists in the project. Choose another ID.')
            conflicts=sorted(n for kind,n in keys if (kind,n) in app.index)
            if conflicts and not messagebox.askyesno('Trophy ID conflict','Already present in imported sources: '+', '.join(map(str,conflicts))+'.\nUse these IDs anyway?',parent=win):return
            first=len(app.docs);app.docs.extend(results);app.current=first;app.dirty=True;app.refresh();win.destroy()
        except Exception as exc:messagebox.showerror('Quick trophy',str(exc),parent=win)
    controls=ttk.Frame(body);controls.pack(side='bottom',fill='x')
    ttk.Button(controls,text='Create trophies',command=create).pack(side='right')
    ttk.Button(controls,text='Cancel',command=win.destroy).pack(side='left')
    if app.current is not None and app.root().tag=='MusicData':
        root=app.root();selected[0]=(identity(root)[1],root.findtext('name/str'),root.findtext('artistName/str',''))
        song_text.set(f'{selected[0][1]} · ID {selected[0][0]}')
        for row in rows.values():row['text'].set(selected[0][1])
