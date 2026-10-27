"""Song studio notice and durable, app-local preferences."""
import json
import os
import sys
from pathlib import Path

CUSTOMS_URL='https://github.com/Suprnova/Chunithm-Research/blob/main/Customs.md'
RESOURCE_CREDIT='Audio preparation guide / rhythm-game research by Suprnova'
NOTICE=(
    'Notice:\n'
    'This application does not have the feature to convert audio to the required files for the game '
    '(I tried to add it, if that makes you feel better…)\n\n'
    'This application DOES support conversion from UMIGURI (.ugc), and does allow you to import '
    'your already prepared acb/awb. Please follow the resource for instructions on how to prepare your audio files.\n\n'
    'The ACB/AWB fixer can repair supported prepared HCA banks: it corrects metadata and applies the '
    'game audio cipher treatment without re-encoding the sound. WAV/MP3 conversion still requires external tools.'
)

def preferences_path():
    if sys.platform=='darwin':
        return Path.home()/'Library/Application Support/ChuniVaina/preferences.json'
    if sys.platform=='win32':
        return Path(os.environ.get('APPDATA',str(Path.home()/'AppData/Roaming')))/'ChuniVaina/preferences.json'
    return Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'ChuniVaina/preferences.json'

def load_preferences(path=None):
    try:
        value=json.loads((path or preferences_path()).read_text(encoding='utf-8'))
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError):
        return {}

def save_notice_preference(hidden,path=None):
    save_preferences({'hide_song_audio_notice':bool(hidden)},path)

def save_preferences(updates,path=None):
    path=path or preferences_path()
    values=load_preferences(path);values.update(updates)
    path.parent.mkdir(parents=True,exist_ok=True)
    import tempfile
    fd,temporary=tempfile.mkstemp(prefix='.preferences-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as out:json.dump(values,out,indent=2)
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)

def show_notice(app):
    if load_preferences().get('hide_song_audio_notice') is True:return
    import tkinter as tk
    from tkinter import ttk,messagebox
    import webbrowser
    win=tk.Toplevel(app);win.title('Song studio · Notice');win.transient(app);win.grab_set()
    body=ttk.Frame(win,padding=20);body.pack(fill='both',expand=True)
    ttk.Label(body,text=NOTICE,wraplength=580,justify='left').pack(anchor='w')
    ttk.Label(body,text=RESOURCE_CREDIT,wraplength=580).pack(anchor='w',pady=(16,8))
    hidden=tk.BooleanVar(value=False)
    ttk.Checkbutton(body,text='Don’t show again',variable=hidden).pack(anchor='w',pady=8)
    def okay():
        try:save_notice_preference(hidden.get())
        except OSError as exc:
            messagebox.showerror('Could not save preference',str(exc),parent=win)
            return
        win.destroy()
    def source():
        try:
            if not webbrowser.open(CUSTOMS_URL):
                messagebox.showinfo('Audio preparation guide',CUSTOMS_URL,parent=win)
        except Exception:
            messagebox.showinfo('Audio preparation guide',CUSTOMS_URL,parent=win)
    row=ttk.Frame(body);row.pack(fill='x',pady=(8,0))
    ttk.Button(row,text='Okay',command=okay).pack(side='left')
    ttk.Button(row,text='Audio preparation guide',command=source).pack(side='left',padx=8)
    win.protocol('WM_DELETE_WINDOW',okay)
    win.bind('<Return>',lambda event:okay())
    app.wait_window(win)
