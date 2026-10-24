# ACB/AWB fixer

Repair supported externally prepared HCA banks without re-encoding or resampling. WAV/MP3 preparation, HCA encoding and initial bank creation require external tools.

## Workflow

In Song studio, attach your pair, open **ACB/AWB fixer…**, choose **Repair & verify**, then **Use repaired pair**. Choose **Apply song to project**, close the studio and **Save project** before export.

The main editor’s fixer loads the selected Song or CueFile’s pair when available. **Use repaired pair** updates attachments. Shared filenames cannot silently replace another item’s different content.

For standalone files, choose an ACB and matching AWB, repair, then **Save repaired ZIP…** with a new filename. Extract both files together. Source files are never overwritten. Internal names, cue graphs and preview commands remain intact.

## Supported formats

- One streaming stereo HCA 2.0 waveform with a 96-byte fmt/comp/ciph header, at 44.1 or 48 kHz, up to 30 minutes.
- ACB sample-rate/count/channel metadata, named music cue duration and external AWB hash are corrected. AWB offsets, padding and IDs remain intact.
- Plain cipher-type-0 streams become type 56 using the public vgmstream CHUNITHM interoperability entry. Plain banks require AWB subkey zero.
- Every HCA header/frame checksum is checked. Cipher conversion requires identical decoded PCM before and after processing.
- Existing type-56 streams stay byte-identical. Key compatibility is not inferred or changed.
- Damaged frames, unsupported layouts/ciphers, multiple streams and verification failures stop repair. Repeating a repair does not double-encrypt the stream.

Game-version compatibility also depends on your installation and bank. This is not a general audio encoder.

## Credits

[Suprnova’s CHUNITHM Customs Source](https://github.com/Suprnova/Chunithm-Research/blob/main/Customs.md), [vgmstream](https://github.com/vgmstream/vgmstream/blob/master/src/meta/hca_keys.h), and [CriCodecs](https://github.com/Youjose/CriCodecs). The build scripts install and bundle CriCodecs for cipher conversion and verification. FFmpeg is not required.
