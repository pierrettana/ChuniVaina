"""Contextual field guide for supported CHUNITHM content."""

EVENT_TYPES={
 '1':'Announcement / information: uses the information block and its image; this alone is not a map-opening event.',
 '2':'Map opening: references a map in substances/map/mapName.',
 '3':'Music opening: Opens music or ULT content. Review the music block; this app has no music-opening preset.',
 '7':'Course opening: Opens course content. No course editor/preset is provided.',
 '8':'Quest opening: references quests in substances/quest/questNames/list.',
 '11':'Rights information: Lists rights-information definitions. Use New → Rights information for a definition/image, then New → Rights-information event (type 11) and Link event target to list it.',
}
REWARD_TYPES={
 '0':'Game points: use gamePoint/gamePoint.',
 '2':'Trophy: set trophy/trophyName to the trophy definition.',
 '3':'Character: set chara/charaName to the character definition.',
 '5':'Name plate: set namePlate/namePlateName.',
 '13':'Stage: set stage/stageName.',
}
TYPE_HELP={
 'CharaData':('Characters','Character definition: identity, category, artwork links, default ownership and rank entries. defaultHave=false requires an unlock. A reward that grants the character must also be delivered by a map, quest or another supported mechanism. Character IDs and artwork IDs are separate.'),
 'CharaWorksData':('Categories','Groups characters under a category. A character uses works/id; quests can reference the category in charaWorks/list. Use Link reference to keep the ID and name together. The category definition alone does not grant any characters. Known observed limitation: an otherwise unused category ID may be beyond the range displayed by the installed game. The cutoff may depend on the game version and may change with official updates; the mechanism is unconfirmed. ID conflict checks do not verify this runtime limit. Try an unused ID within the range supported by your installation, check imported sources and update all character/quest/map-bonus category references after renumbering. ChuniVaina does not enforce a guessed cap.'),
 'TrophyData':('Trophies','Defines the trophy text, description, numeric rarity and ownership settings. A trophy-granting Reward uses type 2. Merely creating a trophy does not connect it to a quest or map. The supplied examples do not establish the rarity-to-color/name mapping.'),
 'RewardData':('Rewards','A reward contains one or more RewardSubstanceData entries. Each entry has a type and corresponding payload. Duplicate an entry for multiple grants. Link reward sets trophy/character references; then connect the reward to a map completion, area checkpoint or quest milestone. An orphan reward is not proof of an obtainable unlock.'),
 'QuestData':('Quests','Contains category/character references and QuestRewardDataInfo milestones. Each milestone has sumRank, key references and a reward list. Use a separate type-8 quest-opening event. Use New → Quest-opening event, assign a unique ID, then Link event target. Progress semantics, repeated sumRank values and the exact role of key fields are not confirmed.'),
 'DDSImageData':('Character artwork','Three DDS slots: 0 = 1080×1080, 1 = 512×512, 2 = 128×128. Artwork studio converts PNGs to uncompressed BGRA DDS with alpha and mipmaps. Link character to artwork connects a character to this definition. Save project embeds attached DDS bytes.'),
 'EventData':('Events','An event definition has an ID, release reference, flags and substances/type. Event type selects the role; setting a map reference on an announcement does not change its type. Use the map/quest-opening presets and review alwaysOpen and release references for your installation.'),
 'MapData':('Maps','A map contains MapDataAreaInfo entries. Each row links an area, background artwork and completion reward; pageIndex/indexInPage determine its stored position. Use the map editor to add/remove rows and connect custom content. Referenced external songs/gauges must also exist. Use a separate type-2 opening event.'),
 'MapAreaData':('Map areas','Defines grid/checkpoint positions, rewards, bonus reference, boost and other area settings. The sample has entrance 0, reward checkpoints 5/25/45, and exit 55. Grid index is a position, not the number of XML entries. Use unique ascending positions. The map/area editor has a live numbered grid: edits preview immediately, duplicate positions turn red, and clicking checkpoints selects their entries after applying the current edit. Scroll for long areas. Rows wrap for readability; this is a schematic, not the exact in-game path. Save to project commits the draft. An area must be referenced by a map to form a configured map unlock path.'),
 'MapBonusData':('Map bonuses','Rules for bonus points associated with a map area. The sample demonstrates type 1 for a character category and type 5 for music genre. Edit the matching condition and points. A bonus reference is not a character unlock. Other numeric enum values remain unverified.'),
 'NamePlateData':('Nameplates','Defines a nameplate with identity, ownership and an attached image. Reference dimensions are 576×228; PNG conversion uses DXT5 with alpha and one mip. Use Artwork studio for preview/conversion. A type-5 Reward grants a nameplate; connect it to a map or quest as usual.'),
 'DDSMapData':('Map artwork','A DDS background referenced by a map row through ddsMapName. Reference dimensions: 1220×680, DXT1 with one mip. Artwork studio can resize/crop PNGs and preview this image. This conversion is opaque: transparency and padding become black.'),
 'StageData':('Stages','Template-based gameplay stage. Import Stage.xml with its referenced AFB/DDS files beside it; assign a unique ID/name and Apply identity. Stage texture editor browses embedded DXT1/DXT3/DXT5 textures, frames PNG/image replacements, and preserves dimensions, compression, mip count and bundle length. Replace selected texture commits to the dialog draft; Apply stage bundles commits to the project. Save project persists AFBs. Artwork studio edits only the 960×450 selection preview (DXT1). Stage geometry, camera/animation behavior and internal resource names are preserved; this is not a 3D scene editor. Attach base/note-field AFBs and optional objects as needed. Reward type 13 grants a stage; deliver it through a map or quest, or set defaultHave=true.'),
}

COMMON={
 'rightsText':'Human-readable rights credit. Artwork studio renders this text into a DDS only when Apply DDS & text is clicked. Editing XML text alone does not update the image.',
 'dispNet':'Rights display flag, enabled by the template. Review netOpenName and the type-11 event as well.',
 'rightsNames':'RightsInfoData references listed by a type-11 event. Select the list and Link reference, or use Link event target on the rights-information event preset.',
 'dataName':'Folder/data identity. Apply identity derives it from the selected content type and ID, including the correct zero padding. Export validates that they match.',
 'name':'This definition’s ID and display/reference name. Edit with the identity controls, then Apply identity. Existing references elsewhere do not automatically update.',
 'defaultHave':'true = available by default; false = requires an unlock. Axxx export warns if no supported configured unlock path is found. Existing profile/server ownership can affect what you see in-game.',
 'disableFlag':'Enable/disable flag; false means this flag does not disable the definition. Other visibility or opening requirements may still apply.',
 'hideInfo':'Information-hiding flag. The supplied quest uses false; the exact UI behavior of true is not fully documented.',
 'netOpenName':'Release/opening reference (ID plus name). Samples use version/distribution tags. Preserve a known compatible value or choose a reference appropriate to your setup; it is not a calendar date or the ID of your custom opening event.',
 'releaseTagName':'Version/release reference. Song studio provides a CHUNITHM version selector using exact tags from indexed Music.xml and project songs. Rescan A000/Axxx sources after updating. Applying writes the selected tag; Stage ID -1 allows the game’s default behavior, while a special stage stays set. This is separate from netOpenName and the Axxx export version.',
 'alwaysOpen':'Always-open flag; the map/quest opening examples use true. This alone does not change the event type or establish that a server will honor it.',
 'teamOnly':'Team-only flag. The provided opening events use false. Exact behavior when true is not fully documented.',
 'isKop':'KOP-related flag. The examples use false; its complete behavior is not established.',
 'periodDispType':'Numeric period-display setting. The opening examples use 1; its complete enum mapping is not established.',
 'priority':'Numeric priority setting. Examples use 0. The direction and scope of ordering have not been verified.',
 'notesFieldFile':'AFB bundle for note-field resources. A note-field bundle can contain geometry/resource data without embedded DDS textures. Attach this in Stage texture editor; it is preserved on export.',
 'baseFile':'AFB bundle for the gameplay stage. This bundle may contain embedded DDS textures alongside scene resources. Stage texture editor replaces textures while preserving the scene data.',
 'objectFile':'Optional stage object AFB. Leave this empty when no object bundle is needed. A nonempty path requires an attached AFB at export.',
 'notesFieldLine':'Note-field line style reference. The supplied stage uses ID 8 / White. Other IDs and visual mappings are unverified.',
 'enablePlate':'Stage flag retained as false by the template. Its exact effect is unverified.',
 'isReward':'Stage flag retained as true by the template. Use an actual stage-granting Reward (type 13) and a delivery path to configure an unlock; this flag alone is not an unlock.',
 'sortName':'Separate sort-name string. It does not automatically change when you change the display name.',
 'rareType':'Numeric rarity/type code. Trophy examples show different values, but the color/title mapping has not been established. The app preserves the number rather than guessing a label.',
 'sumRank':'Rank threshold stored for a quest milestone. The name suggests a summed rank value, but category-total versus per-character behavior has not been confirmed. Choose a threshold appropriate to the intended quest progression.',
 'keyCharaName':'Character key reference on a quest milestone. This is not the character-granting Reward payload. Its exact role in quest progress/display is unverified.',
 'keyTrophyName':'Trophy key reference on a quest milestone. This is separate from the rewardName list. Its exact runtime role is unverified.',
 'keyNamePlateName':'Name-plate key reference on a quest milestone. Its exact runtime role is unverified.',
 'musicName':'Song reference. In a map row this is the task track. Use Map / area / bonus editor → Search songs to choose from imported song titles, artists and IDs, or Clear task track to remove it. Rescan imported A000/Axxx folders after updating ChuniVaina.',
 'rewardName':'Reward definition reference, or a list of reward references. It points to RewardData; it is not a raw trophy/character ID.',
 'mapAreaName':'Map-area definition reference for this map row. Use Link reference or the map editor to select a project/indexed area.',
 'ddsMapName':'Map-artwork (DDSMapData) reference. The DDS file is attached to that artwork definition rather than stored directly in this reference.',
 'mapBonusName':'MapBonusData reference used by the area. Changing the name without the correct ID does not establish a valid link.',
 'mapName':'MapData reference. For map opening, it belongs in a type-2 Event; a type-1 announcement with this reference is not the opening preset.',
 'defaultImages':'Default DDSImageData reference for a character. Link character to artwork sets the ID/name pair.',
 'changeImg':'Enables this alternate image slot. Link character to artwork enables it automatically; review the associated rank and image reference.',
 'rank':'Rank value on an alternate character image. Set the intended unlock rank; its exact limits are not established by the sample.',
 'pageIndex':'Map row’s stored page index. The sample uses zero-based pages; keep the pair (pageIndex, indexInPage) unique.',
 'indexInPage':'Map row’s stored position within its page. Keep the page/position pair unique. The full range of allowed positions is not established.',
 'requiredAchievementCount':'Numeric achievement-count requirement on a map row. Sample values are 0; the full runtime meaning has not been verified.',
 'isHard':'Hard-area flag stored on a map row. The supplied rows use false; consequences of true have not been verified.',
 'hiddenType':'Numeric hidden-state setting. The examples use 0; other values and unlock behavior are unverified.',
 'mapType':'Numeric map category/type setting. The map template uses 2; the full enum mapping is not established.',
 'mapFilterID':'Filter reference used by map/event information. The template uses ID 0 with name Collaboration. Other mappings are not established.',
 'stopReleaseEventName':'Reference to a release/stop event. The example uses -1 / Invalid; do not repurpose it as the normal map-opening event without evidence.',
 'mapAreaBoostType':'Numeric boost setting; sample 0. Complete enum mapping is unverified.',
 'mapAreaBoostMultiple':'Numeric boost multiplier setting; sample 10. The scale/units have not been verified.',
 'shorteningGridCountList':'Per-entry shortening counts. The sample has eight entries set to 0. The correspondence to other game settings is not established.',
 'point':'Bonus point value for this condition. Edit the points under the condition matching the bonus type.',
 'path':'Asset filename/path. For the artwork slots supported by this app, attach a DDS or use Artwork studio; export copies it beside the XML. Plain filenames are required for these attachments.',
 'id':'An ID is interpreted in the namespace of its reference/definition type. -1 with name Invalid is the sample’s unused-reference sentinel. A number reused across different definition types is not necessarily a conflict.',
 'str':'Display/reference name paired with an ID. Use Link reference to set both consistently. Do not rely on changing the name alone to redirect a reference.',
 'data':'Additional serialized reference data, often empty in examples. Preserve it unless you know that field’s required payload.',
}

TYPE_HELP['MusicData']=('Song','Song studio imports Margrete text UGC v8 difficulties and creates C2S charts, a 300×300 jacket and a linked CueFile audio bank. Choose a unique numeric ID. Music and CueFile conflicts are checked separately. Save project, then export an Axxx folder. Existing release/net-open references can affect cabinet/server availability; review them in the structured editor.')
TYPE_HELP['RightsInfoData']=('Rights information','Defines a rights credit with rightsText, identity, dispNet, netOpenName, image and priority. Use New → Rights information, Apply identity, then Artwork studio to render text into a 512×48 transparent DXT5 DDS with one mip. Choose font, size, alignment and color; Apply DDS & text, then Save project. Existing DDS files can be attached unchanged. Rights entries are listed in a separate type-11 Event; create the rights-information event preset and Link event target for each entry. Use the type-11 event to list rights entries; the song schema has no direct song-to-rights field.')
TYPE_HELP['CueFileData']=('Song audio bank','A CueFile definition links your prepared HCA ACB/AWB pair. ACB/AWB fixer corrects supported single-stream bank metadata and converts plain HCA to the CHUNITHM type-56 cipher profile. Cipher conversion verifies identical decoded PCM. Existing encrypted audio is preserved without inferring its key compatibility. Preview commands and internal bank name are preserved. Use repaired pair commits to the selected bank; Save project afterwards. WAV/MP3 conversion, multi-stream/ADX banks and unsupported layouts require external tools. Resource: CHUNITHM Customs Source by Suprnova, https://github.com/Suprnova/Chunithm-Research/blob/main/Customs.md .')
TOPICS={
 'Getting started':'Import Axxx folders (Bulk import accepts a parent folder) → New or Import XML → choose your ID/name → Apply identity → edit/link fields → Save project → Export Axxx folder. Templates retain sample references: review every external link. Check references helps find missing targets.',
 'Event type guide':'Supported event roles:\n\n'+'\n\n'.join(f'{code} — {text}' for code,text in EVENT_TYPES.items())+'\n\nOther values are unverified. These descriptions identify the observed role, not a guarantee of runtime/server activation.',
 'Reward type guide':'Supported reward roles:\n\n'+'\n\n'.join(f'{code} — {text}' for code,text in REWARD_TYPES.items())+'\n\nOther values remain numeric/unverified. Link reward provides trophy, character, and nameplate shortcuts.',
 'Unlock workflow':'For a locked character: set defaultHave=false → make a Reward whose type-3 substance grants that character → deliver the Reward through a map completion, a checkpoint in a linked area, or a quest milestone. A reward by itself can remain unreachable. Configure a type-2 map or type-8 quest opening event as appropriate. Export warns about missing supported paths. Availability also depends on your game and server configuration.',
 'Artwork workflow':'Character artwork uses three transparent BGRA DDS files with mipmaps; map/event images use opaque DXT1 with one mip. Select the definition → Artwork studio → choose PNG → adjust Fit/Crop, zoom and alignment → Apply converted artwork. Save project retains DDS files. Original DDS attachments are preserved unless replaced.',
 'Saving and applying edits':'Set value commits a leaf field. Apply identity commits ID/name changes and synchronizes dataName. Apply XML edits commits the advanced XML tab. Apply entry commits a list-editor row before selecting another. Save to project commits the map/area/bonus editor. Save project writes the project file; Export does not replace saving your project.',
 'References and conflicts':'Definitions and references are different. Conflicts compare top-level definition IDs within one type. Link reference sets an ID/name pair; reference lists can append entries. Scan sources to include external definitions. Changing a target ID later does not automatically update links. Axxx export blocks duplicate project IDs and warns about imported collisions.',
 'Evidence and limits':'Help describes supported XML structures and artwork formats. Known mappings are described in context. Unverified flags/enums are explicitly labeled. The app does not contain a complete official schema and cannot verify server scheduling, arbitrary unlock mechanisms, all asset dependencies, or every in-game effect.',
}
TOPICS['Layered nameplate composer']='Select a Nameplate → Artwork studio. Import multiple images; add text and shapes; drag layers or enter transforms. Topmost layers appear first in the list. Raise/Lower changes stacking. Opacity, rotation, flipping, visibility, locks, Fit/Fill, font/color controls and undo/redo are available. Property edits commit before switching layers or invoking tools; Apply properties commits immediately. Apply DDS & layers updates the project; close the composer and Save project to persist both the DDS and editable layers. Save layout exports a portable .cvplate with embedded images/fonts. Starter template is an original editable design. Guides are layout suggestions, not verified game-safe regions. Existing DDS imports are flattened and cannot recover their original layers.'
TOPICS['Task track picker']='Select a map → Map / area / bonus editor → select a row → Search songs. The catalog includes imported A000/Axxx metadata and songs in the current project. Choose a track, Apply entry, then Save to project. Clear task track writes -1 / Invalid. Rescan sources after adding external songs.'
TOPICS['Custom song conversion']='New → Song / UGC converter, or Song studio. Select one song’s UGC difficulties, jacket and ID, then attach a prepared ACB with matching AWB. Native audio conversion is not supported. Follow CHUNITHM Customs Source by Suprnova: https://github.com/Suprnova/Chunithm-Research/blob/main/Customs.md . Preview timing follows your prepared bank. Apply song to project adds both MusicData and CueFileData atomically. Binary MGXC, custom timelines/speeds, SOFFSET, nonzero BGMOFS, overlapping Ex-long carriers and AIR-HOLD endpoints without actions are rejected explicitly. Normal TAP/ExTAP/FLICK/HOLD/SLIDE/AIR/AIR-HOLD/AIR-SLIDE/AIR-CRUSH, BPM and meter changes are supported. WORLD’S END is not supported yet. C2S uses 384 ticks per nominal four-beat measure; absolute endpoints are rounded together to keep segments connected.'
from song_model import CHART_CONSTANT_WARNING
TOPICS['Custom chart constants and server rules']=CHART_CONSTANT_WARNING+' Review Song → fumens → each enabled MusicFumenData → level and levelDecimal. Constants imported from UGC are retained until you edit them; do not assume they meet your server’s rules.'
TOPICS['Removing project files']='Project files below the project list shows embedded files, sizes and users. Remove selected files supports multiple selections; Remove all unused files cleans stale attachments. Removing used files asks before clearing their file references; required assets must be replaced before export. Remove selected item also removes its editable nameplate layers and unshared attachments, keeping shared files. Song and CueFile are separate items: remove both to remove the song and its bank. DDS deletion alone retains separate editable nameplate layers. Save project writes these removals to disk; source files are untouched.'
TOPICS['Quick tour']='Quick tour in the header opens the optional penguin-guided introduction. Use Back and Next to browse, Skip tour to close, or Don’t show this tour at startup to hide future startup visits. Finishing the tour also hides it at startup. You can always reopen it from Quick tour or About. It does not modify your project.'
TOPICS['Quick trophy']='Quick trophy creates independent EXPERT and/or MASTER ALL JUSTICE trophies for a song chosen from the project or imported catalog. Edit trophy text and IDs, then Create trophies, Save project and Export. The presets use type-1 song/difficulty condition plus type-3 ALL JUSTICE condition, rareType 4/6, defaultHave=false. Both means two separate awards, not one award requiring both charts. No Reward, map or quest is generated. Review the retained netOpenName release reference.'
TOPICS['ACB/AWB fixer']='Open ACB/AWB fixer from the main editor or Song studio. It loads the attached bank when available; otherwise choose an ACB and matching AWB. Repair & verify runs in the background. Supported: a single streaming stereo HCA 2.0 waveform, 96-byte header, comp/fmt/ciph layout, 44.1 or 48 kHz, up to 30 minutes; plain input requires AWB subkey zero. Corrects sample rate/count/channels and named music cue length, applies the public vgmstream CHUNITHM cipher entry to plain HCA, checks identical decoded PCM and every header/frame checksum, and refreshes the AWB hash. Existing type-56 streams stay untouched; this does not prove their key compatibility. The cue graph, preview commands, internal name and AWB offsets are retained. Save repaired ZIP writes a new copy. Use repaired pair updates the Song studio draft or selected project bank; Apply song and/or Save project afterwards. No source files are overwritten. Unsupported/damaged formats require external preparation. WAV/MP3 conversion remains external. Credits: Suprnova’s CHUNITHM research, vgmstream’s public audio entry, and CriCodecs cipher/verification support.'
for kind,(title,body) in TYPE_HELP.items(): TOPICS[title]=body


def describe_field(root, element):
    parents={c:p for p in root.iter() for c in p}
    chain=[]; current=element
    while current is not None:
        chain.append(current.tag);current=parents.get(current)
    path='/'.join(reversed(chain[:-1]))
    tag=element.tag
    if element is root: return TYPE_HELP.get(root.tag,('Unknown','No verified description available.'))[1]
    if tag=='type' and root.tag=='EventData' and path=='substances/type':
        value=(element.text or '').strip()
        return 'Event type '+value+': '+EVENT_TYPES.get(value,'Unverified value; no role mapping is established by the supplied examples.')
    if tag=='type' and 'RewardSubstanceData' in chain:
        value=(element.text or '').strip()
        return 'Reward type '+value+': '+REWARD_TYPES.get(value,'Unverified value; preserve or consult a matching working reward example.')
    if tag in ('type','displayType') and 'MapAreaGridData' in chain:
        return 'The supplied grid examples use type/displayType 1 at the entrance, 2 at the exit, and 3 at reward checkpoints. Other values and independent combinations are unverified.'
    if tag=='type' and 'MapBonusSubstanceData' in chain:
        return 'Map bonus type: the supplied example demonstrates 1 for character category (charaWorks) and 5 for music genre (musicGenre). Set the corresponding condition and point value. Other values are unverified.'
    if tag=='index' and 'MapAreaGridData' in chain: return 'Grid position along the area. The sample uses 0, 5, 25, 45, 55; these are positions, not a count of XML nodes. Keep indices unique, nonnegative and ascending.'
    if tag=='name' and parents.get(element) is not root: return 'ID/name reference. Its namespace depends on the enclosing field; use Link reference where supported.'
    if tag in COMMON: return COMMON[tag]
    return 'No verified description for this field yet. Its exact semantics/enum are not established by the supplied examples. Preserve a known working value or compare a matching reference.'


def open_help(app):
    import tkinter as tk
    from tkinter import ttk
    from tkinter.scrolledtext import ScrolledText
    win=tk.Toplevel(app);win.title('ChuniVaina help');win.geometry('920x650');win.transient(app)
    from branding import badge
    heading=ttk.Frame(win,padding=14);heading.pack(fill='x')
    badge(heading,(36,36)).pack(side='left',padx=(0,10))
    ttk.Label(heading,text='Help & field guide',font=('Helvetica',20,'bold')).pack(side='left')
    query=tk.StringVar();entry=ttk.Entry(win,textvariable=query);entry.pack(fill='x',padx=14,pady=(0,10))
    body=ttk.Frame(win,padding=14);body.pack(fill='both',expand=True)
    listing=tk.Listbox(body,width=27,exportselection=False);listing.pack(side='left',fill='y',padx=(0,12))
    content=ScrolledText(body,wrap='word',padx=12,pady=12,font=('Helvetica',12));content.pack(side='left',fill='both',expand=True)
    titles=[]
    context=''
    if app.current is not None:
        root=app.root();selection=app.tree.selection()
        element=app.nodes.get(selection[0],root) if selection else root
        context=describe_field(root,element)
    local={'Selected field / item':context} if context else {}
    local.update(TOPICS)
    def show(_=None):
        if not listing.curselection(): return
        title=titles[listing.curselection()[0]]
        content.configure(state='normal');content.delete('1.0','end');content.insert('end',title+'\n\n'+local[title]);content.configure(state='disabled')
    def search(*_):
        titles[:]=[title for title,text in local.items() if query.get().casefold() in (title+' '+text).casefold()]
        listing.delete(0,'end')
        for title in titles: listing.insert('end',title)
        if titles:listing.selection_set(0);show()
        else:
            content.configure(state='normal');content.delete('1.0','end');content.insert('end','No matching help topics.');content.configure(state='disabled')
    listing.bind('<<ListboxSelect>>',show);query.trace_add('write',search);search();entry.focus_set()
