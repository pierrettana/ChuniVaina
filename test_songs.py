import unittest,tempfile,struct,io,wave,math,shutil,subprocess
from pathlib import Path
from fractions import Fraction
from chart_converter import parse_ugc,convert,ConversionError
from cri_audio import read_utf,write_utf,write_awb,read_awb,validate_bank
from song_model import build_song,validate_c2s
from core import parse,serialize,export_option,scan,song_catalog

HEADER="""@VER\t8
@TITLE\tTest & Song
@ARTIST\tArtist
@DESIGN\tDesigner
@DIFF\t3
@CONST\t12.4
@TICKS\t480
@BEAT\t0\t4\t4
@BPM\t0'0\t120
@TIL\t0\t0'0\t7
@FLAG\tSOFFSET\tFALSE
@BGMOFS\t0
@ENDHEAD
"""
BODY="""#1'1:t04
#1'1:a04UCN
#1'480:s84
#480>cA4
#960>sC4
#1'1440:S C4
"""

def table(name,columns,rows):return write_utf({'name':name,'columns':columns,'rows':rows,'version':1})
def reference():
    hca_header=bytearray(96);hca_header[:4]=b'HCA\0';hca_header[24:28]=b'comp'
    hca_header[28:40]=bytes.fromhex('0200010f0100804040000000')
    awb,head=write_awb([bytes(hca_header)])
    wave_table=table('Waveform',[('EncodeType',0),('Streaming',0),('NumChannels',0),('LoopFlag',0),('SamplingRate',2),('NumSamples',4),('ExtensionData',2),('StreamAwbId',2)],
      [dict(EncodeType=2,Streaming=1,NumChannels=2,LoopFlag=1,SamplingRate=48000,NumSamples=48000,ExtensionData=65535,StreamAwbId=0)])
    children={'Name':'music1','WaveformTable':wave_table,
      'StreamAwbAfs2Header':table('StreamAwbHeader',[('Header',11)],[{'Header':head}]),
      'StreamAwbHash':table('StreamAwb',[('Name',10),('Hash',11)],[{'Name':'music1','Hash':bytes(16)}]),
      'CueNameTable':table('CueName',[('CueName',10),('CueIndex',2)],[{'CueName':'music','CueIndex':0},{'CueName':'preview','CueIndex':1}]),
      'CueTable':table('Cue',[('Length',4)],[{'Length':1000},{'Length':1000}]),
      'SynthTable':table('Synth',[('ReferenceItems',11)],[{'ReferenceItems':b'\0\1\0\0'},{'ReferenceItems':b'\0\7\0\0'}]),
      'TrackEventTable':table('Event',[('Command',11)],[{'Command':b'old playback'},{'Command':b'old seek/loop'}])}
    acb=table('Header',[(key,10 if key=='Name' else 11) for key in children],[children])
    return acb,awb

class ConverterTests(unittest.TestCase):
    def test_timing_rounding_chain_and_air_targets(self):
        src=HEADER+"#1'1:s04\n#481>c24\n#961>s44\n#1'962:H44N\n#480>s\n#960>s\n#3'0:C84280,240\n#240>c8428\n"
        out,report=convert(src,9999)
        self.assertIn('SLC\t1\t0\t0\t4\t96\t2\t4\tSLD',out)
        self.assertIn('SLD\t1\t96\t2\t4\t96\t4\t4\tSLD',out)
        self.assertIn('AHD\t1\t192\t4\t4\tSLD\t96\tDEF',out)
        self.assertIn('AHD\t1\t288\t4\t4\tAHD\t96\tDEF',out)
        self.assertIn('ALD\t3\t0\t8\t4\t48\t5.000\t48',out)
        self.assertEqual(report['converted_types'],{'s':1,'H':1,'C':1})
    def test_bpm_and_meter_changes_use_ugc_measure_lengths(self):
        src=HEADER.replace('@ENDHEAD','@BEAT\t2\t3\t4\n@BPM\t3\'0\t150\n@ENDHEAD')+"#3'0:t04\n"
        out,_=convert(src)
        self.assertIn('BPM\t2\t288\t150.000000',out)
        self.assertIn('TAP\t2\t288\t0\t4',out)
    def test_airslide_height_and_controls(self):
        src=HEADER+"#1'0:t04\n#1'0:S0428N\n#240>c243C\n#480>s4428\n"
        out,_=convert(src)
        self.assertIn('ASC\t1\t0\t0\t4\tTAP\t5.000\t48\t2\t4\t7.000\tDEF',out)
        self.assertIn('ASD\t1\t48\t2\t4\tASC\t7.000\t48\t4\t4\t5.000\tDEF',out)
    def test_rejects_unsupported_instead_of_partial_conversion(self):
        for src in [HEADER+"#1'0:z04\n",HEADER+"#1'0:a04UCN\n",HEADER.replace('@BGMOFS\t0','@BGMOFS\t0.2')+"#1'0:t04\n",
                    HEADER.replace('SOFFSET\tFALSE','SOFFSET\tTRUE')+"#1'0:t04\n",
                    HEADER+"#1'0:s04\n#1>s44\n",HEADER+"#1'0:h04\n#240>c\n"]:
            with self.subTest(src=src),self.assertRaises(ConversionError):convert(src)
    def test_ultima_slot_and_flick_preservation(self):
        out,_=convert(HEADER.replace('@DIFF\t3','@DIFF\t5')+"#1'0:f04A\n")
        self.assertIn('DIFFICULT\t04',out);self.assertIn('FLK\t1\t0\t0\t4\tL',out)

class AudioSongTests(unittest.TestCase):
    def test_prepared_pair_preserves_streams_and_playback_graph(self):
        from cri_audio import retarget_bank
        a,w=reference();renamed,unchanged=retarget_bank(a,w,6700)
        self.assertEqual(unchanged,w)
        before=read_utf(a)['rows'][0];after=read_utf(renamed)['rows'][0]
        for key in ('WaveformTable','SynthTable','TrackEventTable','CueNameTable','CueTable'):
            self.assertEqual(after[key],before[key])
        self.assertEqual(after['Name'],'music6700')
    def test_utf_and_awb_roundtrip_and_mismatch(self):
        a,w=reference();root,streams=validate_bank(a,w)
        self.assertEqual(read_utf(write_utf(root)),root)
        pair=[b'1'*35,b'2'*81];awb,h=write_awb(pair)
        self.assertEqual([b for _,b in read_awb(awb)],pair)
        with self.assertRaises(ValueError):validate_bank(a,awb)
        with self.assertRaises(ValueError):read_awb(awb[:20])
    def test_assemble_export_index_and_serialization(self):
        from PIL import Image
        from artwork import encode_world_dds
        template=parse(Path('templates/Music.xml').read_text());cue=parse(Path('templates/CueFile.xml').read_text())
        data=encode_world_dds(Image.new('RGB',(300,300),'blue'))
        song,bank,assets,reports=build_song(template,cue,99001,'A & B','Artist',{3:HEADER+"#1'0:t04\n"},data,reference())
        self.assertEqual(song.findtext('fumens/MusicFumenData[4]/file/path'),'99001_03.c2s')
        self.assertEqual(song.findtext('fumens/MusicFumenData[4]/levelDecimal'),'40')
        self.assertEqual(read_utf(assets['music99001.acb'])['rows'][0]['Name'],'music99001')
        self.assertEqual(parse(serialize(song)).findtext('name/str'),'A & B')
        with tempfile.TemporaryDirectory() as parent:
            out=export_option(parent,'A900',[song,bank],assets=assets)
            self.assertTrue((out/'music/music99001/99001_03.c2s').is_file())
            self.assertTrue((out/'cueFile/cueFile099001/music99001.awb').is_file())
            defs=[];index,errors=scan([out],defs);self.assertFalse(errors)
            self.assertIn(('CueFileData',99001),index);self.assertEqual(song_catalog([song],index)[0][1],'A & B')
            incomplete=dict(assets);del incomplete['music99001.awb']
            with self.assertRaises(ValueError):export_option(parent,'A901',[song,bank],assets=incomplete)
            self.assertFalse((Path(parent)/'A901').exists())
    def test_actual_project_roundtrip_keeps_new_binary_types(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from app import App
        from PIL import Image
        from artwork import encode_world_dds
        root,cue,assets,_=build_song(parse(Path('templates/Music.xml').read_text()),parse(Path('templates/CueFile.xml').read_text()),99001,'Song','Artist',
          {3:HEADER+"#1'0:t04\n"},encode_world_dds(Image.new('RGB',(300,300))),reference())
        fake=SimpleNamespace(docs=[root,cue],folders=[],assets=assets,nameplate_layouts={},dirty=True)
        with tempfile.TemporaryDirectory() as d:
            file=str(Path(d)/'song.cvproject')
            with patch('app.filedialog.asksaveasfilename',return_value=file):App.save_project(fake)
            loaded=SimpleNamespace(scanning=False,may_discard=lambda:True,refresh=lambda:None,rescan=lambda:None)
            with patch('app.filedialog.askopenfilename',return_value=file):App.open_project(loaded)
            self.assertEqual(loaded.assets,assets)
            self.assertEqual([r.tag for r in loaded.docs],['MusicData','CueFileData'])
    def test_old_adx_bank_is_blocked(self):
        from cri_audio import require_hca_bank
        a,w=reference();root=read_utf(a)
        waves=read_utf(root['rows'][0]['WaveformTable']);waves['rows'][0]['EncodeType']=0
        root['rows'][0]['WaveformTable']=write_utf(waves)
        with self.assertRaisesRegex(ValueError,'old ADX'):require_hca_bank(write_utf(root),w)
    def test_same_size_utf_changes_preserve_layout(self):
        from cri_audio import rewrite_utf
        source=table('Header',[('Name',10),('Count',4),('Untouched',11)],[{'Name':'music6700','Count':100,'Untouched':b'keep me'}])
        changed=read_utf(source);changed['rows'][0]['Name']='music6701'
        output=rewrite_utf(source,changed)
        self.assertEqual(len(source),len(output))
        self.assertEqual(sum(a!=b for a,b in zip(source,output)),1)
        self.assertEqual(read_utf(output),changed)

if __name__=='__main__':unittest.main()
