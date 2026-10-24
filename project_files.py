"""Embedded file management. Source files on disk are never deleted."""
from core import kind_label

def file_references(documents):
    refs={}
    for root in documents:
        for node in root.iter('path'):
            if node.text:refs.setdefault(node.text,[]).append((root,node))
    return refs

def unused_files(documents,assets):
    refs=file_references(documents)
    return sorted(name for name in assets if name not in refs)

def delete_files(documents,assets,names,clear_references=False):
    names=set(names);refs=file_references(documents)
    if names-set(assets):raise ValueError('Some files are no longer in the project.')
    if not clear_references and any(refs.get(n) for n in names):raise ValueError('Some files are still used by project items.')
    if clear_references:
        for name in names:
            for _,node in refs.get(name,[]):node.text=''
    total=sum(len(assets[name]) for name in names)
    for name in names:del assets[name]
    return total

def remove_item(app,index):
    root=app.docs[index];candidates=set(file_references([root]))
    app.nameplate_layouts.pop(id(root),None);app.docs.pop(index)
    remaining=file_references(app.docs);removed=[]
    for name in candidates:
        if name in app.assets and name not in remaining:del app.assets[name];removed.append(name)
    app.current=min(index,len(app.docs)-1) if app.docs else None;app.dirty=True
    return removed

def open_manager(app):
    import tkinter as tk
    from tkinter import ttk,messagebox
    win=tk.Toplevel(app);win.title('ChuniVaina · Project files');win.geometry('850x540');win.transient(app);win.grab_set()
    ttk.Label(win,text='Embedded project files',font=('Helvetica',18,'bold'),padding=12).pack(anchor='w')
    ttk.Label(win,text='Remove embedded files, then Save project to write the smaller project file. Original files on disk are untouched.',wraplength=800,padding=(12,0,12,8)).pack(anchor='w')
    body=ttk.Frame(win,padding=12);body.pack(fill='both',expand=True)
    listing=ttk.Treeview(body,columns=('name','size','used'),show='headings',selectmode='extended')
    for key,label,width in [('name','File',330),('size','Size (KiB)',100),('used','Used by',340)]:
        listing.heading(key,text=label);listing.column(key,width=width)
    scroll=ttk.Scrollbar(body,command=listing.yview);listing.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right',fill='y');listing.pack(fill='both',expand=True)
    status=tk.StringVar();ttk.Label(win,textvariable=status,padding=(12,0)).pack(anchor='w')
    names=[]
    def users(refs):
        return ', '.join(dict.fromkeys(f'{kind_label(r.tag)} {r.findtext("name/id")}' for r,_ in refs))
    def refresh():
        listing.delete(*listing.get_children());names[:]=sorted(app.assets);refs=file_references(app.docs)
        for i,name in enumerate(names):
            listing.insert('','end',iid=str(i),values=(name,f'{len(app.assets[name])/1024:,.1f}',users(refs.get(name,[])) or 'Unused'))
        status.set(f'{len(names)} files · {sum(map(len,app.assets.values()))/1048576:,.2f} MiB · {len(unused_files(app.docs,app.assets))} unused')
    def remove(unused=False):
        chosen=unused_files(app.docs,app.assets) if unused else [names[int(i)] for i in listing.selection()]
        if not chosen:
            messagebox.showinfo('Project files','No unused files.' if unused else 'Select one or more files first.',parent=win);return
        refs=file_references(app.docs);used=[n for n in chosen if refs.get(n)]
        detail='\n'.join(chosen[:12])+('\n…' if len(chosen)>12 else '')
        if used:
            detail+='\n\nStill used by:\n'+'\n'.join(n+': '+users(refs[n]) for n in used[:8])
            detail+='\n\nTheir file references will also be cleared. Required files must be replaced before these items can export. Editable nameplate layers are separate and remain with their item.'
        if not messagebox.askyesno('Remove project files?',f'Remove {len(chosen)} embedded file(s)?\n\n'+detail,parent=win):return
        delete_files(app.docs,app.assets,chosen,clear_references=True);app.dirty=True
        if app.current is not None:app.show()
        refresh()
    controls=ttk.Frame(win,padding=12);controls.pack(fill='x')
    ttk.Button(controls,text='Remove selected files…',command=lambda:remove()).pack(side='left')
    ttk.Button(controls,text='Remove all unused files…',command=lambda:remove(True)).pack(side='left',padx=8)
    ttk.Button(controls,text='Close',command=win.destroy).pack(side='right')
    refresh()
