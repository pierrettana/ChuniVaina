import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from map_preview import checkpoints, GridPreview


class GridPreviewTests(unittest.TestCase):
    def nodes(self):
        return ET.parse(Path('templates/MapArea.xml')).getroot().findall('grids/MapAreaGridData')

    def test_sample_positions_and_reward_identity(self):
        nodes = self.nodes()
        before = [ET.tostring(n) for n in nodes]
        cells, warnings = checkpoints(nodes)
        self.assertEqual(list(cells), [0, 5, 25, 45, 55])
        self.assertEqual(warnings, [])
        self.assertEqual(cells[55][0], (4, '2', 'Exit'))
        self.assertIn('Point 1000 (ID 10000010)', cells[5][0][2])
        self.assertEqual(before, [ET.tostring(n) for n in nodes])

    def test_unsaved_invalid_and_duplicate_positions_keep_row_identity(self):
        nodes = self.nodes()
        nodes[1].find('index').text = '45'
        nodes[2].find('index').text = '-2'
        nodes[0].find('index').text = ''
        cells, warnings = checkpoints(nodes)
        self.assertEqual([e[0] for e in cells[45]], [1, 3])
        self.assertEqual(len(warnings), 3)
        self.assertIn('unique positions', warnings[-1])
        nodes[1].find('reward/rewardName/id').text = '-1'
        self.assertIn('Unassigned', checkpoints(nodes)[0][45][0][2])

    def test_large_area_draw_only_renders_viewport(self):
        shapes = []
        canvas = SimpleNamespace(delete=lambda *_: None, winfo_width=lambda: 600,
            winfo_height=lambda: 200, canvasy=lambda y: y + 66000,
            create_rectangle=lambda *a, **k: shapes.append(a), create_text=lambda *a, **k: None)
        view = SimpleNamespace(canvas=canvas, columns=5, cell_height=66,
            cells={1000000: [(0, '3', 'Reward')]}, selected=None, last=1000000)
        GridPreview.draw(view)
        self.assertGreater(len(shapes), 0)
        self.assertLessEqual(len(shapes), 25)

    def test_click_cycles_duplicate_rows_and_ignores_empty_cells(self):
        selected = []
        messages = []
        view = SimpleNamespace(canvas=SimpleNamespace(winfo_width=lambda: 500, canvasy=lambda y: y),
            columns=5, cell_height=66, cells={1: [(2, '3', 'First'), (4, '3', 'Second')]},
            selected=2, on_select=selected.append, message=SimpleNamespace(set=messages.append))
        GridPreview.click(view, SimpleNamespace(x=150, y=30))
        self.assertEqual(selected, [4])
        self.assertIn('Second', messages[-1])
        GridPreview.click(view, SimpleNamespace(x=250, y=30))
        self.assertEqual(selected, [4])


if __name__ == '__main__':
    unittest.main()
