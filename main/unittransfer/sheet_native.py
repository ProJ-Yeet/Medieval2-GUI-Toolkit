"""Typed sheet drafts -> existing EDU field patcher and backup/Undo writer."""
from __future__ import annotations
import difflib
import hashlib
import json
from pathlib import Path
from . import buildings,edu,sheet_ops,unit_sheets as sheets
from . import i18n as _i18n
from .mod import Mod


def plan(mod,project):
    fresh=Mod(mod.root);units=sheets.live_units(fresh);sheet_ops.records(fresh,project)
    originals={};parsed={};changes=[]
    for uid,columns in project['draft'].items():
        if uid not in units:sheets.fail(_i18n.msg('eng.sheets.native_unit_absent','Staged unit {unit} is absent from the mod',unit=uid))
        unit=units[uid];path=Path(unit.eop_file) if unit.is_eop else fresh.edu_path
        expected=project.get('draft_sources',{}).get(uid)
        if expected and expected!=sheets.revision({'raw':unit.raw}):sheets.fail(_i18n.msg('eng.sheets.draft_source_changed','Source unit {unit} changed after staging; discard its draft and review again',unit=uid))
        if not path.is_file():sheets.fail(_i18n.msg('eng.sheets.native_extract_first','Extract the unit file before applying sheet edits'))
        if path not in parsed:
            originals[path]=path.read_bytes();parsed[path]=edu.parse_text(originals[path].decode(edu.ENCODING))
        live=[u for u in parsed[path].units if u.type==uid]
        if len(live)!=1:sheets.fail(_i18n.msg('eng.sheets.native_unit_ambiguous','Unit {unit} is missing or duplicated in its source file',unit=uid))
        overrides,removals=sheet_ops.field_changes(live[0],columns)
        before=live[0].raw;after=edu.apply_field_edits(before,overrides,removals)
        live[0].raw=after
        if before!=after:
            changes.append({'unit':uid,'fields':overrides,'removed':removals})
    texts={p:doc.to_text() for p,doc in parsed.items() if doc.to_text().encode(edu.ENCODING)!=originals[p]}
    inputs={'project':sheets.revision(project),'files':{str(p):hashlib.sha256(b).hexdigest() for p,b in originals.items()}}
    token=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
    diffs=[]
    for path,text in texts.items():
        label=str(path.relative_to(fresh.root)) if path.is_relative_to(fresh.root) else str(path)
        diff=list(difflib.unified_diff(originals[path].decode(edu.ENCODING).splitlines(),text.splitlines(),fromfile=label,tofile=label,lineterm=''))
        diffs.append({'file':label,'diff':'\n'.join(diff[:500]),'truncated':len(diff)>500})
    return fresh,originals,texts,{'plan_token':token,'changes':changes,'files':diffs,'units':len(changes)}


def preview(mod,project):return plan(mod,project)[3]


def apply(mod,project,token):
    fresh,originals,texts,result=plan(mod,project)
    if not token or result['plan_token']!=token:sheets.fail(_i18n.msg('eng.sheets.native_preview_changed','Unit preview changed; review it again before applying'))
    if not texts:sheets.fail(_i18n.msg('eng.sheets.native_no_changes','There are no unit changes to apply'))
    if any(path.read_bytes()!=blob for path,blob in originals.items()):sheets.fail(_i18n.msg('eng.sheets.native_files_changed','A unit file changed after preview'))
    main=texts.pop(fresh.edu_path,'')
    notes=[json.dumps(c,ensure_ascii=False) for c in result['changes']]
    building_plan=buildings.BuildingPlan(mod=fresh,line='Unit sheet edits',edu_text=main,
        eop_texts={str(p):t for p,t in texts.items()},changes=notes,atomic_text=True,
        log_mode='edit',log_action='unit-sheets')
    try:return buildings.apply_edit(building_plan)
    except Exception:
        for path,blob in originals.items():
            if path.read_bytes()!=blob:buildings._atomic_edb_write(path,blob)
        raise
