import json,tempfile,unittest,copy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from core import parse,artwork_files
from project_files import remove_item,delete_files,unused_files

def item(name):
    r=parse(Path('templates/RightsInfo.xml').read_text());r.find('image/path').text=name;return r

class ProjectFileTests(unittest.TestCase):
    def test_remove_item_preserves_shared_files_and_removes_layers(self):
        a=item('shared.dds');b=item('shared.dds')
        app=SimpleNamespace(docs=[a,b],assets={'shared.dds':b'data','unused.dds':b'orphan'},nameplate_layouts={id(a):{'layers':['embedded source']}},current=0,dirty=False)
        self.assertEqual(remove_item(app,0),[]);self.assertIn('shared.dds',app.assets);self.assertFalse(app.nameplate_layouts)
        self.assertEqual(remove_item(app,0),['shared.dds']);self.assertNotIn('shared.dds',app.assets)
        self.assertEqual(unused_files(app.docs,app.assets),['unused.dds']);self.assertIsNone(app.current)
    def test_in_use_delete_is_atomic_and_clears_all_references_when_confirmed(self):
        a=item('used.dds');b=item('used.dds');assets={'used.dds':b'data','orphan.dds':b'orphan'}
        with self.assertRaises(ValueError):delete_files([a,b],assets,list(assets))
        self.assertEqual(len(assets),2);self.assertEqual(a.findtext('image/path'),'used.dds')
        delete_files([a,b],assets,['used.dds'],True)
        self.assertEqual(a.findtext('image/path'),'');self.assertEqual(b.findtext('image/path'),'')
        self.assertNotIn('used.dds',assets)
        with self.assertRaises(ValueError):artwork_files(a,assets)
    def test_removed_bytes_are_absent_after_save_and_reopen(self):
        from app import App
        from artwork import encode_nameplate_dds
        from PIL import Image
        a=item('keep.dds');b=item('remove.dds');data=encode_nameplate_dds(Image.new('RGBA',(512,48)))
        app=SimpleNamespace(docs=[a,b],assets={'keep.dds':data,'remove.dds':data,'old.dds':data},nameplate_layouts={},folders=[],current=1,dirty=False)
        remove_item(app,1);delete_files(app.docs,app.assets,unused_files(app.docs,app.assets))
        with tempfile.TemporaryDirectory() as d:
            path=str(Path(d)/'project.cvproject')
            with patch('app.filedialog.asksaveasfilename',return_value=path):App.save_project(app)
            saved=json.loads(Path(path).read_text());self.assertEqual(set(saved['assets']),{'keep.dds'})
            loaded=SimpleNamespace(scanning=False,may_discard=lambda:True,refresh=lambda:None,rescan=lambda:None)
            with patch('app.filedialog.askopenfilename',return_value=path):App.open_project(loaded)
            self.assertEqual(set(loaded.assets),{'keep.dds'});self.assertEqual(len(loaded.docs),1)

if __name__=='__main__':unittest.main()
