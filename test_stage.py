import copy
import io
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image
from artwork import decode, encode_world_dds
from core import parse, set_identity, configure_reward, reference_report, export_option, scan, artwork_files
from stage_model import afb_regions, textures, extract, replace_texture, encode_texture, apply_stage_assets


def chunk(tag, payload, header=32):
    head=bytearray(header);head[:4]=tag
    struct.pack_into('<II',head,4,len(payload),header)
    return bytes(head)+payload


def bundle(dds=b''):
    resources=chunk(b'AFRC',b'resource_names\x00'+dds)+chunk(b'POF0',b'\x00'*32)
    return chunk(b'FILS',chunk(b'FILE',resources),64)+b'trailer-preserve'


def small_dds(format='DXT5',mips=1):
    levels=[]
    header=None
    for i in range(mips):
        out=io.BytesIO()
        Image.new('RGBA',(max(1,16>>i),max(1,8>>i)),(20,70,100,255)).save(out,format='DDS',pixel_format=format)
        data=out.getvalue()
        if header is None:
            header=bytearray(data[:128]);struct.pack_into('<I',header,28,mips)
        levels.append(data[128:])
    return bytes(header)+b''.join(levels)


class StageTests(unittest.TestCase):
    def root(self): return parse(Path('templates/Stage.xml').read_text())

    def test_replacement_preserves_all_other_bytes_and_original_header(self):
        for format in ('DXT1','DXT3','DXT5'):
            with self.subTest(format=format):
                original=bundle(small_dds(format,3))
                texture=textures(original)[0]
                replacement=encode_texture(Image.new('RGBA',(16,8),(240,10,40,255)),texture)
                changed=replace_texture(original,texture,replacement)
                self.assertEqual(len(original),len(changed))
                self.assertEqual(original[:texture.offset+128],changed[:texture.offset+128])
                self.assertEqual(original[texture.offset+texture.length:],changed[texture.offset+texture.length:])
                self.assertNotEqual(original,changed)
                self.assertEqual(decode(extract(changed,texture)).size,(16,8))

    def test_rejects_invalid_containers_and_mismatched_dds(self):
        for invalid in (b'',b'not an afb',b'FILS'+b'\xff'*60):
            with self.assertRaises(ValueError): afb_regions(invalid)
        original=bundle(small_dds());texture=textures(original)[0]
        invalid=bytearray(extract(original,texture));struct.pack_into('<I',invalid,16,32)
        with self.assertRaises(ValueError): replace_texture(original,texture,bytes(invalid))
        with self.assertRaises(ValueError): replace_texture(original,texture,b'DDS ')
        truncated=original[:-200]
        with self.assertRaises(ValueError): textures(truncated)
        self.assertEqual(textures(bundle()),[])

    def test_assets_export_rewards_and_index(self):
        stage=self.root();set_identity(stage,90001,'Test stage')
        data=bundle(small_dds())
        assets={}
        apply_stage_assets(stage,[stage],assets,{'baseFile/path':data,'notesFieldFile/path':bundle()})
        self.assertEqual(stage.findtext('baseFile/path'),'st_90001.afb')
        assets[stage.findtext('image/path')]=encode_world_dds(Image.new('RGB',(960,450)))
        reward=parse(Path('templates/Reward.xml').read_text())
        substance=reward.find('substances/list/RewardSubstanceData')
        configure_reward(substance,stage)
        self.assertEqual(substance.findtext('type'),'13')
        self.assertEqual(substance.findtext('stage/stageName/id'),'90001')
        self.assertEqual(reference_report([stage,reward],{}),[])
        with tempfile.TemporaryDirectory() as parent:
            output=export_option(parent,'A901',[stage,reward],assets=assets)
            folder=output/'stage'/'stage090001'
            self.assertEqual((folder/'st_90001.afb').read_bytes(),data)
            self.assertTrue((folder/'nf_90001.afb').is_file())
            self.assertTrue((folder/'Stage.xml').is_file())
            index,errors=scan([output])
            self.assertEqual(errors,[]);self.assertIn(('StageData',90001),index)
        del assets['nf_90001.afb']
        with self.assertRaisesRegex(ValueError,'Missing attached stage bundle'): artwork_files(stage,assets)

    def test_optional_bundle_and_shared_filename_atomicity(self):
        stage=self.root();set_identity(stage,90001,'Custom')
        other=copy.deepcopy(stage);other.find('baseFile/path').text='st_90001.afb'
        assets={'st_90001.afb':bundle()};before=dict(assets)
        before_xml=copy.deepcopy(stage)
        with self.assertRaisesRegex(ValueError,'another stage'):
            apply_stage_assets(stage,[stage,other],assets,{'notesFieldFile/path':bundle(),'baseFile/path':bundle(small_dds())})
        self.assertEqual(assets,before)
        self.assertEqual(stage.findtext('notesFieldFile/path'),before_xml.findtext('notesFieldFile/path'))
        stage.find('objectFile/path').text='missing.afb'
        assets.update({stage.findtext('notesFieldFile/path'):bundle(),stage.findtext('baseFile/path'):bundle(),stage.findtext('image/path'):encode_world_dds(Image.new('RGB',(4,4)))})
        with self.assertRaisesRegex(ValueError,'missing.afb'): artwork_files(stage,assets)

    def test_actual_project_save_open_keeps_afb_and_legacy_dds(self):
        from app import App
        root=self.root()
        assets={'st_test.afb':bundle(small_dds()),'preview.dds':encode_world_dds(Image.new('RGB',(8,8)))}
        fake=SimpleNamespace(docs=[root],folders=[],assets=assets,nameplate_layouts={},dirty=True)
        with tempfile.TemporaryDirectory() as parent:
            file=str(Path(parent)/'stage.cvproject')
            with patch('app.filedialog.asksaveasfilename',return_value=file):App.save_project(fake)
            loaded=SimpleNamespace(scanning=False,may_discard=lambda:True,refresh=lambda:None,rescan=lambda:None)
            with patch('app.filedialog.askopenfilename',return_value=file):App.open_project(loaded)
            self.assertEqual(loaded.assets,assets)
            self.assertEqual(loaded.docs[0].tag,'StageData')

    def test_actual_import_attaches_sibling_assets(self):
        from app import App
        from core import serialize
        root=self.root()
        assets={root.findtext('baseFile/path'):bundle(small_dds()),root.findtext('notesFieldFile/path'):bundle(),root.findtext('image/path'):encode_world_dds(Image.new('RGB',(8,8)))}
        fake=SimpleNamespace(docs=[],assets={},refresh=lambda:None)
        fake.store_asset=lambda name,data:App.store_asset(fake,name,data)
        with tempfile.TemporaryDirectory() as parent:
            file=Path(parent)/'Stage.xml';file.write_text(serialize(root))
            for name,data in assets.items():(Path(parent)/name).write_bytes(data)
            with patch('app.filedialog.askopenfilenames',return_value=[str(file)]):App.import_xml(fake)
        self.assertEqual(fake.assets,assets)
        self.assertEqual(len(fake.docs),1)


if __name__=='__main__': unittest.main()
