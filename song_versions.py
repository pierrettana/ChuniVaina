"""Release-tag choices from the user's indexed Music.xml metadata."""
import copy

def version_options(documents,current):
    """Retain exact StringIDs, including unknown/future versions and the current tag."""
    choices={}
    for root in [*documents,current]:
        if root.tag!='MusicData':continue
        tag=root.find('releaseTagName')
        if tag is None:continue
        try:number=int(tag.findtext('id','-1'))
        except ValueError:continue
        name=tag.findtext('str','')
        if number<0 or not name.strip():continue
        choices[(number,name)]=copy.deepcopy(tag)
    return [choices[key] for key in sorted(choices)]

def version_label(tag):
    return f'{tag.findtext("str")} · release ID {tag.findtext("id")}'

def set_song_version(root,tag):
    if root.tag!='MusicData':raise ValueError('Select a Song first.')
    if tag is None:return
    try:number=int(tag.findtext('id','-1'))
    except ValueError:raise ValueError('Version release ID must be numeric.')
    if number<0 or not tag.findtext('str','').strip():raise ValueError('Choose a valid CHUNITHM version.')
    old=root.find('releaseTagName')
    replacement=copy.deepcopy(tag);replacement.tag='releaseTagName'
    if old is None:root.insert(1,replacement)
    else:
        position=list(root).index(old);root.remove(old);root.insert(position,replacement)
