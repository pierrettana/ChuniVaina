import base64
import copy
import json
import queue
import sys
import threading
from helptext import describe_field, open_help
from branding import VERSION, badge, picture, about, open_tutorial, welcome_if_needed
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from core import KINDS, parse, serialize, identity, set_identity, validate, scan, export_path, discover_sources, export_option, dds_info, artwork_files, configure_reward, add_quest_reward, asset_slots, binary_slots, validate_asset, REFERENCE_TYPES, LIST_REFERENCE_TYPES, reference_report, set_reference, configure_activation, character_unlock_warnings, kind_label

BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f'ChuniVaina {VERSION} · Custom content studio')
        self._app_icon = picture(self, 'icon.png', (256, 256))
        self.iconphoto(True, self._app_icon)
        self.geometry('1180x840')
        self.minsize(1000, 800)
        self.docs, self.folders, self.index = [], [], {}
        self.assets = {}
        self.nameplate_layouts = {}
        self.source_definitions = []
        self.current = None
        self.dirty = False
        self.scanning = False
        self.messages = queue.Queue()
        self.bulk_messages = queue.Queue()
        self.protocol('WM_DELETE_WINDOW', self.close)
        style = ttk.Style(self)
        style.configure('Title.TLabel', font=('Helvetica', 24, 'bold'))
        header = ttk.Frame(self, padding=18); header.pack(fill='x')
        badge(header, (42, 42)).pack(side='left', padx=(0, 10))
        ttk.Label(header, text='ChuniVaina', style='Title.TLabel').pack(side='left')
        ttk.Label(header, text='  /  CUSTOM CONTENT STUDIO').pack(side='left')
        ttk.Button(header,text='Help / F1',command=lambda:self.guard(self.help_window)).pack(side='right')
        ttk.Button(header,text='About',command=lambda:self.guard(lambda:about(self))).pack(side='right',padx=4)
        ttk.Button(header,text='Quick tour',command=lambda:self.guard(lambda:open_tutorial(self))).pack(side='right',padx=4)
        self.bind('<F1>',lambda event:self.guard(self.help_window))
        bar = ttk.Frame(self, padding=(18, 0, 18, 12)); bar.pack(fill='x')
        for label, fn in [('New', self.new), ('Import XML', self.import_xml), ('Open project', self.open_project), ('Save project', self.save_project), ('Export XML', self.export), ('Export Axxx folder…', self.export_axxx)]:
            ttk.Button(bar, text=label, command=lambda f=fn: self.guard(f)).pack(side='left', padx=3)
        ttk.Label(self, text='Changes in the XML tab require Apply XML edits. Artwork studio supports PNG conversion and live previews.', padding=12).pack(side='bottom',fill='x')
        pane = ttk.Panedwindow(self, orient='horizontal'); pane.pack(fill='both', expand=True, padx=18)
        left = ttk.Frame(pane, padding=8); pane.add(left, weight=1)
        ttk.Label(left, text='PROJECT CONTENT', font=('Helvetica', 12, 'bold')).pack(anchor='w')
        self.items = tk.Listbox(left, width=30, exportselection=False); self.items.pack(fill='both', expand=True, pady=8)
        self.items.bind('<<ListboxSelect>>', self.select_doc)
        self.empty_welcome = ttk.Frame(self.items, padding=10)
        badge(self.empty_welcome, (72, 80), full=True).pack()
        ttk.Label(self.empty_welcome, text='Your next idea starts here.\nChoose New or Import XML.', justify='center', wraplength=200).pack(pady=8)
        self.empty_welcome.place(relx=.5,rely=.5,anchor='center')
        ttk.Button(left, text='Remove selected item', command=lambda:self.guard(self.remove_doc)).pack(fill='x')
        ttk.Button(left, text='Project files…', command=lambda:self.guard(self.project_files)).pack(fill='x',pady=4)
        ttk.Separator(left).pack(fill='x', pady=12)
        ttk.Label(left, text='ID CONFLICT SOURCES', font=('Helvetica', 12, 'bold')).pack(anchor='w')
        self.sources = tk.Listbox(left, height=5, width=30, exportselection=False); self.sources.pack(fill='x', pady=8)
        for text, fn in [('Import Axxx folder', self.add_source), ('Bulk import Axxx folders…', self.bulk_sources), ('Remove source', self.remove_source), ('Rescan sources', self.rescan), ('View index / scan errors', self.view_index)]:
            ttk.Button(left, text=text, command=lambda f=fn: self.guard(f)).pack(fill='x', pady=2)
        right = ttk.Frame(pane, padding=8); pane.add(right, weight=4)
        ident = ttk.Frame(right); ident.pack(fill='x')
        self.idvar, self.namevar = tk.StringVar(), tk.StringVar()
        ttk.Label(ident, text='ID').pack(side='left')
        ttk.Entry(ident, textvariable=self.idvar, width=10).pack(side='left', padx=5)
        ttk.Label(ident, text='Name').pack(side='left')
        ttk.Entry(ident, textvariable=self.namevar).pack(side='left', fill='x', expand=True, padx=5)
        ttk.Button(ident, text='Apply identity', command=lambda: self.guard(self.apply_identity)).pack(side='left')
        from cv_workflow import build_tools, build_overview
        build_tools(self, right)
        self.artstatus=tk.StringVar()
        ttk.Label(right, textvariable=self.artstatus, wraplength=680).pack(anchor='w')
        self.warning = tk.StringVar(value='Create an item or import an XML reference to begin.')
        ttk.Label(right, textvariable=self.warning, wraplength=700, foreground='#b25718').pack(fill='x', pady=10)
        book = ttk.Notebook(right); book.pack(fill='both', expand=True)
        self.overview = ttk.Frame(book, padding=12); book.add(self.overview, text='Item settings & next steps')
        build_overview(self)
        fields = ttk.Frame(book, padding=8); book.add(fields, text='Advanced fields')
        self.tree = ttk.Treeview(fields, columns=('value',), selectmode='browse'); self.tree.heading('#0', text='Field / reference'); self.tree.heading('value', text='Value')
        self.tree.column('#0', width=260); self.tree.column('value', width=300)
        scroll = ttk.Scrollbar(fields, command=self.tree.yview); self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y'); self.tree.pack(fill='both', expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.select_field)
        self.value = tk.StringVar()
        edit = ttk.Frame(fields); edit.pack(fill='x', pady=8)
        ttk.Entry(edit, textvariable=self.value).pack(side='left', fill='x', expand=True)
        ttk.Button(edit, text='Set value', command=lambda: self.guard(self.set_value)).pack(side='left', padx=4)
        self.field_help=tk.StringVar(value='Select a field for its description. Press F1 for the full guide.')
        ttk.Label(fields,textvariable=self.field_help,wraplength=680,foreground='#555555').pack(fill='x',pady=(0,8))
        for text, fn in [('Duplicate node', self.duplicate), ('Remove node', self.remove_node), ('Add XML child…', self.add_child), ('Link reference…', self.link_reference)]:
            ttk.Button(fields, text=text, command=lambda f=fn: self.guard(f)).pack(side='left', padx=3)
        raw = ttk.Frame(book, padding=8); book.add(raw, text='XML preview / advanced')
        self.raw = tk.Text(raw, undo=True, wrap='none', font=('Menlo', 11)); self.raw.pack(fill='both', expand=True)
        ttk.Button(raw, text='Apply XML edits', command=lambda: self.guard(self.apply_raw)).pack(anchor='e', pady=8)
        self.after(100, self.poll)
        self.after(350, lambda: self.guard(lambda:welcome_if_needed(self)))

    @property
    def dirty(self):
        return getattr(self, '_dirty', False)

    @dirty.setter
    def dirty(self, value):
        self._dirty = value
        self.title(f'ChuniVaina {VERSION} · ' + ('Unsaved project changes' if value else 'Project saved / no changes'))
        if hasattr(self, 'project_status'):
            self.project_status.set('Unsaved project changes — Save project to keep them.' if value else 'Project saved / no changes. Studio drafts must be applied first.')

    def help_window(self):
        open_help(self)

    def song_studio(self,new=False):
        from song_editor import open_editor
        open_editor(self,BASE,new)

    def quick_trophy(self):
        from quick_trophy import open_editor
        open_editor(self,BASE)

    def audio_fixer(self):
        from audio_repair_editor import open_fixer
        cue=None
        if self.current is not None:
            root=self.root()
            if root.tag=='CueFileData':cue=root
            elif root.tag=='MusicData':
                cue=next((r for r in self.docs if r.tag=='CueFileData' and r.findtext('name/id')==root.findtext('cueFileName/id')),None)
        pair=None;stem='music';apply=None
        if cue is not None:
            a=cue.findtext('acbFile/path','');w=cue.findtext('awbFile/path','')
            if a in self.assets and w in self.assets:
                pair=(self.assets[a],self.assets[w]);stem=Path(a).stem
                def apply(repaired):
                    from audio_repair import apply_project_pair
                    apply_project_pair(self,cue,repaired)
                    if self.current is not None:self.show()
        open_fixer(self,pair,apply,stem)

    def warn_song_constants(self,documents):
        if any(root.tag=='MusicData' for root in documents):
            from song_model import CHART_CONSTANT_WARNING
            messagebox.showwarning('Custom charts: server rules and chart constants',
                CHART_CONSTANT_WARNING+'\n\nReview Song → fumens → each enabled MusicFumenData → level and levelDecimal before exporting.',parent=self)

    def guard(self, fn):
        try: fn()
        except Exception as exc: messagebox.showerror('ChuniVaina', str(exc))

    def root(self):
        if self.current is None: raise ValueError('Select a project item first.')
        return self.docs[self.current]

    def refresh(self):
        self.items.delete(0, 'end')
        if self.docs:self.empty_welcome.place_forget()
        else:
            self.empty_welcome.place(relx=.5,rely=.5,anchor='center')
            self.idvar.set(''); self.namevar.set(''); self.artstatus.set('')
            self.warning.set('Create an item or import XML to begin.')
            for child in self.overview.winfo_children(): child.destroy()
            from cv_workflow import build_overview
            build_overview(self)
        for r in self.docs: self.items.insert('end', f'{KINDS[r.tag][0]} · {r.findtext("name/id")} · {r.findtext("name/str")}')
        if self.current is not None:
            self.items.selection_set(self.current)
            self.show()

    def show(self):
        root = self.root()
        self.idvar.set(root.findtext('name/id')); self.namevar.set(root.findtext('name/str'))
        self.tree.delete(*self.tree.get_children()); self.nodes = {}
        def visit(el, parent=''):
            key = self.tree.insert(parent, 'end', text=el.tag, values=(el.text.strip() if el.text else '',), open=parent=='')
            self.nodes[key] = el
            for child in el: visit(child, key)
        visit(root)
        self.raw.delete('1.0', 'end'); self.raw.insert('1.0', serialize(root))
        if asset_slots(root):
            details=[]
            for slot,(path,required,_) in enumerate(asset_slots(root)):
                filename=root.findtext(path,'')
                if filename in self.assets:
                    w,h,m=dds_info(self.assets[filename]); details.append(f'{slot}: {w}×{h}')
                else: details.append(f'{slot}: missing' if filename or required else f'{slot}: optional / empty')
            for path,required,_ in binary_slots(root):
                filename=root.findtext(path,'')
                details.append(path.split('/')[0]+': '+('attached' if filename in self.assets else 'missing' if filename or required else 'optional / empty'))
            self.artstatus.set(' | '.join(details))
        else: self.artstatus.set('')
        self.field_help.set(describe_field(root,root))
        self.check_conflict()
        from cv_workflow import update_overview
        update_overview(self)

    def check_conflict(self):
        if self.current is None: return
        try: key = identity(self.root())
        except ValueError:
            self.warning.set('Invalid ID. Use Apply identity to fix it.'); return
        hits = self.index.get(key, [])
        local = [i for i, r in enumerate(self.docs) if i != self.current and identity(r) == key]
        if hits or local:
            self.warning.set(f'⚠ ID conflict: {len(hits)} imported definition(s), {len(local)} other project item(s). ' + '; '.join(p for _, p in hits[:2]))
        else: self.warning.set('No indexed conflict. Avoid official IDs and ranges likely to be used in future updates, especially song IDs. Future IDs cannot be predicted.' if self.folders else 'Import A000 and options to check IDs. Do not use official IDs or likely future official ranges, especially for songs.')

    def select_doc(self, _=None):
        if self.items.curselection(): self.current = self.items.curselection()[0]; self.show()

    def new(self):
        win = tk.Toplevel(self); win.title('New content'); win.transient(self)
        ttk.Label(win, text='Choose a content template:', padding=12).pack()
        options=[(spec[0],spec[2]) for kind,spec in KINDS.items() if kind not in ('MusicData','CueFileData')]+[('Map-opening event (type 2)','Event-map.xml'),('Quest-opening event (type 8)','Event-quest.xml'),('Rights-information event (type 11)','Event-rights.xml')]
        from cv_workflow import character_wizard
        ttk.Button(win,text='Guided character creator…',command=lambda:(win.destroy(),self.guard(lambda:character_wizard(self,BASE)))).pack(fill='x',padx=12,pady=4)
        ttk.Button(win,text='Song / UGC converter…',command=lambda:(win.destroy(),self.guard(lambda:self.song_studio(True)))).pack(fill='x',padx=12,pady=4)
        choices_frame=ttk.Frame(win);choices_frame.pack(fill='both',expand=True,padx=8)
        for option_index,(label,file) in enumerate(options):
            def create(file=file):
                r = parse((BASE/'templates'/file).read_text(encoding='utf-8-sig'))
                if file=='Event-map.xml':
                    r.find('substances/map/mapName/id').text='-1';r.find('substances/map/mapName/str').text='Invalid'
                elif file=='Event-quest.xml': r.find('substances/quest/questNames/list').clear()
                elif file=='Event-rights.xml': r.find('substances/rightsInfo/rightsNames/list').clear()
                self.docs.append(r); self.current = len(self.docs)-1; self.dirty=True; self.refresh(); win.destroy()
            ttk.Button(choices_frame, text=label, command=lambda f=create: self.guard(f)).grid(row=option_index//2,column=option_index%2,sticky='ew',padx=4,pady=4)
        ttk.Label(win, text='Template rewards and references are retained. Review before exporting.', wraplength=330, padding=12).pack()

    def import_xml(self):
        for file in filedialog.askopenfilenames(filetypes=[('XML', '*.xml')]):
            root=parse(Path(file).read_text(encoding='utf-8-sig'))
            for path,_,_ in asset_slots(root)+binary_slots(root):
                filename=root.findtext(path,'')
                if filename and Path(filename).name==filename and '/' not in filename and '\\' not in filename:
                    asset=Path(file).parent/filename
                    if asset.is_file(): self.store_asset(filename,asset.read_bytes())
            self.docs.append(root); self.current=len(self.docs)-1; self.dirty=True
        self.refresh()

    def apply_identity(self):
        set_identity(self.root(), self.idvar.get(), self.namevar.get()); self.dirty=True; self.refresh()

    def select_field(self, _=None):
        if self.tree.selection():
            element=self.nodes[self.tree.selection()[0]]
            self.value.set((element.text or '').strip())
            self.field_help.set(describe_field(self.root(),element))

    def selected(self):
        if not self.tree.selection(): raise ValueError('Select a field.')
        return self.nodes[self.tree.selection()[0]]

    def set_value(self):
        el = self.selected()
        if len(el): raise ValueError('Select a leaf field to change its value.')
        el.text = self.value.get(); self.dirty=True; self.refresh()

    def parent_of(self, el):
        return next((p for p in self.root().iter() if el in list(p)), None)

    def duplicate(self):
        el = self.selected(); parent=self.parent_of(el)
        if parent is None: raise ValueError('Cannot duplicate the root.')
        if el.tag not in ('StringID', 'QuestRewardDataInfo', 'CharaRankData', 'RewardSubstanceData', 'MapDataAreaInfo', 'MapAreaGridData', 'MapBonusSubstanceData', 'MapAreaGridShorteningData'):
            raise ValueError('Select a repeatable list entry, map entry, area grid, bonus rule, quest milestone, reward content, or character rank.')
        parent.insert(list(parent).index(el)+1, copy.deepcopy(el)); self.dirty=True; self.refresh()

    def remove_node(self):
        el=self.selected(); parent=self.parent_of(el)
        if parent is None: raise ValueError('Cannot remove the root.')
        if messagebox.askyesno('Remove XML node', 'Remove '+el.tag+' and its children? Required fields may need to be restored manually.'):
            parent.remove(el); self.dirty=True; self.refresh()

    def add_child(self):
        import xml.etree.ElementTree as ET
        el=self.selected()
        text=simpledialog.askstring('Add XML child', 'Paste one XML element, e.g. a StringID or reward block:', parent=self)
        if text:
            if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper(): raise ValueError('Entities are not supported.')
            el.append(ET.fromstring(text)); self.dirty=True; self.refresh()

    def apply_raw(self):
        old=self.root()
        replacement=parse(self.raw.get('1.0', 'end'))
        self.docs[self.current]=replacement
        layout=self.nameplate_layouts.pop(id(old),None)
        if layout is not None and replacement.tag=='NamePlateData':self.nameplate_layouts[id(replacement)]=layout
        self.dirty=True; self.refresh()

    def remove_doc(self):
        if self.current is not None and messagebox.askyesno('Remove item', 'Remove selected item, its editable layers, and attached files not used by other project items? Save project afterwards to make this permanent.'):
            from project_files import remove_item
            remove_item(self,self.current);self.refresh()
            if self.current is None: self.tree.delete(*self.tree.get_children()); self.raw.delete('1.0','end')

    def project_files(self):
        from project_files import open_manager
        open_manager(self)

    def add_source(self):
        if self.scanning: raise ValueError("Wait for the current scan to finish.")
        import re
        folder=filedialog.askdirectory(title='Select an Axxx folder (including A000)')
        if not folder: return
        if not re.fullmatch(r'A[0-9A-Za-z]{3}', Path(folder).name): raise ValueError('Select an Axxx folder itself, such as A000 or A123.')
        if folder not in self.folders: self.folders.append(folder); self.dirty=True
        self.rescan()

    def bulk_sources(self):
        if self.scanning: raise ValueError('Wait for the current scan to finish.')
        folder=filedialog.askdirectory(title='Select a parent folder containing your Axxx folders')
        if not folder: return
        self.scanning=True
        self.warning.set('Finding Axxx folders…')
        def work():
            try: self.bulk_messages.put(discover_sources(folder))
            except Exception as exc: self.bulk_messages.put(([], [str(exc)]))
        threading.Thread(target=work, daemon=True).start()

    def remove_source(self):
        if self.scanning: raise ValueError("Wait for the current scan to finish.")
        if self.sources.curselection(): self.folders.pop(self.sources.curselection()[0]); self.dirty=True; self.rescan()

    def rescan(self):
        if self.scanning: raise ValueError('A scan is already running. Wait for it to finish.')
        self.sources.delete(0,'end')
        for p in self.folders: self.sources.insert('end',p)
        self.scanning=True; self.warning.set('Scanning source folders…')
        folders=list(self.folders)
        def work():
            try:
                definitions=[]; index,errors=scan(folders,definitions)
                self.messages.put((index,errors,definitions))
            except Exception as e: self.messages.put(({}, [str(e)],[]))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            found, errors = self.bulk_messages.get_nowait()
            self.scanning=False
            existing={str(Path(p).resolve()) for p in self.folders}
            added=[p for p in found if p not in existing]
            self.folders.extend(added)
            if added: self.dirty=True
            summary=f'Added {len(added)} Axxx folder(s). Skipped {len(found)-len(added)} already imported folder(s).'
            if errors: summary+='\nSome folders could not be searched:\n'+'\n'.join(errors[:10])
            if not found: summary+='\nNo Axxx folders found in the selected location.'
            messagebox.showinfo('Bulk import', summary)
            self.rescan()
        except queue.Empty: pass
        try:
            self.index, self.errors, self.source_definitions = self.messages.get_nowait(); self.scanning=False; self.check_conflict()
            if self.current is not None:
                from cv_workflow import update_overview
                update_overview(self)
            if self.errors: messagebox.showwarning('Incomplete scan', f'{len(self.errors)} scan error(s). View index / scan errors for details. Conflicts may be missing.')
        except queue.Empty: pass
        self.after(100, self.poll)

    def view_index(self):
        w=tk.Toplevel(self); w.title('Imported ID index'); w.geometry('850x520')
        t=tk.Text(w, wrap='word'); t.pack(fill='both',expand=True)
        for (kind, num), entries in sorted(self.index.items()):
            for name,path in entries: t.insert('end',f'{kind_label(kind)}  {num}  {name}\n{path}\n\n')
        t.insert('end','SCAN ERRORS\n'+'\n'.join(getattr(self,'errors',[]))); t.configure(state='disabled')

    def save_project(self):
        file=filedialog.asksaveasfilename(defaultextension='.cvproject', filetypes=[('ChuniVaina project','*.cvproject')])
        if file:
            Path(file).write_text(json.dumps({'version':1,'folders':self.folders,'documents':[serialize(r) for r in self.docs], 'assets':{n:base64.b64encode(b).decode('ascii') for n,b in self.assets.items()},'nameplate_layouts':[self.nameplate_layouts.get(id(r)) for r in self.docs]},ensure_ascii=False,indent=2),encoding='utf-8'); self.dirty=False

    def may_discard(self):
        return not self.dirty or messagebox.askyesno('Unsaved project', 'Discard unsaved project changes? Save first if you want to keep them.')

    def open_project(self):
        if self.scanning: raise ValueError("Wait for the current scan to finish.")
        if not self.may_discard(): return
        file=filedialog.askopenfilename(filetypes=[('ChuniVaina project','*.cvproject')])
        if file:
            data=json.loads(Path(file).read_text(encoding='utf-8'))
            if data.get('version') != 1: raise ValueError('Unsupported project version.')
            docs=[parse(s) for s in data['documents']]
            assets={n:base64.b64decode(b,validate=True) for n,b in data.get('assets',{}).items()}
            for name,b in assets.items(): validate_asset(name,b)
            from plate_model import validate_layout
            layouts=data.get('nameplate_layouts',[None]*len(docs))
            if not isinstance(layouts,list) or len(layouts)!=len(docs):raise ValueError('Invalid nameplate layout list.')
            for root,layout in zip(docs,layouts):
                if layout is not None:
                    if root.tag!='NamePlateData':raise ValueError('Layer layout attached to a non-nameplate item.')
                    validate_layout(layout)
            self.nameplate_layouts={id(r):layout for r,layout in zip(docs,layouts) if layout is not None}
            self.assets=assets
            self.docs=docs; self.folders=data['folders']; self.current=0 if docs else None; self.dirty=False; self.refresh(); self.rescan()

    def export(self):
        r=self.root(); validate(r)
        self.warn_song_constants([r])
        files=artwork_files(r,self.assets)
        if self.scanning: raise ValueError('Wait for the source scan to finish.')
        key=identity(r)
        conflicts=self.index.get(key,[]) or any(identity(d)==key for i,d in enumerate(self.docs) if i!=self.current)
        if conflicts and not messagebox.askyesno('ID conflict', 'This ID is already defined. Export anyway?'): return
        if getattr(self,'errors',[]) and not messagebox.askyesno('Incomplete index','The source scan had errors. Export with incomplete conflict checking?'): return
        folder=filedialog.askdirectory(title='Choose output folder (content subfolder will be created)')
        if folder:
            out=export_path(folder,r)
            if any(out.resolve().is_relative_to(Path(p).resolve()) for p in self.folders): raise ValueError('Choose an output folder outside imported game sources.')
            existing=[p for p in [out]+[out.parent/n for n,_ in files] if p.exists()]
            if existing and not messagebox.askyesno('Replace exported files', 'Replace these files?\n'+'\n'.join(str(p) for p in existing)): return
            out.parent.mkdir(parents=True,exist_ok=True); out.write_text(serialize(r),encoding='utf-8')
            for filename,data in files: (out.parent/filename).write_bytes(data)
            messagebox.showinfo('Exported',str(out))

    def artwork_studio(self):
        if self.root().tag=='RightsInfoData':
            from rights_editor import open_editor
            open_editor(self)
            return
        if self.root().tag=='NamePlateData':
            from plate_editor import open_composer
            open_composer(self)
            return
        try: from artwork import open_studio
        except ImportError: raise ValueError('Install artwork support with: python3 -m pip install -r requirements.txt, then rebuild the app if needed.')
        open_studio(self)

    def stage_studio(self):
        if self.root().tag!='StageData': raise ValueError('Select a Stage item first. Import Stage.xml with its AFB files beside it, or create a new Stage.')
        from stage_editor import open_editor
        open_editor(self)

    def store_asset(self, filename, data):
        validate_asset(filename,data)
        if filename in self.assets and self.assets[filename]!=data:
            raise ValueError('A different asset already uses filename '+filename+'. Rename the new file before attaching.')
        self.assets[filename]=data

    def attach_dds(self):
        root=self.root(); slots=asset_slots(root)
        if not slots: raise ValueError('Select character artwork, nameplate, map artwork, an event, or a stage preview.')
        if len(slots)>1:
            slot=simpledialog.askinteger('Artwork slot','Slot: 0 = 1080×1080, 1 = 512×512, 2 = 128×128',minvalue=0,maxvalue=len(slots)-1,parent=self)
            if slot is None: return
        else: slot=0
        path,_,expected=slots[slot]
        node=root.find(path)
        if node is None: raise ValueError('Missing artwork path. Restore it in the XML editor.')
        file=filedialog.askopenfilename(title='Choose DDS artwork',filetypes=[('DDS artwork','*.dds')])
        if not file: return
        data=Path(file).read_bytes(); w,h,m=dds_info(data)
        if (w,h)!=expected and not messagebox.askyesno('Artwork size differs',f'This DDS is {w}×{h}; the reference uses {expected[0]}×{expected[1]}. Attach anyway?'): return
        self.store_asset(Path(file).name,data)
        node.text=Path(file).name; self.dirty=True; self.show()

    def link_artwork(self):
        root=self.root()
        if root.tag!='CharaData': raise ValueError('Select a character to link its artwork.')
        choices=[r for r in self.docs if r.tag=='DDSImageData']
        if not choices: raise ValueError('Create or import a Character artwork item first.')
        win=tk.Toplevel(self); win.title('Link character artwork'); win.transient(self)
        ttk.Label(win,text='Choose a DDSImage definition from this project:',padding=12).pack()
        selected=tk.StringVar()
        combo=ttk.Combobox(win,state='readonly',textvariable=selected,width=50,values=[f'{r.findtext("name/id")} · {r.findtext("name/str")}' for r in choices]); combo.pack(padx=12); combo.current(0)
        slotvar=tk.StringVar(value='Default')
        ttk.Combobox(win,state='readonly',textvariable=slotvar,values=['Default']+[f'Alternate {i}' for i in range(1,10)]).pack(pady=8)
        def apply():
            artwork=choices[combo.current()]
            if slotvar.get()=='Default': target=root.find('defaultImages')
            else:
                slot=int(slotvar.get().split()[-1]); target=root.find(f'addImages{slot}/image')
                root.find(f'addImages{slot}/changeImg').text='true'
            if target is None: raise ValueError('Character has no matching image field.')
            target.find('id').text=artwork.findtext('name/id'); target.find('str').text=artwork.findtext('name/str')
            self.dirty=True; self.show(); win.destroy()
        ttk.Button(win,text='Link artwork',command=lambda: self.guard(apply)).pack(pady=12)

    def link_reward(self):
        root=self.root()
        if root.tag=='RewardData':
            node=self.selected()
            while node is not None and node.tag!='RewardSubstanceData': node=self.parent_of(node)
            if node is None: raise ValueError('Select a RewardSubstanceData entry or a field inside it.')
            choices=[r for r in self.docs if r.tag in ('TrophyData','CharaData','NamePlateData','StageData')]
            action=configure_reward
            description='Set this reward entry to grant a trophy, character, nameplate, or stage:'
        elif root.tag=='QuestData':
            node=self.selected()
            while node is not None and node.tag!='QuestRewardDataInfo': node=self.parent_of(node)
            if node is None: raise ValueError('Select a QuestRewardDataInfo milestone or a field inside it.')
            choices=[r for r in self.docs if r.tag=='RewardData']
            action=add_quest_reward
            description='Add a reward to this quest milestone:'
        else: raise ValueError('Select a Reward or Quest item first.')
        if not choices: raise ValueError('Create or import the target project items first.')
        win=tk.Toplevel(self); win.title('Link reward'); win.transient(self)
        ttk.Label(win,text=description,padding=12).pack()
        combo=ttk.Combobox(win,state='readonly',width=65,values=[f'{KINDS[r.tag][0]} · {r.findtext("name/id")} · {r.findtext("name/str")}' for r in choices]); combo.pack(padx=12); combo.current(0)
        def apply():
            action(node,choices[combo.current()]); self.dirty=True; self.show(); win.destroy()
        ttk.Button(win,text='Apply link',command=lambda: self.guard(apply)).pack(pady=12)

    def world_editor(self):
        from world import open_editor
        root=self.root()
        template=parse((BASE/'templates'/KINDS[root.tag][2]).read_text(encoding='utf-8-sig'))
        open_editor(self,template)

    def check_references(self):
        issues=reference_report(self.docs,self.index)+character_unlock_warnings(self.docs,self.source_definitions)
        w=tk.Toplevel(self); w.title('Project reference check'); w.geometry('850x540')
        text=tk.Text(w,wrap='word',padx=12,pady=12); text.pack(fill='both',expand=True)
        text.insert('end','Known references are checked against the project and imported ID index. External dependencies not indexed may be valid. This does not verify game/server event activation.\n\n')
        text.insert('end','\n\n'.join(issues) if issues else 'No unresolved known references found.')
        text.configure(state='disabled')

    def link_reference(self):
        node=self.selected()
        while node is not None and not (node.find('id') is not None and node.find('str') is not None) and node.tag!='list': node=self.parent_of(node)
        if node is None: raise ValueError('Select an ID/name reference or a supported reference list.')
        is_list=node.tag=='list'
        if is_list:
            parent=self.parent_of(node); kind=LIST_REFERENCE_TYPES.get(parent.tag) if parent is not None else None
        elif node.tag=='StringID':
            parent=self.parent_of(node); outer=self.parent_of(parent) if parent is not None else None
            kind=LIST_REFERENCE_TYPES.get(outer.tag) if outer is not None else None
        else: kind=REFERENCE_TYPES.get(node.tag)
        if kind is None: raise ValueError('No verified type mapping for this field. Edit its ID/name manually.')
        choices=[(r.findtext('name/id'),r.findtext('name/str')) for r in self.docs if r.tag==kind]
        choices += [(str(num),name) for (tag,num),entries in self.index.items() if tag==kind for name,_ in entries]
        choices=list(dict.fromkeys(choices))
        if not choices: raise ValueError('Create/import a '+kind_label(kind)+' or scan sources containing it first.')
        win=tk.Toplevel(self); win.title('Link '+kind_label(kind)); win.transient(self); win.grab_set()
        combo=ttk.Combobox(win,state='readonly',width=65,values=[f'{num} · {name}' for num,name in choices]);combo.pack(padx=12,pady=12);combo.current(0)
        def apply():
            import xml.etree.ElementTree as ET
            num,name=choices[combo.current()]
            if is_list:
                if any(r.findtext('id')==num for r in node): raise ValueError('That item is already in this list.')
                ref=ET.SubElement(node,'StringID');ET.SubElement(ref,'id');ET.SubElement(ref,'str');ET.SubElement(ref,'data')
            else: ref=node
            ref.find('id').text=num;ref.find('str').text=name
            self.dirty=True;self.show();win.destroy()
        ttk.Button(win,text='Apply reference',command=lambda:self.guard(apply)).pack(pady=12)

    def link_event_target(self):
        import xml.etree.ElementTree as ET
        event=self.root()
        code=event.findtext('substances/type')
        if event.tag!='EventData' or code not in ('2','8','11'):
            raise ValueError('Use New → Map-opening event (type 2) or Quest-opening event (type 8), or Rights-information event (type 11), then select it.')
        kind={'2':'MapData','8':'QuestData','11':'RightsInfoData'}[code]
        choices=[(r.findtext('name/id'),r.findtext('name/str')) for r in self.docs if r.tag==kind]
        choices += [(str(num),name) for (tag,num),entries in self.index.items() if tag==kind for name,_ in entries]
        choices=list(dict.fromkeys(choices))
        if not choices: raise ValueError('Create/import the target '+KINDS[kind][0]+' first.')
        win=tk.Toplevel(self);win.title('Link event target');win.transient(self);win.grab_set()
        ttk.Label(win,text='Choose the '+KINDS[kind][0]+' for this opening event:',padding=12).pack()
        combo=ttk.Combobox(win,state='readonly',width=65,values=[f'{num} · {name}' for num,name in choices]);combo.pack(padx=12);combo.current(0)
        def apply():
            num,name=choices[combo.current()]
            target=ET.Element(kind);ref=ET.SubElement(target,'name');ET.SubElement(ref,'id').text=num;ET.SubElement(ref,'str').text=name
            configure_activation(event,target);self.dirty=True;self.show();win.destroy()
        ttk.Button(win,text='Link target',command=lambda:self.guard(apply)).pack(pady=12)

    def review_character_unlocks(self):
        issues=character_unlock_warnings(self.docs,self.source_definitions)
        if not issues: return True
        win=tk.Toplevel(self);win.title('Characters may be unobtainable');win.geometry('850x500');win.transient(self);win.grab_set()
        ttk.Label(win,text='Some characters are not owned by default and have no verified configured unlock path.',wraplength=800,padding=12).pack(anchor='w')
        text=tk.Text(win,wrap='word',padx=12,pady=12);text.pack(fill='both',expand=True)
        text.insert('end','\n\n'.join(issues)+'\n\nSet defaultHave to true to make them available by default, or link them to a character-granting Reward used by a map completion, a linked map-area checkpoint, or a quest milestone.\n\nThis checks supported definitions in this project and imported sources. Other unlock systems and server availability are not verified.');text.configure(state='disabled')
        result=[False]
        def proceed(): result[0]=True;win.destroy()
        buttons=ttk.Frame(win,padding=12);buttons.pack(fill='x')
        ttk.Button(buttons,text='Back to editor',command=win.destroy).pack(side='left')
        ttk.Button(buttons,text='Export anyway',command=proceed).pack(side='right')
        self.wait_window(win)
        return result[0]

    def export_axxx(self):
        import re
        if not self.docs: raise ValueError('Create or import project content first.')
        if self.scanning: raise ValueError('Wait for the source scan to finish.')
        for root in self.docs: validate(root)
        self.warn_song_constants(self.docs)
        keys=[identity(root) for root in self.docs]
        if len(keys) != len(set(keys)):
            raise ValueError('Resolve duplicate IDs within this project before exporting an Axxx folder.')
        if not self.review_character_unlocks(): return
        if any(r.tag in ('MapData','MapAreaData','MapBonusData','EventData','MusicData') for r in self.docs):
            issues=reference_report(self.docs,self.index)
            if issues and not messagebox.askyesno('Reference review',str(len(issues))+' reference/activation note(s). Use Check references for details.\n\n'+'\n'.join(issues[:5])+'\n\nExport anyway?'): return
        conflicts=[f'{KINDS[k[0]][0]} {k[1]}' for k in keys if k in self.index]
        if conflicts and not messagebox.askyesno('Imported ID conflicts', 'These project IDs already exist in imported sources:\n'+', '.join(conflicts)+'\nExport anyway?'): return
        if getattr(self,'errors',[]) and not messagebox.askyesno('Incomplete index','Source scanning had errors. Continue with incomplete conflict checks?'): return
        name=simpledialog.askstring('Option folder name','Name for the new folder, e.g. A900:', initialvalue='A900', parent=self)
        if name is None: return
        name=name.strip()
        if not re.fullmatch(r'A[0-9A-Za-z]{3}',name): raise ValueError('Use A followed by three letters or digits, e.g. A900.')
        from cv_workflow import export_settings
        settings=export_settings(self)
        if settings is None: return
        folder=filedialog.askdirectory(title='Choose the parent directory for '+name)
        if not folder: return
        dest=(Path(folder)/name).resolve()
        if any(dest.is_relative_to(Path(p).resolve()) for p in self.folders):
            raise ValueError('Choose an output location outside imported source folders.')
        output=export_option(folder,name,self.docs,assets=self.assets,version=settings[0])
        messagebox.showinfo('Option exported',f'Exported {len(self.docs)} item(s) to:\n{output}\n\nIncludes XML definitions and attached DDS/AFB assets, song charts and audio banks. Other external dependencies must be supplied separately.')

    def close(self):
        if self.may_discard(): self.destroy()

if __name__=='__main__': App().mainloop()
