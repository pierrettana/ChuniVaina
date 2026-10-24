import copy,io,json,math,struct,tempfile,unittest,wave,zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from audio_repair import repair_bank,hca_info,save_repaired_zip,apply_project_pair,CHUNITHM_AUDIO_KEY
from cri_audio import read_utf,rewrite_utf,write_awb,require_hca_bank
from test_songs import reference
from core import parse,artwork_files,export_option
try:from cricodecs import hca
except ImportError:hca=None

def bank(stream):
    a,_=reference();root=read_utf(a);row=root['rows'][0]
    w,head=write_awb([stream]);headers=read_utf(row['StreamAwbAfs2Header']);headers['rows'][0]['Header']=head
    row['StreamAwbAfs2Header']=rewrite_utf(row['StreamAwbAfs2Header'],headers)
    return rewrite_utf(a,root),w

@unittest.skipIf(hca is None,'Install requirements.txt to test HCA cipher verification')
class AudioRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.streams={}
        for rate in (44100,48000):
            out=io.BytesIO()
            with wave.open(out,'wb') as f:
                f.setparams((2,2,rate,0,'NONE',''))
                f.writeframes(b''.join(struct.pack('<hh',int(8000*math.sin(i*.063)),int(6000*math.sin(i*.037))) for i in range(rate//4)))
            config=hca.HcaEncodeConfig();config.sample_rate=rate;config.channel_count=2;config.version=0x200;config.bitrate=192000;config.quality=hca.HcaQuality.HIGH
            cls.streams[rate]=hca.encode(out.getvalue(),config)
    def test_cipher_pcm_metadata_graph_and_idempotence(self):
        for rate,source in self.streams.items():
            with self.subTest(rate=rate):
                a,w=bank(source);new_a,new_w,report=repair_bank(a,w)
                root,streams=require_hca_bank(new_a,new_w);row=root['rows'][0]
                info=hca_info(streams[0][1]);self.assertEqual(info['cipher_type'],56)
                self.assertEqual(hca.decode(source),hca.decode(streams[0][1],keycode=CHUNITHM_AUDIO_KEY))
                wave_row=read_utf(row['WaveformTable'])['rows'][0]
                self.assertEqual(wave_row['SamplingRate'],rate);self.assertEqual(wave_row['NumSamples'],rate//4)
                self.assertEqual(read_utf(row['CueTable'])['rows'][0]['Length'],250)
                before=read_utf(a)['rows'][0]
                for key in ('SynthTable','TrackEventTable','CueNameTable','Name'):
                    self.assertEqual(before[key],row[key])
                twice_a,twice_w,twice_report=repair_bank(new_a,new_w)
                self.assertEqual((twice_a,twice_w),(new_a,new_w));self.assertFalse(twice_report['changed'])
                self.assertTrue(report['changed'])
    def test_damaged_stream_and_unsupported_cipher_fail(self):
        source=bytearray(self.streams[44100]);source[-8]^=1
        with self.assertRaisesRegex(ValueError,'checksum'):repair_bank(*bank(bytes(source)))
        source=bytearray(self.streams[44100]);source[44:46]=struct.pack('>H',1)
        with self.assertRaisesRegex(ValueError,'type 0'):repair_bank(*bank(bytes(source)))
    def test_existing_other_key_audio_is_not_double_encrypted(self):
        source=hca.encrypt(self.streams[44100],cipher_type=56,keycode=123456789)
        a,w=bank(source);new_a,new_w,report=repair_bank(a,w)
        self.assertEqual(new_w,w)
        self.assertEqual(require_hca_bank(new_a,new_w)[1][0][1],source)
        self.assertIn('not inferred',report['verification'])
    def test_music_cue_is_found_by_name_and_preview_is_preserved(self):
        a,w=bank(self.streams[44100]);root=read_utf(a);row=root['rows'][0]
        names=read_utf(row['CueNameTable']);names['rows'][0]['CueIndex']=1;names['rows'][1]['CueIndex']=0
        row['CueNameTable']=rewrite_utf(row['CueNameTable'],names)
        a=rewrite_utf(a,root);na,_,_=repair_bank(a,w)
        cues=read_utf(read_utf(na)['rows'][0]['CueTable'])['rows']
        self.assertEqual(cues[0]['Length'],1000);self.assertEqual(cues[1]['Length'],250)
    def test_multistream_bank_is_rejected(self):
        source=self.streams[44100];a,_=bank(source);root=read_utf(a);row=root['rows'][0]
        w,head=write_awb([source,source]);headers=read_utf(row['StreamAwbAfs2Header']);headers['rows'][0]['Header']=head
        row['StreamAwbAfs2Header']=rewrite_utf(row['StreamAwbAfs2Header'],headers)
        waves=read_utf(row['WaveformTable']);second=copy.deepcopy(waves['rows'][0]);second['StreamAwbId']=1;waves['rows'].append(second)
        row['WaveformTable']=rewrite_utf(row['WaveformTable'],waves)
        with self.assertRaisesRegex(ValueError,'one streaming HCA'):repair_bank(rewrite_utf(a,root),w)
    def test_bank_mismatch_and_nonzero_subkey_fail_before_commit(self):
        a,w=bank(self.streams[44100])
        wrong=bytearray(w);wrong[20]^=1
        with self.assertRaises(ValueError):repair_bank(a,bytes(wrong))
        # Keep the embedded streaming header matched, but reject the unsupported key derivation.
        root=read_utf(a);headers=read_utf(root['rows'][0]['StreamAwbAfs2Header'])
        header=bytearray(headers['rows'][0]['Header']);header[14]=1;headers['rows'][0]['Header']=bytes(header)
        root['rows'][0]['StreamAwbAfs2Header']=rewrite_utf(root['rows'][0]['StreamAwbAfs2Header'],headers)
        subkey=bytearray(w);subkey[14]=1
        with self.assertRaisesRegex(ValueError,'subkey'):repair_bank(rewrite_utf(a,root),bytes(subkey))
    def test_zip_copy_refuses_overwrite_and_keeps_inputs(self):
        a,w=bank(self.streams[44100]);na,nw,report=repair_bank(a,w)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixed.zip';save_repaired_zip(p,'music6700',na,nw,report)
            before=p.read_bytes()
            with self.assertRaises(FileExistsError):save_repaired_zip(p,'music6700',a,w,report)
            self.assertEqual(p.read_bytes(),before)
            with zipfile.ZipFile(p) as z:
                self.assertEqual(z.read('music6700.awb'),nw);self.assertTrue(json.loads(z.read('repair-report.json'))['changed'])
    def test_apply_save_export_and_shared_file_protection(self):
        from app import App
        a,w=bank(self.streams[44100]);na,nw,_=repair_bank(a,w)
        cue=parse(Path('templates/CueFile.xml').read_text());an=cue.findtext('acbFile/path');wn=cue.findtext('awbFile/path')
        fake=SimpleNamespace(docs=[cue],assets={an:a,wn:w},dirty=False,folders=[],nameplate_layouts={})
        other=copy.deepcopy(cue);fake.docs.append(other)
        with self.assertRaisesRegex(ValueError,'shared'):apply_project_pair(fake,cue,(na,nw))
        self.assertEqual(fake.assets,{an:a,wn:w});self.assertFalse(fake.dirty)
        fake.docs.pop();apply_project_pair(fake,cue,(na,nw));self.assertTrue(fake.dirty)
        with tempfile.TemporaryDirectory() as d:
            output=export_option(d,'A900',fake.docs,assets=fake.assets)
            self.assertEqual((output/'cueFile'/cue.findtext('dataName')/wn).read_bytes(),nw)
            p=str(Path(d)/'fixed.cvproject')
            with patch('app.filedialog.asksaveasfilename',return_value=p):App.save_project(fake)
            loaded=SimpleNamespace(scanning=False,may_discard=lambda:True,refresh=lambda:None,rescan=lambda:None)
            with patch('app.filedialog.askopenfilename',return_value=p):App.open_project(loaded)
            self.assertEqual(loaded.assets,fake.assets)

if __name__=='__main__':unittest.main()
