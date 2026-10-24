"""Background repair with explicit save/use actions; no source-file writes."""
import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from audio_repair import repair_bank,save_repaired_zip

def open_fixer(parent,initial_pair=None,on_apply=None,stem='music'):
    win=tk.Toplevel(parent);win.title('ChuniVaina · ACB/AWB fixer');win.geometry('800x570');win.minsize(650,500)
    win.transient(parent);win.grab_set()
    body=ttk.Frame(win,padding=16);body.pack(fill='both',expand=True)
    ttk.Label(body,text='ACB/AWB fixer',font=('Helvetica',20,'bold')).pack(anchor='w')
    ttk.Label(body,text='For externally prepared song banks: correct sample-rate/duration metadata and apply the CHUNITHM cipher treatment. Original files are kept intact.',wraplength=740).pack(anchor='w',pady=10)
    ttk.Label(body,text='Supported: one stereo HCA 2.0 stream at 44.1/48 kHz, 96-byte header. Existing type-56 audio stays encrypted as supplied. Other layouts and source WAV/MP3 conversion require external tools.',wraplength=740).pack(anchor='w',pady=4)
    pair=[initial_pair];name=[stem];result=[None];busy=[False];messages=queue.Queue();buttons=[]
    selected=tk.StringVar(value=stem+' · attached pair' if initial_pair else 'No pair selected.')
    status=tk.StringVar(value='Choose a pair, then Repair & verify. This can take a little while for long songs.')
    ttk.Label(body,textvariable=selected,wraplength=740).pack(anchor='w',pady=8)
    def choose():
        try:
            path=filedialog.askopenfilename(parent=win,title='Choose the ACB to repair',filetypes=[('ACB','*.acb')])
            if not path:return
            a=Path(path);w=a.with_suffix('.awb')
            if not w.is_file():
                other=filedialog.askopenfilename(parent=win,title='Choose its matching AWB',filetypes=[('AWB','*.awb')])
                if not other:return
                w=Path(other)
            pair[0]=(a.read_bytes(),w.read_bytes());name[0]=a.stem;result[0]=None
            text.configure(state='normal');text.delete('1.0','end');text.configure(state='disabled')
            selected.set(a.name+' + '+w.name);status.set('Pair loaded. Repair creates a verified copy.');controls()
        except Exception as exc:messagebox.showerror('ACB/AWB fixer',str(exc),parent=win)
    def controls():
        choose_button.configure(state='disabled' if busy[0] else 'normal')
        repair_button.configure(state='normal' if pair[0] and not busy[0] else 'disabled')
        for b in buttons:b.configure(state='normal' if result[0] and not busy[0] else 'disabled')
    choose_button=ttk.Button(body,text='Choose ACB/AWB pair…',command=choose);choose_button.pack(anchor='w')
    text=tk.Text(body,height=9,wrap='word',state='disabled');text.pack(fill='both',expand=True,pady=12)
    def show_report(report):
        old=report['metadata_before']
        lines=[
            'Repair verified.' if report['changed'] else 'Already consistent; no changes needed.',
            f'Sample rate: {old["SamplingRate"]} → {report["sample_rate"]} Hz',
            f'Sample count: {old["NumSamples"]} → {report["samples"]}',
            f'Music duration: {report["music_cue_length_ms_before"]/1000:.3f} → {report["music_cue_length_ms_after"]/1000:.3f} seconds',
            f'HCA cipher: {report["cipher_type"]} → {report["cipher_type_after"]}',
            report['verification'],
            'Cue graph, preview commands and internal bank name preserved.',
            'Cipher interoperability: public vgmstream CHUNITHM audio entry.',
            'WAV/MP3 encoding and unsupported bank layouts require external tools.',
        ]
        text.configure(state='normal');text.delete('1.0','end');text.insert('end','\n\n'.join(lines));text.configure(state='disabled')
    def repair():
        if pair[0] is None:return
        source=pair[0];busy[0]=True;result[0]=None;controls();status.set('Repairing and checking audio…')
        def work():
            try:messages.put(('ok',repair_bank(*source)))
            except Exception as exc:messages.put(('error',str(exc)))
        threading.Thread(target=work,daemon=True).start()
    def save():
        if result[0] is None:return
        path=filedialog.asksaveasfilename(parent=win,title='Save repaired pair as a new ZIP',initialfile=name[0]+'-fixed.zip',defaultextension='.zip',filetypes=[('ZIP','*.zip')])
        if not path:return
        try:
            save_repaired_zip(path,name[0],*result[0]);status.set('Saved '+path+'. Extract and replace both bank files together.')
        except FileExistsError:messagebox.showerror('Choose a new filename','The fixer keeps existing files intact. Choose a new ZIP filename.',parent=win)
        except Exception as exc:messagebox.showerror('Save repaired pair',str(exc),parent=win)
    def use():
        try:
            if result[0] is not None:on_apply(result[0][:2]);close()
        except Exception as exc:messagebox.showerror('Apply repaired pair',str(exc),parent=win)
    def close():
        if busy[0]:status.set('Wait for repair/verification to finish before closing.');return
        win.after_cancel(timer[0]);win.destroy()
        if parent.winfo_exists():parent.grab_set() if isinstance(parent,tk.Toplevel) else None
    footer=ttk.Frame(body);footer.pack(side='bottom',fill='x')
    repair_button=ttk.Button(footer,text='Repair & verify',command=repair);repair_button.pack(side='left')
    save_button=ttk.Button(footer,text='Save repaired ZIP…',command=save);save_button.pack(side='left',padx=6);buttons.append(save_button)
    if on_apply is not None:
        apply_button=ttk.Button(footer,text='Use repaired pair',command=use);apply_button.pack(side='left',padx=6);buttons.append(apply_button)
    ttk.Button(footer,text='Close',command=close).pack(side='right')
    ttk.Label(body,textvariable=status,wraplength=740).pack(fill='x',pady=(0,8))
    # Keep the current scheduled callback cancellable when the window closes.
    timer=[None]
    def schedule_poll():
        try:
            kind,value=messages.get_nowait();busy[0]=False
            if kind=='ok':result[0]=value;show_report(value[2]);status.set('Save a repaired ZIP, or use the pair in the editor. Save project afterwards to retain project changes.')
            else:status.set(value);messagebox.showerror('Repair stopped',value,parent=win)
            controls()
        except queue.Empty:pass
        timer[0]=win.after(100,schedule_poll)
    win.protocol('WM_DELETE_WINDOW',close);controls();schedule_poll()
