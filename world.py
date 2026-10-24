"""Map/area/bonus list editor. Uses supplied examples; no inferred event enum."""
import copy
import tkinter as tk
from tkinter import ttk, messagebox
from core import KINDS, validate, set_reference, song_catalog, set_task_track
from map_preview import GridPreview

SPECS={
    'MapData':('infos','MapDataAreaInfo',[('pageIndex','Page'),('indexInPage','Position in page'),('requiredAchievementCount','Required achievements'),('isHard','Hard (true/false)')],
               [('mapAreaName','Map area','MapAreaData'),('ddsMapName','Map artwork','DDSMapData'),('rewardName','Completion reward','RewardData')]),
    'MapAreaData':('grids','MapAreaGridData',[('index','Grid position'),('displayType','Display type (numeric)'),('type','Grid type (numeric)')],
                   [('reward/rewardName','Grid reward','RewardData')]),
    'MapBonusData':('substances/list','MapBonusSubstanceData',[('type','Bonus type (numeric)'),('charaWorks/point','Category bonus points'),('chara/point','Character bonus points'),('musicGenre/point','Genre bonus points')],
                    [('charaWorks/charaWorksName','Category','CharaWorksData'),('chara/charaName','Character','CharaData')]),
}


def open_editor(app, template):
    original=app.root()
    if original.tag not in SPECS: raise ValueError('Select a Map, Map area, or Map bonus item. Event settings use the structured editor.')
    draft=copy.deepcopy(original)
    container_path,item_tag,fields,refs=SPECS[draft.tag]
    container=draft.find(container_path)
    if container is None: raise ValueError('Missing list: '+container_path)
    seed=template.find(container_path+'/'+item_tag)
    win=tk.Toplevel(app); win.title('ChuniVaina · '+KINDS[draft.tag][0]+' editor'); win.geometry(f'1100x{min(930,win.winfo_screenheight()-90)}'); win.minsize(900,650); win.transient(app); win.grab_set()
    win.columnconfigure(0,weight=1); win.rowconfigure(2,weight=1)
    ttk.Label(win,text=f'{KINDS[draft.tag][0]} · {draft.findtext("name/str")}',font=('Helvetica',18,'bold'),padding=12).grid(row=0,column=0,sticky='w')
    ttk.Label(win,text='Apply entry before changing list selection. Save to project commits the whole list; Cancel discards edits.',padding=(12,0,12,10)).grid(row=1,column=0,sticky='w')
    body=ttk.Frame(win,padding=12); body.grid(row=2,column=0,sticky='nsew')
    body.columnconfigure(0,weight=3); body.columnconfigure(1,weight=2)
    body.rowconfigure(0,weight=1); body.rowconfigure(1,weight=3)
    listing=tk.Listbox(body,width=29,height=6,exportselection=False); listing.grid(row=0,column=0,sticky='nsew',padx=(0,15))
    form=ttk.Frame(body); form.grid(row=0,column=1,rowspan=2,sticky='nsew')
    variables={}; refboxes={}; current=[None]; loading=[False]
    preview=None
    def preview_nodes():
        if draft.tag=='MapAreaData':
            nodes=list(copy.deepcopy(container))
            if current[0] is not None:
                node=nodes[current[0]]
                for path,var in variables.items():
                    node.find(path).text=var.get().strip()
                for path,(combo,_,choices) in refboxes.items():
                    if combo.current()>=0:
                        number,name=choices[combo.current()]
                        node.find(path+'/id').text=number; node.find(path+'/str').text=name
            return nodes,''
        if current[0] is None: return [],'Select a map entry to preview its area.'
        combo,_,choices=refboxes['mapAreaName']
        if combo.current()<0: return [],'Select a map area.'
        number,_=choices[combo.current()]
        area=next((r for r in [*app.docs,*app.source_definitions] if r.tag=='MapAreaData' and r.findtext('name/id')==number),None)
        if area is None: return [],'Area XML is unavailable. Import/rescan its Axxx folder or add the area to this project.'
        return area.findall('grids/MapAreaGridData'),f'Area: {area.findtext("name/str")} (ID {number}). Edit checkpoints in this map area’s editor.'
    def update_preview(reveal=False):
        if preview is None or loading[0]: return
        nodes,note=preview_nodes()
        preview.update_grid(nodes,current[0] if draft.tag=='MapAreaData' else None,note,reveal)
    task=[None];task_label=tk.StringVar(value='No task track')
    catalog=song_catalog(app.source_definitions+app.docs,app.index)
    for path,label in fields:
        ttk.Label(form,text=label).pack(anchor='w')
        var=tk.StringVar(); variables[path]=var
        ttk.Entry(form,textvariable=var).pack(fill='x',pady=(0,7))
    for path,label,kind in refs:
        ttk.Label(form,text=label+' (project / imported)').pack(anchor='w')
        combo=ttk.Combobox(form,state='readonly',width=48); combo.pack(fill='x',pady=(0,7)); refboxes[path]=(combo,kind,[])
    if draft.tag=='MapData':
        ttk.Label(form,text='Task track').pack(anchor='w')
        ttk.Label(form,textvariable=task_label,wraplength=440).pack(anchor='w',pady=(0,5))
        trackbar=ttk.Frame(form);trackbar.pack(fill='x')
        def chosen(song):
            task[0]=song;task_label.set(f'{song[1]} · {song[2]} (ID {song[0]})')
        def pick():
            if current[0] is None: raise ValueError('Select a map entry first.')
            from songs import choose_song
            choose_song(win,catalog,chosen)
        def clear(): task[0]=None;task_label.set('No task track')
        ttk.Button(trackbar,text='Search songs…',command=lambda:app.guard(pick)).pack(side='left')
        ttk.Button(trackbar,text='Clear task track',command=clear).pack(side='left',padx=5)
    def redraw(selection=0):
        listing.delete(0,'end')
        for i,node in enumerate(container):
            if draft.tag=='MapData': text=f'{i+1}. page {node.findtext("pageIndex")} / {node.findtext("indexInPage")} · area {node.findtext("mapAreaName/id")}'
            elif draft.tag=='MapAreaData': text=f'Grid {node.findtext("index")} · type {node.findtext("type")} · reward {node.findtext("reward/rewardName/id")}'
            else: text=f'{i+1}. type {node.findtext("type")} · category {node.findtext("charaWorks/charaWorksName/id")}'
            listing.insert('end',text)
        current[0]=None
        if len(container): listing.selection_set(min(selection,len(container)-1)); select()
        else:
            if draft.tag=='MapData': task[0]=None;task_label.set('No task track')
            for var in variables.values(): var.set('')
            for combo,_,_ in refboxes.values(): combo.set('')
            update_preview()
    def select(_=None):
        if not listing.curselection(): return
        loading[0]=True
        current[0]=listing.curselection()[0]; node=container[current[0]]
        for path,var in variables.items(): var.set(node.findtext(path,''))
        if draft.tag=='MapData':
            number=int(node.findtext('musicName/id','-1'))
            task[0]=next((s for s in catalog if s[0]==number),(number,node.findtext('musicName/str',''),'') if number>=0 else None)
            task_label.set(f'{task[0][1]} (ID {number})' if task[0] else 'No task track')
        for path,(combo,kind,_) in list(refboxes.items()):
            ref=node.find(path)
            if ref is None: combo.set('Missing reference'); continue
            existing=(ref.findtext('id','-1'),ref.findtext('str','Invalid'))
            choices=[existing,('-1','Invalid')]
            choices += [(r.findtext('name/id'),r.findtext('name/str')) for r in app.docs if r.tag==kind]
            choices += [(str(num),name) for (tag,num),entries in app.index.items() if tag==kind for name,_ in entries]
            choices=list(dict.fromkeys(choices))
            combo['values']=[f'{num} · {name}' for num,name in choices]; combo.current(0)
            refboxes[path]=(combo,kind,choices)
        loading[0]=False
        update_preview(reveal=True)
    listing.bind('<<ListboxSelect>>',select)
    def apply_entry():
        if current[0] is None: raise ValueError('Select an entry.')
        node=container[current[0]]
        candidate=copy.deepcopy(node)
        for path,var in variables.items():
            value=var.get().strip()
            if path=='isHard':
                if value not in ('true','false'): raise ValueError('Hard must be true or false.')
            else:
                if int(value)<0: raise ValueError('Numeric fields must be nonnegative.')
            candidate.find(path).text=value
        for path,(combo,kind,choices) in refboxes.items():
            if combo.current()<0: continue
            number,name=choices[combo.current()]; ref=candidate.find(path)
            ref.find('id').text=number; ref.find('str').text=name
        if draft.tag=='MapData': set_task_track(candidate,task[0])
        idx=current[0]; container.remove(node); container.insert(idx,candidate); redraw(idx)
    def add():
        if seed is None: raise ValueError('No template entry available.')
        node=copy.deepcopy(seed)
        if draft.tag=='MapData':
            page=max([int(e.findtext('pageIndex','0')) for e in container],default=0)
            positions=[int(e.findtext('indexInPage','0')) for e in container if int(e.findtext('pageIndex','0'))==page]
            node.find('pageIndex').text=str(page); node.find('indexInPage').text=str(max(positions,default=-1)+1)
            for path,_,_ in refs:
                node.find(path+'/id').text='-1'; node.find(path+'/str').text='Invalid'
            node.find('musicName/id').text='-1'; node.find('musicName/str').text='Invalid'
        elif draft.tag=='MapAreaData':
            # A new entry is a reward checkpoint, not an extra entrance/exit.
            node=copy.deepcopy(next((e for e in template.findall(container_path+'/'+item_tag) if e.findtext('type')=='3'),seed))
            indices=[int(e.findtext('index','0')) for e in container]
            position=max(indices,default=0)+1
            node.find('index').text=str(position)
            node.find('reward/rewardName/id').text='-1'; node.find('reward/rewardName/str').text='Invalid'
        container.append(node); redraw(len(container)-1)
    def remove():
        if current[0] is not None:
            idx=current[0]; container.remove(container[idx]); redraw(max(0,idx-1))
    def save():
        # Form values are explicitly committed, then whole-list invariants checked.
        if current[0] is not None: apply_entry()
        if draft.tag=='MapAreaData': container[:]=sorted(container,key=lambda el:int(el.findtext('index','0')))
        validate(draft)
        app.docs[app.current]=draft; app.dirty=True; app.refresh(); win.destroy()
    def preview_select(row):
        if draft.tag=='MapData': return
        def commit_and_select():
            apply_entry()
            listing.selection_clear(0,'end'); listing.selection_set(row); listing.see(row); select()
        app.guard(commit_and_select)
    if draft.tag in ('MapData','MapAreaData'):
        preview=GridPreview(body,preview_select)
        preview.grid(row=1,column=0,sticky='nsew',padx=(0,15),pady=(8,0))
        for var in variables.values(): var.trace_add('write',lambda *_: update_preview())
        for combo,_,_ in refboxes.values(): combo.bind('<<ComboboxSelected>>',lambda _:update_preview())
    buttons=ttk.Frame(win,padding=12); buttons.grid(row=4,column=0,sticky='ew')
    for text,fn in [('Add entry',add),('Remove entry',remove),('Apply entry',apply_entry),('Save to project',save)]:
        ttk.Button(buttons,text=text,command=lambda f=fn:app.guard(f)).pack(side='left',padx=4)
    ttk.Button(buttons,text='Cancel',command=win.destroy).pack(side='right')
    ttk.Label(win,text='Other fields (gauge, hidden settings, area boost, release tags, bonus rules) remain available in the structured editor.',wraplength=810,padding=12).grid(row=5,column=0,sticky='w')
    redraw()
