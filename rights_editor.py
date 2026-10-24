"""Live rights text-image editor; applies the flattened DDS to the project."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox,colorchooser
from PIL import Image,ImageTk
from artwork import decode
from rights_model import render_text,default_font_path,apply_artwork

def open_editor(app):
    root=app.root()
    if root.tag!='RightsInfoData':raise ValueError('Select Rights information first.')
    win=tk.Toplevel(app);win.title('ChuniVaina · Rights text image');win.geometry('760x600');win.minsize(620,520)
    win.transient(app);win.grab_set()
    header=ttk.Frame(win,padding=14);header.pack(fill='x')
    ttk.Label(header,text='Rights text → DDS',font=('Helvetica',20,'bold')).pack(side='left')
    body=ttk.Frame(win,padding=(14,0,14,12));body.pack(fill='both',expand=True)
    ttk.Label(body,text='512×48 · DXT5 with transparency · one mip. Set the rights ID before applying.',wraplength=710).pack(anchor='w')
    ttk.Label(body,text='Text (line breaks are supported)').pack(anchor='w',pady=(12,4))
    editor=tk.Text(body,height=4,wrap='word');editor.pack(fill='x');editor.insert('1.0',root.findtext('rightsText',''))
    font=tk.StringVar(value=default_font_path());size=tk.StringVar(value='16');align=tk.StringVar(value='left');fit=tk.BooleanVar(value=True);color=tk.StringVar(value='#000000')
    options=ttk.Frame(body);options.pack(fill='x',pady=10)
    ttk.Label(options,text='Size').pack(side='left');ttk.Spinbox(options,from_=6,to=96,width=5,textvariable=size).pack(side='left',padx=4)
    ttk.Combobox(options,values=['left','center','right'],textvariable=align,state='readonly',width=8).pack(side='left',padx=6)
    ttk.Checkbutton(options,text='Shrink to fit',variable=fit).pack(side='left',padx=4)
    def choose_color():
        chosen=colorchooser.askcolor(color.get(),parent=win)[1]
        if chosen:color.set(chosen)
    ttk.Button(options,text='Text color…',command=choose_color).pack(side='left',padx=4)
    def choose_font():
        path=filedialog.askopenfilename(parent=win,title='Choose a font with your required glyphs',filetypes=[('Font files','*.ttf *.otf *.ttc')])
        if path:font.set(path)
    ttk.Button(body,text='Choose font…',command=choose_font).pack(anchor='w')
    ttk.Label(body,textvariable=font,wraplength=710).pack(anchor='w',pady=4)
    ttk.Label(body,text='Choose a font that includes your text’s characters. Fonts/framing are used for this session; Save project retains the applied DDS.',wraplength=710).pack(anchor='w')
    preview=ttk.Label(body);preview.pack(fill='x',pady=14)
    status=tk.StringVar();ttk.Label(body,textvariable=status,wraplength=710).pack(anchor='w')
    pending=[None];rendered=[None];changed=[False];existing=root.findtext('image/path')
    def display(image):
        bg=Image.new('RGBA',image.size,'#DADDE2');bg=Image.alpha_composite(bg,image)
        preview.photo=ImageTk.PhotoImage(bg.convert('RGB'),master=win);preview.configure(image=preview.photo)
    def update():
        pending[0]=None
        try:
            image,used=render_text(editor.get('1.0','end-1c'),font.get(),size.get(),align.get(),color.get(),fit.get())
            rendered[0]=image;display(image);status.set(f'Live text preview · {used}px. Apply DDS & text commits to the project.')
        except Exception as exc:rendered[0]=None;status.set(str(exc))
    def schedule(*_):
        changed[0]=True
        if pending[0] is not None:win.after_cancel(pending[0])
        pending[0]=win.after(120,update)
    def text_changed(event):
        if editor.edit_modified():editor.edit_modified(False);schedule()
    editor.edit_modified(False);editor.bind('<<Modified>>',text_changed)
    for var in (font,size,align,fit,color):var.trace_add('write',schedule)
    def apply():
        if pending[0] is not None:win.after_cancel(pending[0]);pending[0]=None
        try:
            update()
            if rendered[0] is None:raise ValueError(status.get())
            name=apply_artwork(root,app.assets,app.docs,editor.get('1.0','end-1c'),rendered[0])
            app.dirty=True;changed[0]=False
            if app.root() is root:app.show()
            display(decode(app.assets[name]));status.set('Applied DDS & rightsText. Close and Save project to keep the result.')
        except Exception as exc:messagebox.showerror('Rights text image',str(exc),parent=win)
    ttk.Button(header,text='Apply DDS & text',command=apply).pack(side='right')
    def close():
        if changed[0] and not messagebox.askyesno('Discard text-image edits?','Close without applying these edits?',parent=win):return
        if pending[0] is not None:win.after_cancel(pending[0])
        win.destroy()
    ttk.Button(body,text='Close',command=close).pack(side='bottom',anchor='e')
    win.bind('<Command-s>',lambda event:apply());win.bind('<Control-s>',lambda event:apply());win.protocol('WM_DELETE_WINDOW',close)
    if existing in app.assets:
        display(decode(app.assets[existing]));status.set('Existing DDS preview. Applying renders the text above into a new DDS; original text layers cannot be recovered.')
    else:update()
