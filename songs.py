"""Search imported song metadata without importing/editing song content."""
import tkinter as tk
from tkinter import ttk
from core import search_songs


def choose_song(parent, catalog, on_select):
    win=tk.Toplevel(parent);win.title('Choose task track');win.geometry('850x540');win.transient(parent);win.grab_set()
    ttk.Label(win,text='Search song title, artist, or ID',font=('Helvetica',16,'bold'),padding=12).pack(anchor='w')
    query=tk.StringVar();entry=ttk.Entry(win,textvariable=query);entry.pack(fill='x',padx=12,pady=(0,8))
    status=tk.StringVar();ttk.Label(win,textvariable=status,padding=(12,0,12,8)).pack(anchor='w')
    frame=ttk.Frame(win,padding=12);frame.pack(fill='both',expand=True)
    listing=ttk.Treeview(frame,columns=('title','artist','id'),show='headings',selectmode='browse')
    for key,label,width in [('title','Song',360),('artist','Artist',280),('id','ID',80)]:
        listing.heading(key,text=label);listing.column(key,width=width)
    scroll=ttk.Scrollbar(frame,orient='vertical',command=listing.yview);listing.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right',fill='y');listing.pack(fill='both',expand=True)
    rows=[];pending=[None]
    def render():
        pending[0]=None;matches=search_songs(catalog,query.get());rows[:]=matches[:200]
        listing.delete(*listing.get_children())
        for i,(num,title,artist) in enumerate(rows):listing.insert('','end',iid=str(i),values=(title,artist,num))
        status.set(f'{len(matches)} matching songs · showing {len(rows)}. Refine your search to narrow the results.' if catalog else 'No songs indexed. Import A000 and your Axxx folders, then Rescan sources.')
        if rows:listing.selection_set('0')
    def search(*_):
        if pending[0] is not None:win.after_cancel(pending[0])
        pending[0]=win.after(120,render)
    def close():
        if pending[0] is not None:win.after_cancel(pending[0])
        win.destroy()
        if parent.winfo_exists():parent.grab_set()
    def apply(_=None):
        if listing.selection():on_select(rows[int(listing.selection()[0])]);close()
    buttons=ttk.Frame(win,padding=12);buttons.pack(fill='x')
    ttk.Button(buttons,text='Cancel',command=close).pack(side='left')
    ttk.Button(buttons,text='Use selected song',command=apply).pack(side='right')
    listing.bind('<Double-1>',apply);entry.bind('<Return>',apply);query.trace_add('write',search)
    win.protocol('WM_DELETE_WINDOW',close);render();entry.focus_set()
