import tempfile
import unittest
from pathlib import Path
from core import parse, export_option, identity
from cv_workflow import make_character

BASE=Path(__file__).parent

class WorkflowTests(unittest.TestCase):
    def test_optional_configuration_preserves_identical_content(self):
        root=parse((BASE/'templates/CharaWorks.xml').read_text())
        with tempfile.TemporaryDirectory() as directory:
            without=export_option(directory,'A900',[root])
            with_conf=export_option(directory,'A901',[root],version=(2,51,3))
            self.assertFalse((without/'data.conf').exists())
            self.assertEqual((with_conf/'data.conf').read_text(),'[Version]\nName = CHUNITHM\nVerMajor   = 2\nVerMinor   = 51\nVerRelease = 3\n')
            for file in without.rglob('*'):
                if file.is_file():self.assertEqual(file.read_bytes(),(with_conf/file.relative_to(without)).read_bytes())
            for version in ((1,2),(-1,0,0),(True,1,0),('2',50,1)):
                with self.assertRaises(ValueError):export_option(directory,'A902',[root],version=version)
                self.assertFalse((Path(directory)/'A902').exists())

    def test_character_and_artwork_links(self):
        for available in (True,False):
            char,art=make_character(BASE,'900001','Example',('201','Example category'),available,'900002')
            self.assertEqual(identity(char),('CharaData',900001))
            self.assertEqual(char.findtext('defaultImages/id'),art.findtext('name/id'))
            self.assertEqual(char.findtext('defaultImages/str'),art.findtext('name/str'))
            self.assertEqual(char.findtext('works/id'),'201')
            self.assertEqual(char.findtext('defaultHave'),str(available).lower())
            self.assertTrue(all(not art.findtext(f'ddsFile{i}/path') for i in range(3)))
        with self.assertRaises(ValueError):make_character(BASE,'900001',' ',('201','Category'),True,'900002')
