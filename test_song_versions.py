import copy
import tempfile
import unittest
from pathlib import Path
from core import parse,serialize,scan,export_option
from song_versions import version_options,set_song_version
from song_model import build_song
from test_songs import HEADER,reference
from artwork import encode_world_dds
from PIL import Image

def song():return parse(Path('templates/Music.xml').read_text())

class SongVersionTests(unittest.TestCase):
    def test_scan_collects_versions_without_changing_song_catalog(self):
        r=song();r.find('releaseTagName/id').text='777';r.find('releaseTagName/str').text='Future custom release'
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'Music.xml').write_text(serialize(r))
            definitions=[];index,errors=scan([d],definitions)
        self.assertFalse(errors);self.assertEqual(len(definitions),1)
        self.assertEqual(definitions[0].findtext('releaseTagName/id'),'777')
        options=version_options(definitions+[r],song())
        self.assertEqual([x.findtext('id') for x in options],['21','777'])
        options[-1].find('str').text='Edited in dialog'
        self.assertEqual(r.findtext('releaseTagName/str'),'Future custom release')
    def test_build_export_keeps_version_and_default_or_special_stage(self):
        template=song();release=copy.deepcopy(template.find('releaseTagName'))
        release.find('id').text='777';release.find('str').text='Exact source version'
        release.find('data').text='retained metadata'
        for stage in (-1,28501):
            with self.subTest(stage=stage):
                root,cue,assets,_=build_song(template,parse(Path('templates/CueFile.xml').read_text()),6700,'Song','Artist',
                    {3:HEADER+"#1'0:t04\n"},encode_world_dds(Image.new('RGB',(300,300))),reference(),stage,0,release)
                self.assertEqual(root.findtext('releaseTagName/id'),'777')
                self.assertEqual(root.findtext('releaseTagName/str'),'Exact source version')
                self.assertEqual(root.findtext('releaseTagName/data'),'retained metadata')
                self.assertEqual(root.findtext('stageName/id'),str(stage))
                self.assertEqual(root.findtext('netOpenName/id'),template.findtext('netOpenName/id'))
                with tempfile.TemporaryDirectory() as d:
                    out=export_option(d,'A900',[root,cue],assets=assets)
                    saved=parse((out/'music/music6700/Music.xml').read_text())
                    self.assertEqual(saved.findtext('releaseTagName/id'),'777')
                    self.assertEqual(saved.findtext('stageName/id'),str(stage))
                self.assertEqual(template.findtext('releaseTagName/id'),'21')
    def test_keep_current_and_invalid_selection(self):
        root=song();before=serialize(root);set_song_version(root,None)
        self.assertEqual(serialize(root),before)
        tag=copy.deepcopy(root.find('releaseTagName'));tag.find('id').text='-1'
        with self.assertRaises(ValueError):set_song_version(root,tag)
        self.assertEqual(serialize(root),before)

if __name__=='__main__':unittest.main()
