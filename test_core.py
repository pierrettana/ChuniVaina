import tempfile
import unittest
from pathlib import Path
from core import *

class ModelTests(unittest.TestCase):
    def test_all_reference_roundtrips(self):
        for p in Path('templates').glob('*.xml'):
            root=parse(p.read_text(encoding='utf-8-sig'))
            again=parse(serialize(root))
            self.assertEqual(ET.tostring(root), ET.tostring(again))
            validate(again)
    def test_identity_preserves_references(self):
        r=parse(Path('templates/Chara.xml').read_text())
        old=r.findtext('defaultImages/id')
        set_identity(r,99999,'Quincy & friends')
        validate(r)
        self.assertEqual(r.findtext('dataName'),'chara099999')
        self.assertEqual(r.findtext('defaultImages/id'),old)
        self.assertEqual(parse(serialize(r)).findtext('name/str'),'Quincy & friends')
    def test_index_definitions_namespaces_and_overlap(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            for kind,(_,_,file,_) in KINDS.items():
                r=parse((Path('templates')/file).read_text())
                set_identity(r,123,'Test')
                (d/file).write_text(serialize(r))
            (d/'broken.xml').write_text('<CharaData>')
            index,errors=scan([d,d])
            self.assertEqual(len(index),len(KINDS))
            self.assertTrue(all(len(v)==1 for v in index.values()))
            self.assertEqual(len(errors),1)
            self.assertNotIn(('CharaData',14),index)
    def test_export_shape(self):
        r=parse(Path('templates/Quest.xml').read_text())
        self.assertEqual(str(export_path('/tmp/export',r)),'/tmp/export/quest00001210/Quest.xml')
    def test_entity_rejected(self):
        with self.assertRaises(ValueError): parse('<!DOCTYPE x><CharaData/>')

class OptionExportTests(unittest.TestCase):
    def test_layout_and_safety(self):
        docs=[parse((Path('templates')/spec[2]).read_text()) for kind,spec in KINDS.items() if not asset_slots(ET.Element(kind)) and not binary_slots(ET.Element(kind))]
        with tempfile.TemporaryDirectory() as parent:
            out=export_option(parent,'A900',docs,(2,50,1))
            self.assertIn('VerMinor   = 50',(out/'data.conf').read_text())
            for root in docs:
                spec=KINDS[root.tag]
                target=out/spec[1]/root.findtext('dataName')/spec[2]
                self.assertEqual(identity(parse(target.read_text())),identity(root))
            with self.assertRaises(ValueError): export_option(parent,'A900',docs)
            with self.assertRaises(ValueError): export_option(parent,'../A901',docs)
            with self.assertRaises(ValueError): export_option(parent,'A901',[docs[0],docs[0]])
            self.assertFalse((Path(parent)/'A901').exists())

class ArtworkTests(unittest.TestCase):
    def test_artwork_export_and_missing_files(self):
        import struct
        root=parse(Path('templates/DDSImage.xml').read_text())
        assets={}
        for slot,size in enumerate((1080,512,128)):
            header=bytearray(128); header[:4]=b'DDS '
            struct.pack_into('<I',header,4,124)
            struct.pack_into('<II',header,12,size,size)
            name=root.findtext(f'ddsFile{slot}/path')
            assets[name]=bytes(header)
            self.assertEqual(dds_info(header)[:2],(size,size))
        with tempfile.TemporaryDirectory() as parent:
            with self.assertRaises(ValueError): export_option(parent,'A900',[root])
            out=export_option(parent,'A900',[root],assets=assets)
            for name,data in assets.items(): self.assertEqual((out/'ddsImage'/root.findtext('dataName')/name).read_bytes(),data)
        root.find('ddsFile0/path').text='../bad.dds'
        with self.assertRaises(ValueError): artwork_files(root,assets)

class RewardTests(unittest.TestCase):
    def test_trophy_reward_and_quest_link(self):
        reward=parse(Path('templates/Reward.xml').read_text())
        trophy=parse(Path('templates/Trophy.xml').read_text())
        quest=parse(Path('templates/Quest.xml').read_text())
        substance=reward.find('substances/list/RewardSubstanceData')
        configure_reward(substance,trophy)
        self.assertEqual(substance.findtext('type'),'2')
        self.assertEqual(substance.findtext('trophy/trophyName/id'),trophy.findtext('name/id'))
        milestone=quest.find('info/QuestRewardDataInfo')
        add_quest_reward(milestone,reward)
        self.assertEqual(milestone.findall('rewardName/list/StringID')[-1].findtext('id'),reward.findtext('name/id'))
        with self.assertRaises(ValueError): add_quest_reward(milestone,reward)
        validate(reward)
        self.assertEqual(reward.findtext('dataName'),'reward010000500')

class ConversionTests(unittest.TestCase):
    def test_alpha_mipmaps_and_format(self):
        import struct
        from PIL import Image
        from artwork import encode_dds, decode
        image=Image.new('RGBA',(128,128),(21,43,65,97))
        data=encode_dds(image)
        self.assertEqual(decode(data).tobytes(),image.tobytes())
        self.assertEqual(dds_info(data),(128,128,8))
        self.assertEqual(struct.unpack_from('<8I',data,76),(32,65,0,32,16711680,65280,255,4278190080))
        self.assertEqual(len(data),128+sum(max(1,128>>i)**2*4 for i in range(8)))
    def test_framing_and_transparent_padding(self):
        from PIL import Image
        from artwork import compose
        image=Image.new('RGBA',(200,100),(255,0,0,255))
        fit=compose(image,128,'Fit')
        self.assertEqual(fit.getpixel((64,0))[3],0)
        self.assertEqual(fit.getpixel((64,64)),(255,0,0,255))
        crop=compose(image,128,'Crop')
        self.assertEqual(crop.getextrema()[3],(255,255))
        top=compose(image,128,'Fit',1,.5,0)
        self.assertEqual(top.getpixel((64,0))[3],255)

class WorldTests(unittest.TestCase):
    def test_map_area_structure(self):
        area=parse(Path('templates/MapArea.xml').read_text())
        validate(area)
        area.find('grids').append(copy.deepcopy(area.find('grids/MapAreaGridData')))
        with self.assertRaises(ValueError): validate(area)
        world=parse(Path('templates/Map.xml').read_text())
        world.find('infos').append(copy.deepcopy(world.find('infos/MapDataAreaInfo')))
        with self.assertRaises(ValueError): validate(world)
    def test_reference_report_tracks_map_chain(self):
        world=parse(Path('templates/Map.xml').read_text())
        area=parse(Path('templates/MapArea.xml').read_text())
        before=reference_report([world],{})
        self.assertTrue(any('Map area 2305301' in x for x in before))
        after=reference_report([world,area],{})
        self.assertFalse(any('mapAreaName → Map area 2305301 ' in x for x in after))
        event=parse(Path('templates/Event.xml').read_text())
        event.find('substances/map/mapName/id').text='2006640'
        self.assertTrue(any('announcement' in x for x in reference_report([event],{})))
    def test_assets_roundtrip_and_world_layout(self):
        import struct
        from PIL import Image
        from artwork import encode_world_dds,compose,decode
        docs=[parse((Path('templates')/file).read_text()) for file in ('Map.xml','MapArea.xml','MapBonus.xml','DDSMap.xml','Event.xml')]
        assets={}
        for root in docs:
            for path,required,size in asset_slots(root):
                image=compose(Image.new('RGBA',(32,24),(140,90,180,255)),size,'Crop')
                data=encode_world_dds(image)
                self.assertEqual(data[84:88],b'DXT1')
                self.assertEqual(dds_info(data),(size[0],size[1],1))
                self.assertEqual(decode(data).size,size)
                self.assertEqual(len(data),128+((size[0]+3)//4)*((size[1]+3)//4)*8)
                assets[root.findtext(path)]=data
        with tempfile.TemporaryDirectory() as parent:
            with self.assertRaises(ValueError): export_option(parent,'A900',docs)
            out=export_option(parent,'A900',docs,assets=assets)
            for root in docs:
                _,folder,filename,_=KINDS[root.tag]
                base=out/folder/root.findtext('dataName')
                self.assertTrue((base/filename).is_file())
                for path,_,_ in asset_slots(root):
                    name=root.findtext(path)
                    self.assertEqual((base/name).read_bytes(),assets[name])
    def test_event_image_optional_when_empty(self):
        event=parse(Path('templates/Event.xml').read_text())
        event.find('substances/information/image/path').text=''
        self.assertEqual(artwork_files(event,{}),[])

class ActivationUnlockTests(unittest.TestCase):
    def load(self,name): return parse((Path('templates')/name).read_text())
    def test_activation_templates_and_targets(self):
        event=self.load('Event-map.xml'); target=self.load('Map.xml')
        self.assertEqual(event.findtext('substances/type'),'2')
        configure_activation(event,target);validate(event)
        self.assertEqual(event.findtext('substances/map/mapName/id'),target.findtext('name/id'))
        event=self.load('Event-quest.xml');target=self.load('Quest.xml')
        event.find('substances/quest/questNames/list').clear()
        with self.assertRaises(ValueError):validate(event)
        configure_activation(event,target);configure_activation(event,target)
        self.assertEqual(len(event.findall('substances/quest/questNames/list/StringID')),1)
        self.assertEqual(event.findtext('substances/type'),'8');validate(event)
        with self.assertRaises(ValueError):configure_activation(event,self.load('Map.xml'))
    def test_unlock_warning_and_valid_map_completion(self):
        chara=self.load('Chara.xml');reward=self.load('Reward.xml');world=self.load('Map.xml')
        self.assertEqual(len(character_unlock_warnings([chara])),1)
        configure_reward(reward.find('substances/list/RewardSubstanceData'),chara)
        self.assertIn('reward exists',character_unlock_warnings([chara,reward])[0])
        set_reference(world.find('infos/MapDataAreaInfo/rewardName'),reward)
        self.assertEqual(character_unlock_warnings([chara,reward,world]),[])
        chara.find('defaultHave').text='true'
        self.assertEqual(character_unlock_warnings([chara]),[])
    def test_conditions_and_unlinked_area_do_not_grant(self):
        chara=self.load('Chara.xml');reward=self.load('Reward.xml');quest=self.load('Quest.xml');area=self.load('MapArea.xml');world=self.load('Map.xml')
        # A quest key condition is not a character grant.
        set_reference(quest.find('info/QuestRewardDataInfo/keyCharaName'),chara)
        self.assertEqual(len(character_unlock_warnings([chara,quest])),1)
        configure_reward(reward.find('substances/list/RewardSubstanceData'),chara)
        set_reference(area.findall('grids/MapAreaGridData')[1].find('reward/rewardName'),reward)
        self.assertEqual(len(character_unlock_warnings([chara,reward,area])),1)
        self.assertEqual(character_unlock_warnings([chara,reward,area,world]),[])
    def test_quest_and_imported_unlocks(self):
        chara=self.load('Chara.xml');reward=self.load('Reward.xml');quest=self.load('Quest.xml')
        configure_reward(reward.find('substances/list/RewardSubstanceData'),chara)
        add_quest_reward(quest.find('info/QuestRewardDataInfo'),reward)
        self.assertEqual(character_unlock_warnings([chara], [reward,quest]),[])
        # Editing a project definition overrides the source copy.
        changed=copy.deepcopy(reward);changed.find('substances/list/RewardSubstanceData/type').text='0'
        self.assertEqual(len(character_unlock_warnings([chara,changed],[reward,quest])),1)
    def test_scan_collects_unlock_definitions(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.load('Reward.xml');Path(d,'Reward.xml').write_text(serialize(root))
            definitions=[];index,errors=scan([d],definitions)
            self.assertFalse(errors);self.assertEqual(len(definitions),1)
            self.assertEqual(identity(definitions[0]),identity(root))

class HelpTests(unittest.TestCase):
    def test_types_are_context_specific(self):
        from helptext import describe_field
        event=parse(Path('templates/Event-quest.xml').read_text())
        self.assertIn('Quest opening',describe_field(event,event.find('substances/type')))
        reward=parse(Path('templates/Reward.xml').read_text())
        node=reward.find('substances/list/RewardSubstanceData/type');node.text='8'
        self.assertIn('Unverified',describe_field(reward,node))
        self.assertNotIn('Quest opening',describe_field(reward,node))
    def test_uncertainty_and_ownership_guidance(self):
        from helptext import describe_field,TYPE_HELP
        quest=parse(Path('templates/Quest.xml').read_text())
        self.assertIn('not been confirmed',describe_field(quest,quest.find('info/QuestRewardDataInfo/sumRank')))
        chara=parse(Path('templates/Chara.xml').read_text())
        self.assertIn('unlock',describe_field(chara,chara.find('defaultHave')))
        self.assertEqual(set(TYPE_HELP),set(KINDS))

class NameplateSongTests(unittest.TestCase):
    def test_nameplate_conversion_grant_and_export(self):
        from PIL import Image
        from artwork import encode_nameplate_dds,decode,generated_name
        plate=parse(Path('templates/NamePlate.xml').read_text())
        set_identity(plate,12345,'Custom plate');validate(plate)
        data=encode_nameplate_dds(Image.new('RGBA',(576,228),(240,40,70,128)))
        self.assertEqual(dds_info(data),(576,228,1));self.assertEqual(data[84:88],b'DXT5')
        decoded=decode(data)
        self.assertLessEqual(abs(decoded.getpixel((200,100))[3]-128),2)
        self.assertEqual(len(data),128+144*57*16)
        name=generated_name(plate,0);self.assertEqual(name,'CHU_UI_NamePlate_00012345.dds')
        plate.find('image/path').text=name
        reward=parse(Path('templates/Reward.xml').read_text())
        substance=reward.find('substances/list/RewardSubstanceData');configure_reward(substance,plate)
        self.assertEqual(substance.findtext('type'),'5');self.assertEqual(substance.findtext('namePlate/namePlateName/id'),'12345')
        with tempfile.TemporaryDirectory() as parent:
            out=export_option(parent,'A900',[plate,reward],assets={name:data})
            base=out/'namePlate'/'namePlate00012345'
            self.assertTrue((base/'NamePlate.xml').is_file());self.assertEqual((base/name).read_bytes(),data)
    def test_song_scanning_metadata_search_and_clear(self):
        music='<MusicData><name><id>3057</id><str>Your Reality (Kenji Mizuno Remix)</str></name><artistName><id>1</id><str>Dan Salvato／水野健治</str></artistName><fumens><file>keep-out.c2s</file></fumens></MusicData>'
        with tempfile.TemporaryDirectory() as parent:
            Path(parent,'Music.xml').write_text(music)
            definitions=[];index,errors=scan([parent],definitions)
            self.assertFalse(errors);self.assertIn(('MusicData',3057),index)
            self.assertIsNone(definitions[0].find('fumens'))
            catalog=song_catalog(definitions,index)
            self.assertEqual(len(search_songs(catalog,'reality Dan')),1)
            self.assertEqual(len(search_songs(catalog,'3057')),1)
            self.assertEqual(search_songs(catalog,'unrelated'),[])
            self.assertEqual(parse(music).tag,'MusicData')
            row=parse(Path('templates/Map.xml').read_text()).find('infos/MapDataAreaInfo')
            old=row.findtext('rewardName/id')
            set_task_track(row,catalog[0]);self.assertEqual(row.findtext('musicName/id'),'3057')
            self.assertEqual(row.findtext('rewardName/id'),old)
            set_task_track(row);self.assertEqual(row.findtext('musicName/id'),'-1');self.assertEqual(row.findtext('musicName/str'),'Invalid')

if __name__=='__main__': unittest.main()
