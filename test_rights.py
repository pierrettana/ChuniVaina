import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core import parse,set_identity,serialize,scan,export_option,configure_activation,reference_report,validate
from rights_model import render_text,apply_artwork,default_font_path
from artwork import decode
from song_notice import load_preferences,save_notice_preference

def template():return parse(Path('templates/RightsInfo.xml').read_text())

class RightsTests(unittest.TestCase):
    def test_render_compress_export_and_index(self):
        r=template();set_identity(r,6700,'Example credits')
        im,used=render_text('© Example artist\nMusic credits',default_font_path(),18,'center')
        assets={};name=apply_artwork(r,assets,[r],'© Example artist\nMusic credits',im)
        self.assertEqual(name,'CHU_UI_Rights_6700.dds')
        self.assertEqual(assets[name][84:88],b'DXT5');self.assertEqual(len(assets[name]),24704)
        decoded=decode(assets[name]);self.assertEqual(decoded.size,(512,48))
        self.assertEqual(decoded.getchannel('A').getextrema(),(0,255))
        with tempfile.TemporaryDirectory() as d:
            out=export_option(d,'A900',[r],assets=assets)
            xml=out/'rightsInfo/rightsInfo006700/RightsInfo.xml'
            self.assertEqual(parse(xml.read_text()).findtext('rightsText'),'© Example artist\nMusic credits')
            self.assertEqual((xml.parent/name).read_bytes(),assets[name])
            index,errors=scan([out]);self.assertFalse(errors);self.assertIn(('RightsInfoData',6700),index)
    def test_fit_alignment_and_overflow(self):
        for align in ('left','center','right'):
            image,used=render_text('© Credit',default_font_path(),18,align)
            box=image.getchannel('A').getbbox();self.assertGreaterEqual(box[0],4);self.assertLessEqual(box[2],508)
            if align=='left':self.assertLessEqual(box[0],8)
            if align=='right':self.assertGreaterEqual(box[2],504)
        _,size=render_text('A moderately long credit that must fit in the rights image',default_font_path(),48)
        self.assertLess(size,48)
        for text,size in [('',20),('X'*500,40),('A',0)]:
            with self.assertRaises(ValueError):render_text(text,default_font_path(),size,fit=False)
    def test_missing_and_wrong_size_artwork_blocks_export(self):
        from artwork import encode_nameplate_dds
        from PIL import Image
        r=template();name=r.findtext('image/path')
        with tempfile.TemporaryDirectory() as d:
            for assets in ({},{name:encode_nameplate_dds(Image.new('RGBA',(576,228)))}):
                with self.assertRaises(ValueError):export_option(d,'A900',[r],assets=assets)
                self.assertFalse((Path(d)/'A900').exists())
    def test_type_11_multiple_targets_and_reference_checks(self):
        event=parse(Path('templates/Event-rights.xml').read_text())
        event.find('substances/rightsInfo/rightsNames/list').clear()
        with self.assertRaises(ValueError):validate(event)
        first=template();second=copy.deepcopy(first);set_identity(second,6701,'Other credit')
        for target in (first,second,first):configure_activation(event,target)
        refs=event.findall('substances/rightsInfo/rightsNames/list/StringID')
        self.assertEqual([r.findtext('id') for r in refs],['9000','6701']);validate(event)
        self.assertFalse(reference_report([event,first,second],{}))
        self.assertTrue(reference_report([event,first],{}))
    def test_shared_filename_is_not_overwritten(self):
        a=template();b=copy.deepcopy(a);image,_=render_text('Credit')
        assets={};name=apply_artwork(a,assets,[a],'Credit',image);b.find('image/path').text=name
        before=dict(assets);other,_=render_text('Different')
        with self.assertRaises(ValueError):apply_artwork(a,assets,[a,b],'Different',other)
        self.assertEqual(assets,before);self.assertEqual(a.findtext('rightsText'),'Credit')
    def test_project_roundtrip_retains_rights_text_and_dds(self):
        from app import App
        r=template();assets={};im,_=render_text('© A & B');apply_artwork(r,assets,[r],'© A & B',im)
        fake=SimpleNamespace(docs=[r],assets=assets,folders=[],nameplate_layouts={},dirty=True)
        with tempfile.TemporaryDirectory() as d:
            file=str(Path(d)/'rights.cvproject')
            with patch('app.filedialog.asksaveasfilename',return_value=file):App.save_project(fake)
            loaded=SimpleNamespace(scanning=False,may_discard=lambda:True,refresh=lambda:None,rescan=lambda:None)
            with patch('app.filedialog.askopenfilename',return_value=file):App.open_project(loaded)
            self.assertEqual(loaded.assets,assets);self.assertEqual(serialize(loaded.docs[0]),serialize(r))

class NoticeTests(unittest.TestCase):
    def test_persistence_and_existing_settings(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'nested/preferences.json'
            self.assertEqual(load_preferences(p),{})
            save_notice_preference(True,p);self.assertTrue(load_preferences(p)['hide_song_audio_notice'])
            p.write_text('{"other_setting":123,"hide_song_audio_notice":true}')
            save_notice_preference(False,p)
            self.assertEqual(load_preferences(p),{'other_setting':123,'hide_song_audio_notice':False})
            p.write_text('broken');self.assertEqual(load_preferences(p),{})
            save_notice_preference(True,p);self.assertTrue(load_preferences(p)['hide_song_audio_notice'])
    def test_hidden_notice_returns_without_gui(self):
        from song_notice import show_notice
        with patch('song_notice.load_preferences',return_value={'hide_song_audio_notice':True}):
            show_notice(object())

if __name__=='__main__':unittest.main()
