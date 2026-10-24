import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image
from plate_model import blank,starter,layer,image_layer,render,validate_layout,History,hit_test
from artwork import encode_nameplate_dds,decode
from core import parse,export_option,dds_info

class LayeredPlateTests(unittest.TestCase):
    def test_starter_and_portable_roundtrip(self):
        document=starter();document['layers'].append(image_layer(Image.new('RGBA',(40,40),(255,0,0,120)),'Imported'))
        restored=validate_layout(json.loads(json.dumps(document)))
        self.assertEqual(render(restored).tobytes(),render(document).tobytes())
        self.assertEqual(render(restored).size,(576,228))
    def test_alpha_order_visibility_and_hit_testing(self):
        document=blank();bottom=layer('shape','Bottom',width=30,height=30,color='#FF0000')
        top=layer('shape','Top',width=30,height=30,color='#0000FF',opacity=50)
        document['layers']=[bottom,top]
        self.assertEqual(render(document).getpixel((10,10)),(127,0,128,255))
        self.assertEqual(hit_test(document,10,10),top['id'])
        top['locked']=True;self.assertEqual(hit_test(document,10,10),bottom['id'])
        top['visible']=False;self.assertEqual(render(document).getpixel((10,10)),(255,0,0,255))
    def test_transform_clipping_and_source_preservation(self):
        image=Image.new('RGBA',(20,10),(0,255,0,255));item=image_layer(image)
        document=blank();document['layers']=[item];original=item['source']
        item.update(x=-5,y=-5,width=40,height=20,rotation=90,flip_x=True)
        output=render(document)
        self.assertEqual(item['source'],original);self.assertEqual(output.size,(576,228))
        self.assertEqual(output.getpixel((575,227))[3],0)
    def test_undo_redo_and_redo_invalidation(self):
        history=History(blank());history.checkpoint();history.document=starter()
        history.undo();self.assertEqual(history.document['layers'],[])
        history.redo();self.assertEqual(len(history.document['layers']),6)
        history.undo();history.checkpoint();self.assertEqual(history.redo_stack,[])
    def test_invalid_layers_rejected(self):
        document=starter();document['layers'][0]['width']=0
        with self.assertRaises(ValueError):validate_layout(document)
        document=starter();document['layers'][0]['x']=float('nan')
        with self.assertRaises(ValueError):validate_layout(document)
        document=starter();document['layers'][0]['color']='bad'
        with self.assertRaises(ValueError):validate_layout(document)
    def test_composition_dds_export(self):
        image=render(starter());data=encode_nameplate_dds(image)
        self.assertEqual(dds_info(data),(576,228,1));self.assertEqual(data[84:88],b'DXT5');self.assertEqual(decode(data).size,image.size)
        root=parse(Path('templates/NamePlate.xml').read_text());name=root.findtext('image/path')
        with tempfile.TemporaryDirectory() as parent:
            output=export_option(parent,'A900',[root],assets={name:data})
            self.assertEqual((output/'namePlate'/root.findtext('dataName')/name).read_bytes(),data)
    def test_actual_project_save_open_retains_layers(self):
        from app import App
        root=parse(Path('templates/NamePlate.xml').read_text());document=starter()
        document['layers'].append(image_layer(Image.new('RGBA',(2,2),(12,34,56,78))))
        fake=SimpleNamespace(docs=[root],folders=[],assets={},nameplate_layouts={id(root):document},dirty=True)
        with tempfile.TemporaryDirectory() as parent:
            file=str(Path(parent)/'layers.cvproject')
            with patch('app.filedialog.asksaveasfilename',return_value=file):App.save_project(fake)
            loaded=SimpleNamespace(scanning=False,may_discard=lambda:True,refresh=lambda:None,rescan=lambda:None)
            with patch('app.filedialog.askopenfilename',return_value=file):App.open_project(loaded)
            restored=loaded.nameplate_layouts[id(loaded.docs[0])]
            self.assertEqual(render(restored).tobytes(),render(document).tobytes())
            self.assertEqual(len(restored['layers']),7)

if __name__=='__main__':unittest.main()
