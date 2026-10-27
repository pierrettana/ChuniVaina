# ChuniVaina 1.1.1

A desktop studio for a certain sliding rhythm game.. Make characters, categories, trophies, rewards, quests, events, maps, nameplates, rights credits, custom songs and stage texture variants in one project.

The optional **Quick tour** features VainaPenguin, our penguin mascot! You may Skip it, disable startup display, or reopen it from the header. **Help / F1** provides searchable field descriptions.

## Run or build

Install Python 3.12 or newer with Tk support. From this folder:

```
python3 -m pip install -r requirements.txt
python3 app.py
```

On Windows, use `py -3` instead of `python3`. Launch.command and Launch-Windows.cmd launch an environment with dependencies already installed.

- **macOS:** run `bash Build-Mac.command`. Output: `dist/ChuniVaina.app`.
- **Windows:** run `Build-Windows.cmd` on Windows. Output: `dist\ChuniVaina\ChuniVaina.exe`. Distribute the entire ChuniVaina folder with its supporting files.
**ATTENTION**: ChuniVaina was created using MacOS and was made with MacOS in mind. The Windows version may contain errors.

The scripts install dependencies in a build environment and bundle templates, artwork and platform icons. Build on the operating system you intend to distribute for. The scripts do not sign or notarize applications.

## Start a project

1. Import **A000** and your **Axxx** folders as ID conflict sources. **Bulk import Axxx folders…** accepts a parent folder and lets you select multiple options. Sources are read-only. Rescan after source changes.
2. For a guided workflow, choose **New → Guided character creator…**. It creates a character and linked artwork definition, with category and default ownership choices. Then use **Edit linked artwork…** to fill its three image slots. For other content, choose **New** or **Import XML**. Set the ID/name, then **Apply identity**. Templates preserve structural defaults and external release references; review them for your installation.
3. **Item settings & next steps** is the default tab: character ownership/category forms and tools relevant to the selected item. Other settings and reference links remain under **Advanced fields**; raw XML remains available. Edit advanced fields with **Set value**, or use specialized editors. Advanced XML changes need **Apply XML edits**. Studio Apply buttons commit drafts to the project.
4. **Link reference**, **Link reward** and **Link event target** connect definitions. Changing an ID does not automatically update other items’ links.
5. **Save project** writes an editable `.cvproject`, including attachments and editable nameplate layers. Existing project files remain supported.
6. **Check references**, then **Export Axxx folder…** with your chosen folder name. **Include data.conf** is optional and unchecked by default; version fields are enabled only when selected. Export creates definitions and assets, plus `data.conf` only if requested, in a new folder. Existing output folders and imported sources are protected from overwrite.

**ID selection:** do not reuse official IDs. Import A000 and all installed options before choosing IDs. Avoid ranges likely to be used by future official updates, especially for custom songs; leave room beyond current allocations. No numeric range is guaranteed safe. The conflict detector checks scanned sources and project content; it cannot predict or reserve future official IDs. Recheck after updates and update all references if renumbering.

**Optional data.conf:** custom content can load with or without this file. It supplies option/version information so the option appears in the test menu; it is not required for loading the custom itself. Files, IDs, references and installation must still be compatible. Version metadata can cause conflicts with the installed game or subsequent updates even when the content files remain compatible. Leave it unchecked unless you understand the version requirements. The sample version values are not detected from your installation. Review or omit the file when migrating content; it does not convert content to another version. Existing exports are never changed automatically.

The window title and project status show whether applied project changes need saving. Studio windows keep their own drafts until Apply; Save project does not commit an open studio or raw XML draft.

IDs are compared within each definition type. Duplicate project IDs block export; imported collisions require review. Unresolved references may belong to another option, but all dependencies must exist in the installation.

## Characters, rewards and quests

**Link character to artwork…** sets default or alternate DDSImage references. Set alternate-image ranks separately. Character artwork uses 1080×1080, 512×512 and 128×128 slots. Artwork studio provides PNG framing, live preview and DDS conversion with transparency and mipmaps.

Create a **Reward**, select its substance and use **Link reward…**. Shortcuts grant characters, trophies and nameplates; duplicate entries for multiple grants. Deliver rewards through map completion, area checkpoints or quest milestones. A reward by itself does not make content obtainable.

For characters with `defaultHave=false`, export warns when no supported configured unlock path is found. Link an appropriate unlock or enable default ownership. Quests use milestone rank thresholds, key references and reward lists; create a **Quest-opening event (type 8)** and link the quest too.

**Quick trophy…** creates separate EXPERT and/or MASTER ALL JUSTICE trophies. Choose the song, trophy text and IDs. Each difficulty unlocks its own award. Review the retained release reference before export.

## Maps and events

**Map / area / bonus editor…** edits map rows, checkpoints and bonus rules. **Apply entry** commits a row; **Save to project** commits the draft. Cancel discards the draft.

- Map rows link an area, background, completion reward and optional task track. **Search songs** finds tracks by title, artist or ID. **Clear task track** removes the reference.
- The live grid previews positions, entrances, exits and reward names. Click checkpoints to select them. Duplicate positions turn red. This is a schematic, not the game’s rendered path. Keep positions unique and nonnegative.
- Bonus rules include category and music-genre conditions. Other numeric settings remain in the structured editor.
- A **Map-opening event (type 2)** opens a map, **Quest-opening event (type 8)** lists quests, and **Rights-information event (type 11)** lists rights entries. Use **Link event target…**.
- Announcement events (type 1) have their own image and do not replace opening events. Review release references and game/server activation requirements.

## Artwork, nameplates and rights

**Artwork studio…** previews DDS and converts source images. Map/announcement artwork uses opaque DXT1; transparent padding becomes black. Apply attaches the DDS; Save project persists it.

Nameplates use a 576×228 transparent DXT5 image. The layered composer supports images, text, shapes, dragging, transforms, opacity, rotation, flips, stacking, locks, visibility and undo/redo. **Apply properties** commits controls; **Apply DDS & layers** commits the image and layout. **Save layout** writes a portable `.cvplate` with embedded images/fonts. The general starter design and guides are optional. Existing DDS files are flattened. Limits: 64 layers, 20 megapixels per source, 4096 pixels per transformed dimension. Painting, masks and PSD import are unavailable.

Rights information has `rightsText` and a 512×48 transparent DXT5 image. Artwork studio renders text with font, size, alignment, color and shrink-to-fit controls. **Apply DDS & text** updates both; XML text edits alone do not redraw the image. Create a type-11 event and link its entries. The song schema has no direct song-to-rights field.

## Custom songs

**Song studio / UGC converter…** imports one song’s Margrete text UGC v8 difficulties, jacket and prepared ACB/AWB pair. Binary MGXC is unsupported. Pick ID, title, artist, genre, **game version** and optional stage. Versions come from exact release tags in indexed and project songs; rescan sources to populate them. Stage ID -1 uses version-default behavior.

Jackets are framed to 300×300 DXT1. **Apply song to project** converts charts and commits Music/CueFile definitions together. Save project before export. New songs appear in the task-track picker immediately.

Supported: BASIC through ULTIMA, TAP, ExTAP, FLICK, DAMAGE, HOLD, SLIDE, AIR, AIR-HOLD, AIR-SLIDE, AIR-CRUSH, BPM and meter changes. Authored notes are preserved. Unsupported gameplay reports an error. WORLD’S END, custom timelines/speed effects, SOFFSET, nonzero BGMOFS, overlapping ExTAP/long-note carriers and AIR-HOLD endpoints without actions are unsupported. Metronome CLICKs are omitted with a warning. Presentation-only backgrounds/field styling are not exported.

**Audio encoding requires external tools.** Follow [Audio preparation guide](https://github.com/Suprnova/Chunithm-Research/blob/main/Customs.md) by [Suprnova](https://github.com/Suprnova), then attach HCA ACB/AWB files. The opening notice includes Don’t show again. **ACB/AWB fixer…** repairs supported banks without re-encoding; see [AUDIO_FIXER.md](AUDIO_FIXER.md).

**Chart constants:** follow your server’s rules. Some public instances require low constants to avoid rating and leaderboard advantages. Imported constants are retained; review every enabled difficulty’s `level` and `levelDecimal`. There is no universal safe value. Song registration and server activation remain external.

## Stage textures

Import Stage XML with its AFB/DDS files, then open **Stage texture editor…**. Attach base, note-field and optional object bundles. Supported FILS/FILE/AFRC containers expose 2D DXT1/DXT3/DXT5 textures. Replacement preserves dimensions, compression, mip count and bundle length. Apply stage bundles commits the draft; Save project persists it. Artwork studio edits the 960×450 selection preview separately.

This is a texture editor, not a 3D scene editor. Geometry, animation, cameras, effects and internal names remain intact. Some bundles contain no embedded DDS textures. Preview shows individual textures, not an assembled stage. Supply your own compatible bundles; none are included.

## Project files

**Project files…** lists embedded assets, sizes and users. Remove selected files supports multiple selections; removing used assets asks before clearing references. Required missing attachments block export. Remove all unused files clears stale attachments.

Removing an item also removes its nameplate layers and unshared attachments. Shared files remain. Song and CueFile are separate items; remove both for complete song removal. Deleting a DDS alone retains editable layers. Save project persists removals; source files are never deleted.

## Limitations

CharaWorks IDs beyond the range displayed by your game may not appear even without conflicts. The range can depend on game version and official updates; no universal maximum is enforced. Try an unused supported ID and update references after renumbering.

Validation covers supported structures/assets/references, not a complete official schema. Unknown fields are preserved, whitespace normalized and comments not retained. Some flags and enums are undocumented; Help labels them accordingly. Game/server behavior and dependencies depend on your installation. Mates and e-mote editing are not supported.

## Credits

- pierretta: ChuniVaina and supplied mascot artwork.
- [Suprnova / Chunithm-Research](https://github.com/Suprnova/Chunithm-Research): preparation and format research.
- [vgmstream](https://github.com/vgmstream/vgmstream/blob/master/src/meta/hca_keys.h): public audio interoperability information.
- [CriCodecs](https://github.com/Youjose/CriCodecs): HCA cipher conversion and verification.
- [UMIGURI UGC specification](https://gist.github.com/inonote/5c01e73781cab17765a1d93641d52298): chart format reference.
- [SonicAudioTools](https://github.com/blueskythlikesclouds/SonicAudioTools): ACB format reference.
- Python, Tk, Pillow and PyInstaller: runtime, interface, images and packaging.

An independent community tool, not affiliated with or endorsed by SEGA. No game audio, songs, artwork or stage binaries are bundled. Third-party dependencies retain their respective licenses.
