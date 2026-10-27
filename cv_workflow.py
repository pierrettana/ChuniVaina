"""Task-oriented UI and optional export metadata; no source files are modified."""
import tkinter as tk
from tkinter import ttk, messagebox
from core import KINDS, parse, set_identity, identity, asset_slots, character_unlock_warnings

ID_GUIDANCE = ('Do not reuse official IDs. Import A000 and all installed options before choosing IDs. '
               'Avoid ranges likely to be used by official updates, especially for custom songs; '
               'leave room beyond current official allocations. An unused ID is not reserved: '
               'the detector only knows scanned sources and cannot predict future official IDs. '
               'Recheck after updates and update every reference if you renumber content.')
DATA_CONF_GUIDANCE = ('Custom content can load with or without data.conf; it is not required for the custom itself. '
                      'It supplies option/version information so the option appears in the test menu. '
                      'The files, IDs, references and installation must still be compatible. '
                      'Version metadata can conflict with the installed game or later updates, even when the content files remain compatible. '
                      'Leave this unchecked unless you understand your installation’s version requirements; review or omit it when migrating content. '
                      'It does not convert content or make it compatible with another version.')


def export_settings(app):
    win=tk.Toplevel(app); win.title('Axxx export settings'); win.transient(app); win.grab_set()
    body=ttk.Frame(win,padding=18); body.pack(fill='both',expand=True)
    enabled=tk.BooleanVar(value=False)
    ttk.Label(body,text='Optional test-menu listing',font=('Helvetica',15,'bold')).pack(anchor='w')
    ttk.Label(body,text=DATA_CONF_GUIDANCE,wraplength=580,justify='left').pack(pady=12)
    row=ttk.Frame(body); row.pack(fill='x',pady=8)
    values=[tk.StringVar(value=v) for v in ('2','50','1')]; entries=[]
    for label,value in zip(('Major','Minor','Release'),values):
        ttk.Label(row,text=label).pack(side='left',padx=4)
        entry=ttk.Entry(row,textvariable=value,width=7,state='disabled');entry.pack(side='left');entries.append(entry)
    def toggle():
        for entry in entries:entry.configure(state='normal' if enabled.get() else 'disabled')
    ttk.Checkbutton(body,text='Include data.conf (optional; may cause version compatibility conflicts)',variable=enabled,command=toggle).pack(anchor='w',before=row)
    ttk.Label(body,text='The sample version fields are not detected from your installation. Set them explicitly if enabled.',wraplength=580).pack(anchor='w')
    result=[]
    def accept():
        try:
            version=tuple(int(v.get()) for v in values) if enabled.get() else None
            if version is not None and any(v<0 for v in version):raise ValueError()
        except ValueError:
            messagebox.showerror('Invalid version','Use three nonnegative integers.',parent=win);return
        result.append(version);win.destroy()
    buttons=ttk.Frame(body);buttons.pack(fill='x',pady=(18,0))
    ttk.Button(buttons,text='Cancel',command=win.destroy).pack(side='left')
    ttk.Button(buttons,text='Continue export',command=accept).pack(side='right')
    app.wait_window(win)
    return result if result else None


def build_tools(app, parent):
    bar=ttk.Frame(parent);bar.pack(fill='x',pady=6)
    ttk.Button(bar,text='New song…',command=lambda:app.guard(lambda:app.song_studio(True))).pack(side='left')
    ttk.Button(bar,text='Quick trophy…',command=lambda:app.guard(app.quick_trophy)).pack(side='left',padx=4)
    ttk.Button(bar,text='ACB/AWB fixer…',command=lambda:app.guard(app.audio_fixer)).pack(side='left')
    ttk.Button(bar,text='Check references',command=lambda:app.guard(app.check_references)).pack(side='left',padx=4)
    app.project_status=tk.StringVar(value='Project saved / no changes. Studio drafts must be applied first.')
    ttk.Label(parent,textvariable=app.project_status,wraplength=680).pack(anchor='w')


def build_overview(app):
    ttk.Label(app.overview,text='Select an item to see its settings and next steps.',wraplength=650).pack(anchor='w')


def update_overview(app):
    for child in app.overview.winfo_children():child.destroy()
    root=app.root(); body=app.overview
    ttk.Label(body,text=KINDS[root.tag][0],font=('Helvetica',16,'bold')).pack(anchor='w')
    ttk.Label(body,text='Apply buttons update the project draft. Save project keeps those changes on disk.',wraplength=650).pack(anchor='w',pady=6)
    actions=ttk.Frame(body);actions.pack(fill='x',pady=4)
    def action(label,fn):
        ttk.Button(actions,text=label,command=lambda:app.guard(fn)).pack(anchor='w',pady=2)
    if root.tag=='CharaData':
        owned=tk.BooleanVar(value=root.findtext('defaultHave')=='true')
        ttk.Checkbutton(body,text='Available from the start',variable=owned).pack(anchor='w')
        categories=[r for r in app.docs+app.source_definitions if r.tag=='CharaWorksData']
        categories=list({r.findtext('name/id'):r for r in categories}.values())
        options=[f'{r.findtext("name/id")} · {r.findtext("name/str")}' for r in categories]
        ttk.Label(body,text='Character category (leave unchanged to keep current reference)').pack(anchor='w')
        category=ttk.Combobox(body,values=options,state='readonly',width=55);category.pack(anchor='w',pady=4)
        match=next((i for i,r in enumerate(categories) if r.findtext('name/id')==root.findtext('works/id')),None)
        if match is not None:category.current(match)
        def apply():
            root.find('defaultHave').text='true' if owned.get() else 'false'
            if category.current()>=0:
                target=categories[category.current()]
                for field in ('id','str'):root.find('works/'+field).text=target.findtext('name/'+field)
            app.dirty=True;app.show()
        ttk.Button(body,text='Apply character settings',command=lambda:app.guard(apply)).pack(anchor='w',pady=6)
        action('Choose character artwork…',app.link_artwork)
        aid=root.findtext('defaultImages/id')
        art=next((r for r in app.docs if r.tag=='DDSImageData' and r.findtext('name/id')==aid),None)
        if art is not None:
            def edit_art():
                app.current=app.docs.index(art);app.refresh();app.artwork_studio()
            action('Edit linked artwork…',edit_art)
        notes=character_unlock_warnings(app.docs,app.source_definitions)
        own_notes=[n for n in notes if root.findtext('name/str','') in n]
        text=('Next: add or review artwork. Available from the start is enabled.' if owned.get() else
              'Locked character: create a character-granting Reward and deliver it through a map checkpoint, map completion or quest milestone.')
        if own_notes:text+=' No supported unlock path is currently configured.'
    else:
        text='Use Advanced fields for other settings and references. Select a field there before linking its reference.'
        if asset_slots(root):action('Edit artwork…',app.artwork_studio)
        if root.tag=='DDSImageData':
            linked=next((r for r in app.docs if r.tag=='CharaData' and r.findtext('defaultImages/id')==root.findtext('name/id')),None)
            if linked is not None:
                def return_character():
                    app.current=app.docs.index(linked);app.refresh()
                action('Return to linked character',return_character)
        if root.tag=='StageData':action('Edit stage textures…',app.stage_studio)
        if root.tag in ('MusicData','CueFileData'):action('Edit song…',app.song_studio)
        if root.tag in ('MapData','MapAreaData','MapBonusData'):action('Edit map / area / bonus…',app.world_editor)
        if root.tag=='EventData' and root.findtext('substances/type') in ('2','8','11'):action('Choose event targets…',app.link_event_target)
        if root.tag in ('RewardData','QuestData'):
            action('Link reward (select an entry in Advanced fields first)…',app.link_reward)
            text='Select a reward entry or quest milestone in Advanced fields, then choose Link reward. Deliver rewards through a map or quest; creating a Reward alone does not award it.'
    ttk.Label(body,text=text,wraplength=650,justify='left').pack(anchor='w',pady=10)
    ttk.Label(body,text=ID_GUIDANCE,wraplength=650,justify='left',foreground='#80521c').pack(anchor='w',pady=6)


def make_character(base, number, name, category, available, artwork_id):
    """Prepare both definitions before adding anything to the project."""
    char=parse((base/'templates/Chara.xml').read_text(encoding='utf-8-sig'))
    art=parse((base/'templates/DDSImage.xml').read_text(encoding='utf-8-sig'))
    if not name.strip():raise ValueError('Enter a character name.')
    set_identity(char,number,name.strip());set_identity(art,artwork_id,name.strip()+' artwork')
    for field,value in zip(('id','str'),category):char.find('works/'+field).text=str(value)
    for field in ('id','str'):char.find('defaultImages/'+field).text=art.findtext('name/'+field)
    char.find('defaultHave').text='true' if available else 'false'
    char.find('sortName').text=name.strip()
    for slot in range(3):art.find(f'ddsFile{slot}/path').text=''
    return char,art


def character_wizard(app,base):
    win=tk.Toplevel(app);win.title('Create a character · guided setup');win.transient(app);win.grab_set()
    body=ttk.Frame(win,padding=18);body.pack(fill='both',expand=True)
    page=ttk.Frame(body);page.pack(fill='both',expand=True)
    step=[0]; num=tk.StringVar();name=tk.StringVar();aid=tk.StringVar();owned=tk.BooleanVar(value=True)
    categories=list({r.findtext('name/id'):r for r in app.docs+app.source_definitions if r.tag=='CharaWorksData'}.values())
    selected=tk.StringVar()
    def draw():
        for child in page.winfo_children():child.destroy()
        ttk.Label(page,text=f'Step {step[0]+1} of 3',font=('Helvetica',16,'bold')).pack(anchor='w',pady=8)
        if step[0]==0:
            for label,var in [('Character ID',num),('Character name',name),('Artwork definition ID (separate ID type)',aid)]:
                ttk.Label(page,text=label).pack(anchor='w');ttk.Entry(page,textvariable=var,width=50).pack(fill='x',pady=4)
            ttk.Label(page,text=ID_GUIDANCE,wraplength=560).pack(pady=10)
        elif step[0]==1:
            ttk.Label(page,text='Choose a category from this project or scanned sources.').pack(anchor='w')
            ttk.Combobox(page,textvariable=selected,state='readonly',width=55,values=[f'{r.findtext("name/id")} · {r.findtext("name/str")}' for r in categories]).pack(pady=8)
            ttk.Label(page,text='If none are listed, cancel and create a Category or import sources first.',wraplength=560).pack(anchor='w')
            ttk.Checkbutton(page,text='Available from the start',variable=owned).pack(anchor='w',pady=12)
            ttk.Label(page,text='If unchecked, configure a character-granting Reward delivered by a map or quest after creation.',wraplength=560).pack()
        else:
            ttk.Label(page,text=f'{name.get()} · character {num.get()} · artwork {aid.get()}\nCategory: {selected.get()}\n'+('Available from the start' if owned.get() else 'Locked — unlock setup required'),wraplength=560).pack(anchor='w',pady=10)
            ttk.Label(page,text='Create adds a character and linked artwork definition. Next, use Edit linked artwork to fill all three image slots. Review retained release references in Advanced fields, then Save project. No image is generated by this wizard.',wraplength=560).pack()
        back.configure(state='normal' if step[0] else 'disabled');next_button.configure(text='Create character' if step[0]==2 else 'Next')
    def advance():
        if step[0]==0:
            # Validate both identities and block collisions before moving on.
            pair=make_character(base,num.get(),name.get(),('-1','Invalid'),owned.get(),aid.get())
            for root in pair:
                key=identity(root)
                if key in app.index or any(identity(r)==key for r in app.docs):raise ValueError('This ID is already in use. Choose a different ID.')
        if step[0]==1 and not selected.get():raise ValueError('Choose a category or cancel to create one first.')
        if step[0]<2:step[0]+=1;draw();return
        cat=next(r for r in categories if f'{r.findtext("name/id")} · {r.findtext("name/str")}'==selected.get())
        pair=make_character(base,num.get(),name.get(),(cat.findtext('name/id'),cat.findtext('name/str')),owned.get(),aid.get())
        for root in pair:
            if identity(root) in app.index or any(identity(r)==identity(root) for r in app.docs):raise ValueError('An ID is now in use. Go back and choose another.')
        app.docs.extend(pair);app.current=len(app.docs)-2;app.dirty=True;app.refresh();win.destroy()
    def previous():step[0]-=1;draw()
    buttons=ttk.Frame(body);buttons.pack(fill='x',pady=16)
    ttk.Button(buttons,text='Cancel',command=win.destroy).pack(side='left')
    back=ttk.Button(buttons,text='Back',command=previous);back.pack(side='left',padx=8)
    next_button=ttk.Button(buttons,text='Next',command=lambda:app.guard(advance));next_button.pack(side='right')
    draw()
