import tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from core import parse,export_option,scan,reference_report,identity,serialize
from quick_trophy import build_trophies

def templates():
    return {d:parse(Path('templates',f'Trophy-AJ-{label}.xml').read_text()) for d,label in ((2,'expert'),(3,'master'))}

class QuickTrophyTests(unittest.TestCase):
    def test_separate_expert_master_conditions_and_rarity(self):
        source=templates();before={d:serialize(r) for d,r in source.items()}
        result=build_trophies(source,(6700,'エロティック','リリイ・シュシュ'),[(2,9001,'Expert & title'),(3,9002,'Master title')])
        for root,diff,rare in zip(result,(2,3),('4','6')):
            self.assertEqual(root.findtext('rareType'),rare);self.assertEqual(root.findtext('defaultHave'),'false')
            conditions=root.findall('normCondition/conditions/ConditionSubData')
            self.assertEqual([c.findtext('type') for c in conditions],['1','3'])
            self.assertEqual(conditions[0].findtext('playMusicData/musicDif/id'),str(diff))
            self.assertEqual(conditions[0].findtext('playMusicData/musicNames/list/StringID/id'),'6700')
            self.assertEqual(conditions[1].findtext('playMusicResultData/allJustice'),'true')
            self.assertEqual(conditions[1].findtext('playMusicResultData/scoreRank/id'),'-1')
            self.assertIn('/ALL JUSTICE達成',root.findtext('explainText'))
        self.assertEqual({d:serialize(r) for d,r in source.items()},before)
    def test_invalid_batch_does_not_mutate_templates(self):
        source=templates();before={d:serialize(r) for d,r in source.items()}
        for entries in ([],[(2,1,'')],[(0,1,'bad difficulty')],[(2,1,'A'),(3,1,'B')],[(2,1,'A'),(2,2,'B')]):
            with self.assertRaises(ValueError):build_trophies(source,(6700,'Song','Artist'),entries)
        self.assertEqual({d:serialize(r) for d,r in source.items()},before)
    def test_export_rescan_and_song_reference_reporting(self):
        result=build_trophies(templates(),(6700,'Song','Artist'),[(3,9002,'Master')])
        with tempfile.TemporaryDirectory() as d:
            out=export_option(d,'A900',result)
            xml=out/'trophy/trophy009002/Trophy.xml';self.assertTrue(xml.is_file())
            self.assertEqual(parse(xml.read_text()).findtext('name/str'),'Master')
            index,errors=scan([out]);self.assertFalse(errors);self.assertIn(('TrophyData',9002),index)
            self.assertFalse((out/'reward').exists())
        self.assertTrue(any('Song 6700' in issue for issue in reference_report(result,{})))
        self.assertFalse(reference_report(result,{('MusicData',6700):[('Song','external/Music.xml')]}))
    def test_project_save_open_keeps_both_trophies(self):
        from app import App
        docs=build_trophies(templates(),(6700,'Song','Artist'),[(2,9001,'A'),(3,9002,'B')])
        fake=SimpleNamespace(docs=docs,folders=[],assets={},nameplate_layouts={},dirty=True)
        with tempfile.TemporaryDirectory() as d:
            path=str(Path(d)/'trophies.cvproject')
            with patch('app.filedialog.asksaveasfilename',return_value=path):App.save_project(fake)
            loaded=SimpleNamespace(scanning=False,may_discard=lambda:True,refresh=lambda:None,rescan=lambda:None)
            with patch('app.filedialog.askopenfilename',return_value=path):App.open_project(loaded)
            self.assertEqual([serialize(r) for r in loaded.docs],[serialize(r) for r in docs])

if __name__=='__main__':unittest.main()
