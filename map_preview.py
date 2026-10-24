"""Numbered XML positions, deliberately independent of the game's visual path."""
import math
import tkinter as tk
from tkinter import ttk


def checkpoints(nodes):
    """Keep XML row identity even when a draft has duplicate/invalid positions."""
    result = {}
    warnings = []
    for row, node in enumerate(nodes):
        try:
            position = int(node.findtext('index', ''))
            if position < 0:
                raise ValueError()
        except ValueError:
            warnings.append(f'Entry {row + 1}: enter a nonnegative grid position.')
            continue
        kind = node.findtext('type', '')
        label = {'1': 'Entrance', '2': 'Exit', '3': 'Reward'}.get(kind, f'Type {kind}')
        reward_id = node.findtext('reward/rewardName/id', '-1')
        name = node.findtext('reward/rewardName/str', '')
        if reward_id not in ('-1', ''):
            label += f' · {name or "Reward"} (ID {reward_id})'
        elif kind == '3':
            label += ' · Unassigned'
        result.setdefault(position, []).append((row, kind, label))
    for position, entries in result.items():
        if len(entries) > 1:
            warnings.append(f'Position {position} has {len(entries)} entries; choose unique positions.')
    return result, warnings


class GridPreview(ttk.LabelFrame):
    def __init__(self, parent, on_select):
        super().__init__(parent, text='Live area grid', padding=6)
        self.on_select = on_select
        self.cells = {}
        self.selected = None
        self.columns = 10
        self.cell_height = 66
        self.last = 0
        self.message = tk.StringVar()
        self.guide = ttk.Label(self, text='Positions run left → right, then next row. Schematic, not the in-game path. Click a checkpoint for details.', wraplength=460)
        self.guide.grid(row=0, column=0, columnspan=2, sticky='w')
        self.canvas = tk.Canvas(self, height=205, background='#172333', highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(self, orient='vertical', command=self.scroll)
        scroll.grid(row=1, column=1, sticky='ns')
        self.canvas.configure(yscrollcommand=scroll.set)
        self.status = ttk.Label(self, textvariable=self.message, wraplength=460)
        self.status.grid(row=2, column=0, columnspan=2, sticky='w')
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.canvas.bind('<Configure>', self.resize)
        self.canvas.bind('<Button-1>', self.click)
        self.canvas.bind('<MouseWheel>', self.wheel)
        self.canvas.bind('<Button-4>', lambda _: self.scroll('scroll', -1, 'units'))
        self.canvas.bind('<Button-5>', lambda _: self.scroll('scroll', 1, 'units'))

    def update_grid(self, nodes, selected=None, note='', reveal=False):
        self.cells, warnings = checkpoints(nodes)
        self.selected = selected
        self.last = max(self.cells, default=0)
        self.message.set(' '.join(warnings) or note or 'Green: entrance · Gold: reward · Purple: exit · Blue outline: selected · Red: duplicate position')
        rows = self.last // self.columns + 1
        self.canvas.configure(scrollregion=(0, 0, max(1, self.canvas.winfo_width()), rows * self.cell_height))
        if reveal:
            position = next((p for p, entries in self.cells.items() if any(e[0] == selected for e in entries)), None)
            if position is not None:
                top = self.canvas.canvasy(0)
                y = (position // self.columns) * self.cell_height
                if y < top or y + self.cell_height > top + self.canvas.winfo_height():
                    self.canvas.yview_moveto(y / (rows * self.cell_height))
        self.draw()

    def scroll(self, *args):
        self.canvas.yview(*args)
        self.draw()

    def resize(self, _=None):
        width = max(200, self.canvas.winfo_width())
        self.columns = max(2, min(10, width // 110))
        self.guide.configure(wraplength=width)
        self.status.configure(wraplength=width)
        self.canvas.configure(scrollregion=(0, 0, width, (self.last // self.columns + 1) * self.cell_height))
        self.draw()

    def wheel(self, event):
        delta = -int(event.delta / 120) if abs(event.delta) >= 120 else (-1 if event.delta > 0 else 1)
        self.scroll('scroll', delta, 'units')
        return 'break'

    def draw(self):
        c = self.canvas
        c.delete('all')
        width = max(c.winfo_width(), 200) / self.columns
        # Only paint visible rows, even for very long areas or widely spaced IDs.
        first = max(0, int(c.canvasy(0) // self.cell_height))
        end = min(self.last // self.columns + 1, math.ceil(c.canvasy(c.winfo_height()) / self.cell_height) + 1)
        for row in range(first, end):
            for col in range(self.columns):
                position = row * self.columns + col
                if position > self.last:
                    break
                entries = self.cells.get(position, [])
                selected = any(e[0] == self.selected for e in entries)
                color = '#28394b'
                if entries:
                    color = {'1': '#23664c', '2': '#614389', '3': '#76551e'}.get(entries[0][1], '#435367')
                if len(entries) > 1:
                    color = '#8d353d'
                x, y = col * width, row * self.cell_height
                c.create_rectangle(x+3, y+3, x+width-3, y+self.cell_height-3, fill=color, outline='#7bdcff' if selected else '#435367', width=3 if selected else 1)
                label = str(position)
                if entries:
                    detail = entries[0][2]
                    label += '\n' + ('DUPLICATE' if len(entries) > 1 else detail[:34] + ('…' if len(detail)>34 else ''))
                c.create_text(x+width/2, y+self.cell_height/2, text=label, fill='white', width=max(10, width-14), font=('Helvetica', 9), justify='center')

    def click(self, event):
        width = max(self.canvas.winfo_width(), 200) / self.columns
        position = int(self.canvas.canvasy(event.y) // self.cell_height) * self.columns + int(event.x // width)
        entries = self.cells.get(position, [])
        if entries:
            # Repeated clicks cycle overlapping entries so conflicts remain editable.
            rows = [e[0] for e in entries]
            target = rows[(rows.index(self.selected)+1) % len(rows)] if self.selected in rows else rows[0]
            self.on_select(target)
            self.message.set(entries[rows.index(target)][2] + f' · Grid {position}' + (' · Duplicate position' if len(entries)>1 else ''))
