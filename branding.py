"""Small, optional mascot touches using the supplied original artwork."""
from pathlib import Path
import sys

VERSION = '1.0.0'
BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))


def picture(parent, name='mascot.png', size=(100, 112)):
    from PIL import Image, ImageTk
    image = Image.open(BASE / 'assets' / name).convert('RGBA')
    image.thumbnail(size, Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(image, master=parent)


def badge(parent, size=(48, 48), full=False):
    from tkinter import ttk
    photo = picture(parent, 'mascot.png' if full else 'icon.png', size)
    label = ttk.Label(parent, image=photo)
    label.image = photo
    return label


def about(app):
    import tkinter as tk
    from tkinter import ttk
    win = tk.Toplevel(app)
    win.title('About ChuniVaina')
    win.transient(app)
    body = ttk.Frame(win, padding=24)
    body.pack(fill='both', expand=True)
    badge(body, (160, 170), full=True).pack(pady=(0, 12))
    ttk.Label(body, text='ChuniVaina ' + VERSION, font=('Helvetica', 22, 'bold')).pack()
    ttk.Label(body, text='A little penguin. A whole world of custom content.',
              wraplength=410, justify='center').pack(pady=10)
    ttk.Label(body, text='Created by Quincy · Mascot artwork supplied by Quincy\n'
              'An independent community tool; not affiliated with SEGA.\n\n'
              'Thanks to Suprnova for CHUNITHM research, vgmstream for\n'
              'audio interoperability research, and CriCodecs for HCA support.\n'
              'Built with Python, Tk and Pillow.', justify='center').pack()
    ttk.Button(body, text='Take the quick tour', command=lambda: open_tutorial(app)).pack(pady=(18, 6))
    ttk.Button(body, text='Close', command=win.destroy).pack()


STEPS = (
    ('Welcome to ChuniVaina!',
     'Let’s make something you’ll love seeing in-game. I’ll show you the basics in a few short steps. '
     'You can skip this tour at any time and reopen it from Quick tour.',
     'Your project is your workspace. Nothing is exported until you choose Export.'),
    ('Give your IDs a little breathing room',
     'Import A000 and your Axxx folders under ID CONFLICT SOURCES. Have lots of options? '
     'Bulk import lets you select a parent folder and choose multiple options together.',
     'Choose your own IDs. ChuniVaina warns about conflicts within each content type. Rescan after source changes.'),
    ('Make your first piece of content',
     'Choose New for a content template, or Import XML to use an existing definition. '
     'Set the ID and name, then click Apply identity. Select fields in the Structured editor to see their descriptions.',
     'Templates include references and release settings. Review them for your installation. Renaming an ID does not update other items’ links.'),
    ('A little artwork goes a long way',
     'Artwork studio previews and converts images. Character artwork has three sizes; '
     'nameplates have an editable layer composer. Rights information has a text-image editor. '
     'Stage texture editor works with your own supported AFB bundles.',
     'Click Apply inside each studio to bring its changes back into the project. Save project keeps the attached files and editable nameplate layers.'),
    ('Connect the unlocks',
     'A locked character needs a way to be earned. Create a Reward, link the character, trophy or nameplate, '
     'then deliver it through a map, area checkpoint or quest milestone. Map and quest opening events connect the pieces.',
     'The map editor’s live grid shows checkpoint positions. Search songs lets you pick a task track by title instead of memorizing IDs.'),
    ('Bring your own songs',
     'Song studio converts Margrete text UGC charts and imports prepared ACB/AWB audio. '
     'Use the linked audio preparation guide and the ACB/AWB fixer for supported banks. '
     'Audio encoding requires external tools.',
     'Choose a CHUNITHM version for each song and review chart constants against your server’s rules. Quick trophy creates separate EXPERT and MASTER ALL JUSTICE awards.'),
    ('Save it. Pack it. Play it.',
     'Save project keeps an editable .cvproject with its attachments. Check references, then Export Axxx folder '
     'and choose your option folder name. Export creates a new folder and leaves existing folders alone.',
     'Apply edits before saving: Set value, Apply identity, Apply XML edits, or the studio’s Apply button. Help / F1 is always here if you need a hand. Happy creating!'),
)


def open_tutorial(app):
    import tkinter as tk
    from tkinter import ttk, messagebox
    from song_notice import load_preferences, save_preferences
    existing = getattr(app, '_tutorial', None)
    if existing is not None and existing.winfo_exists():
        existing.lift()
        return
    win = tk.Toplevel(app)
    app._tutorial = win
    win.title('ChuniVaina · A little tour')
    win.geometry('720x560')
    win.minsize(650, 530)
    win.transient(app)
    body = ttk.Frame(win, padding=24)
    body.pack(fill='both', expand=True)
    top = ttk.Frame(body)
    top.pack(fill='x')
    badge(top, (108, 118), full=True).pack(side='left', padx=(0, 20))
    heading = tk.StringVar()
    ttk.Label(top, textvariable=heading, font=('Helvetica', 20, 'bold'), wraplength=470).pack(side='left')
    progress = tk.IntVar(value=1)
    ttk.Progressbar(body, maximum=len(STEPS), variable=progress).pack(fill='x', pady=18)
    text = tk.StringVar()
    tip = tk.StringVar()
    ttk.Label(body, textvariable=text, wraplength=590, justify='left', font=('Helvetica', 13)).pack(fill='x')
    ttk.Label(body, textvariable=tip, wraplength=590, justify='left', foreground='#725080').pack(fill='x', pady=20)
    footer = ttk.Frame(body)
    footer.pack(side='bottom', fill='x')
    hidden = tk.BooleanVar(value=load_preferences().get('hide_welcome_tour') is True)
    ttk.Checkbutton(footer, text='Don’t show this tour at startup', variable=hidden).pack(anchor='w', pady=(0, 14))
    row = ttk.Frame(footer)
    row.pack(fill='x')
    index = [0]
    counter = tk.StringVar()
    def close():
        try:
            save_preferences({'hide_welcome_tour': hidden.get()})
        except OSError as exc:
            messagebox.showerror('Could not save preference', str(exc), parent=win)
            return
        win.destroy()
    def move(delta):
        index[0] = max(0, min(len(STEPS)-1, index[0]+delta))
        render()
    def advance():
        if index[0] == len(STEPS)-1:
            hidden.set(True)
            close()
        else:
            move(1)
    back = ttk.Button(row, text='Back', command=lambda: move(-1))
    back.pack(side='left')
    ttk.Label(row, textvariable=counter).pack(side='left', padx=12)
    next_button = ttk.Button(row, command=advance)
    next_button.pack(side='right')
    ttk.Button(row, text='Skip tour', command=close).pack(side='right', padx=8)
    def render():
        title, paragraph, hint = STEPS[index[0]]
        heading.set(title)
        text.set(paragraph)
        tip.set('Penguin tip · ' + hint)
        progress.set(index[0]+1)
        counter.set(f'{index[0]+1} / {len(STEPS)}')
        back.configure(state='disabled' if index[0] == 0 else 'normal')
        next_button.configure(text='Let’s create!' if index[0] == len(STEPS)-1 else 'Next →')
    win.protocol('WM_DELETE_WINDOW', close)
    win.bind('<Escape>', lambda _: close())
    render()
    return win


def welcome_if_needed(app):
    from song_notice import load_preferences
    if load_preferences().get('hide_welcome_tour') is not True:
        open_tutorial(app)
