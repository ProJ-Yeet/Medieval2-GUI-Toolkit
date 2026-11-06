"""Connect script editing to paths, game readers, backups and Undo.

Written independently from a description of the behaviour (2026-11-06); the feature follows Pfadfinder-Adam's campaign editor.
"""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from . import config, i18n as _i18n
from .logutil import log, file_op


def existing(base, *parts):
    """Resolve existing names without assuming filename case."""
    path = Path(base)
    for part in parts:
        direct = path / part
        if not direct.exists() and path.is_dir():
            direct = next((p for p in path.iterdir() if p.name.casefold() == part.casefold()), direct)
        path = direct
    return path


def game_root(mod):
    root = Path(mod.root).absolute()
    if root.parent.name.casefold() == 'mods':
        return root.parent.parent
    from . import gamepack
    saved = gamepack.game_root_of(mod)
    return Path(saved) if saved else Path(mod.data).parent


def loader(root):
    try:
        return b'listModules' in existing(root, 'script', 'main.nut').read_bytes()
    except OSError:
        return False


def destination(mod, filename):
    game = game_root(mod)
    root = Path(mod.root) if loader(mod.root) else game
    if not loader(mod.root) and not loader(game) and not existing(game, 'script').is_dir():
        root = Path(mod.root)
    return existing(root, 'script', 'modules', filename)


def library():
    if config.CONFIG_DIR is None:
        raise ValueError(_i18n.msg('eng.scriptaddons.the_tool_has_no_folder_of',
                                  'the tool needs its own folder to store add-ons'))
    path = Path(config.CONFIG_DIR) / 'script_modules'
    path.mkdir(parents=True, exist_ok=True)
    return path


def names(mod):
    out = {k: [] for k in ('factions', 'units', 'chains', 'levels', 'traits', 'ancillaries', 'towns', 'regions', 'characters')}
    if mod is None:
        return out
    def collect(key, read):
        try:
            out[key] = list(dict.fromkeys(read()))
        except (OSError, ValueError, AttributeError, KeyError):
            pass
    collect('factions', lambda: [p[0] for p in mod.factions() if p[0] != 'slave'] if hasattr(mod, 'factions')
            else [k for k in mod.faction_cultures if k != 'slave'])
    collect('units', lambda: [u.type for u in mod.edu.units])
    collect('chains', lambda: [b.name for b in mod.edb.buildings])
    collect('levels', lambda: [v for b in mod.edb.buildings for v in b.levels])
    from . import traits, ancillaries, campstrat
    collect('traits', lambda: [r['name'] for r in traits.overview(mod)['traits']])
    collect('ancillaries', lambda: [r['name'] for r in ancillaries.overview(mod)['ancillaries']])
    try:
        campaigns = campstrat.campaign_paths(mod)
        campaign = 'imperial_campaign' if 'imperial_campaign' in campaigns else next(iter(campaigns))
        nodes = campstrat.read_strat(mod, campaign).nodes
        out['towns'] = list(dict.fromkeys(str(n.get('region') or n.name) for n in nodes if n.kind == 'settlement'))
        out['regions'] = list(out['towns'])
        out['characters'] = [n.name for n in nodes if n.kind in ('character', 'character_record')]
    except (OSError, ValueError, StopIteration):
        pass
    return out


def town_names(mod):
    """Translate campaign region picks into console/Settlement identifiers."""
    if mod is None:
        return {}
    from . import campmap
    try:
        return {r.name: r.settlement for r in campmap.read_regions(mod).records if r.settlement}
    except (OSError, ValueError, AttributeError):
        return {}


class Plan:
    def __init__(self, mod):
        self.mod = mod
        self.writes = {}
        self.deletions = {}
        self.notes = []

    def binary(self, path, data):
        key = os.path.abspath(path)
        self.writes[key] = data
        self.deletions.pop(key, None)

    def delete(self, path, why=''):
        key = os.path.abspath(path)
        self.deletions[key] = why
        self.writes.pop(key, None)

    def note(self, _file, text):
        self.notes.append(text)

    def stored(self, path):
        key = os.path.abspath(path)
        if key in self.writes:
            return self.writes[key]
        try:
            return Path(key).read_bytes()
        except OSError:
            return None

    def display(self, path):
        path = Path(path).absolute()
        for root, prefix in ((Path(self.mod.data).absolute(), 'data/'), (game_root(self.mod).absolute(), '<game>/')):
            try:
                return prefix + path.relative_to(root).as_posix()
            except ValueError:
                pass
        return str(path)

    def words(self):
        return list(self.notes) + [
            _i18n.msg('eng.scriptcompat.writes', 'write {path}', path=self.display(p)) for p in self.writes
        ] + [_i18n.msg('eng.scriptcompat.deletes', 'take out {path}{why}', path=self.display(p),
                      why=f' ({why})' if why else '') for p, why in self.deletions.items()]

    def run(self, action, who, summary):
        if not self.writes and not self.deletions:
            raise ValueError(_i18n.msg('eng.scriptcompat.nothing', 'nothing to change'))
        tid = config.new_transfer_id()
        backup = config.backup_root_for(tid)
        manifest = dict(backed_up=[], created=[], outside_backed_up=[], outside_created=[])
        data_root = Path(self.mod.data).absolute()
        def preserve(path, writing):
            try:
                rel = path.relative_to(data_root).as_posix()
            except ValueError:
                rel = None
            if path.exists():
                saved = backup / 'data' / rel if rel is not None else backup / 'outside' / f'{len(manifest["outside_backed_up"]) + 1:03d}_{path.name}'
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, saved)
                if rel is None:
                    manifest['outside_backed_up'].append([str(path), str(saved)])
                else:
                    manifest['backed_up'].append(rel)
                file_op('BACKUP', path, f'-> {saved}')
            elif writing:
                manifest['created' if rel is not None else 'outside_created'].append(rel if rel is not None else str(path))
        for filename, blob in self.writes.items():
            path = Path(filename)
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = Path(filename + '.new')
            with temp.open('xb') as stream:
                stream.write(blob)
            preserve(path, True)
            os.replace(temp, path)
            file_op('WRITE', path, action)
        for filename in self.deletions:
            path = Path(filename)
            preserve(path, False)
            if path.exists():
                path.unlink()
                file_op('DELETE', path, action)
        rec = dict(id=tid, when=time.strftime('%Y-%m-%d %H:%M:%S'), mode='scripts', action=action,
                   source=self.mod.name, dest=self.mod.name, source_root=str(self.mod.root), dest_root=str(self.mod.root),
                   unit_type=who, resolved_type=who, options={}, applied=True, undone=False, note='', summary=summary,
                   warnings=[], manifest=manifest, backup_root=str(backup))
        config.append_log(rec)
        log.info('SCRIPTS %s %s in %s, id=%s', action, who, self.mod.name, tid)
        return rec
