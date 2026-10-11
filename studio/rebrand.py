#!/usr/bin/env python3
"""Apply the effectat branding on top of upstream EffectCraft.

Only user-visible text is rebranded; crate names, file formats and other internals keep their
upstream names so `git merge upstream/main` stays easy. The script is idempotent: after merging
upstream, resolve any conflicts in favour of upstream and run it again.

    python3 studio/rebrand.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = 'effectat'
REPO = 'https://github.com/7mz410/CreativeStudio-effectat'
SITE = 'https://studio.creative.ps'
# Persisted names that saved catalogs and presets refer to; renaming them would break those.
KEEP = ('the EffectCraft authors', 'EffectCraft Intro')

# Exact replacements, applied before the general rename (and kept idempotent: skipped once done).
RTL_RULES = [
    ('crates/ui-egui/src/header.rs', 'use crate::icons::{self, Icon};', 'use crate::icons::Icon;'),
    ('crates/ui-egui/src/header.rs', '    let discord = Rect::from_min_max(pos2(rx - 104.0, cy - 13.0), pos2(rx, cy + 13.0));', '    // Creative Studio: no community Discord button yet (an empty slot keeps the layout code as is).\n    let discord = Rect::from_min_max(pos2(rx, cy - 13.0), pos2(rx, cy + 13.0));'),
    ('crates/ui-egui/src/header.rs', '    let dc = Color32::from_rgb(0x58, 0x65, 0xf2);\n    p.rect_filled(discord, 13.0, if dresp.hovered() { dc.gamma_multiply(1.2) } else { dc });\n    icons::paint(&p, Rect::from_center_size(pos2(discord.min.x + 16.0, cy), vec2(14.0, 14.0)), Icon::Chat, Color32::WHITE);\n    p.text(pos2(discord.min.x + 28.0, cy), Align2::LEFT_CENTER, tr("Discord"), Tokens::semibold(12.0), Color32::WHITE);\n', ''),
    ('crates/engine/src/tests.rs', 'unwrap()["url"], "https://github.com/storytold/effectcraft");', 'unwrap()["url"], "https://github.com/7mz410/CreativeStudio-effectat");'),
    # Links (crates/engine/src/links.rs) and the ArtCraft mark (upstream's docs/brand/, removed).
    ('crates/engine/src/links.rs', 'pub const WEBSITE: &str = "https://getartcraft.com";', 'pub const WEBSITE: &str = "https://studio.creative.ps";'),
    ('crates/engine/src/links.rs', 'pub const APP_PAGE: &str = "https://getartcraft.com/apps/effectcraft";', 'pub const APP_PAGE: &str = "https://studio.creative.ps";'),
    ('crates/engine/src/links.rs', 'pub const GITHUB: &str = "https://github.com/storytold/effectcraft";', 'pub const GITHUB: &str = "https://github.com/7mz410/CreativeStudio-effectat";'),
    ('crates/engine/src/links.rs', 'pub const ISSUES: &str = "https://github.com/storytold/effectcraft/issues";', 'pub const ISSUES: &str = "https://github.com/7mz410/CreativeStudio-effectat/issues";'),
    ('crates/ui-egui/src/header.rs', 'include_bytes!("../../../docs/brand/artcraft-mark.png")', 'include_bytes!("../../../assets/app-icon/effectcraft-1024.png")'),
]

SPECIFIC = {
}
# Exact replacements inside string literals and catalogs, before the general rename.
LITERALS = [
    ('EffectCraft on getartcraft.com', 'Creative Studio Website'),
    ('EffectCraft Home Page', 'Creative Studio Website'),
    ('ArtCraft Website', 'Creative Studio Project'),
    ('Join the ArtCraft Discord', 'Upstream Community on Discord'),
    ('Join the ArtCraft community on Discord', 'The upstream ArtCraft community on Discord'),
]

STRING = re.compile(r'"(?:[^"\\\n]|\\.)*"')


def rename(text: str) -> str:
    for a, b in LITERALS:
        text = text.replace(a, b)
    if any(k in text for k in KEEP):
        return text
    return text.replace('EffectCraft', NAME)


def rebrand_rust(path: Path) -> bool:
    src = path.read_text(encoding='utf-8')
    out = src
    for a, b in SPECIFIC.get(path.relative_to(ROOT).as_posix(), []):
        if not b or b not in out:
            out = out.replace(a, b)
    out = STRING.sub(lambda m: rename(m.group(0)), out)
    if out != src:
        path.write_text(out, encoding='utf-8')
    return out != src


def source_strings() -> set:
    """Every string literal in the (rebranded) Rust sources, without quotes."""
    found = set()
    for p in list((ROOT / 'crates').rglob('*.rs')) + list((ROOT / 'apps').rglob('*.rs')):
        found.update(m.group(0)[1:-1] for m in STRING.finditer(p.read_text(encoding='utf-8')))
    return found


SOURCES = None


def rebrand_locale(path: Path) -> bool:
    # Catalog rows are `context<TAB>English<TAB>translation`. A row is renamed only when its renamed
    # English text is a string the sources use (some crates outside the UI keep upstream's name),
    # and a second row for the same text (two upstream labels that rename alike) is dropped.
    global SOURCES
    if SOURCES is None:
        SOURCES = source_strings()
    src = path.read_text(encoding='utf-8')
    rows, seen = [], set()
    for line in src.split('\n'):
        cells = line.split('\t')
        if len(cells) >= 3 and not line.startswith('#'):
            renamed = rename(cells[1])
            if renamed != cells[1] and renamed in SOURCES:
                cells = [cells[0], renamed, *(rename(c) for c in cells[2:])]
                line = '\t'.join(cells)
            if (cells[0], cells[1]) in seen:
                continue
            seen.add((cells[0], cells[1]))
        rows.append(line)
    out = '\n'.join(rows)
    if out != src:
        path.write_text(out, encoding='utf-8')
    return out != src


def rebrand_plist(path: Path) -> bool:
    src = path.read_text(encoding='utf-8')
    out = re.sub(r'(<key>CFBundle(?:Display)?Name</key>\s*<string>)EffectCraft(</string>)', rf'\g<1>{NAME}\2', src)
    out = out.replace('<string>ai.storyteller.effectcraft</string>', '<string>ps.creative.studio.effectat</string>')
    if out != src:
        path.write_text(out, encoding='utf-8')
    return out != src


def RUST_FILES():
    return sorted((ROOT / 'crates/ui-egui/src').rglob('*.rs')) + sorted((ROOT / 'apps/effectcraft/src').rglob('*.rs')) + [ROOT / 'crates/engine/src/commands/frontend.rs', ROOT / 'crates/engine/src/commands/help.rs', ROOT / 'crates/engine/src/menus/tests.rs']


def apply_rtl_rules() -> list:
    changed = []
    for rel, a, b in RTL_RULES:
        path = ROOT / rel
        src = path.read_text(encoding='utf-8')
        if (not b or b not in src) and a in src:
            path.write_text(src.replace(a, b), encoding='utf-8')
            changed.append(path)
    return changed


def main():
    changed = apply_rtl_rules()
    # The engine's menu tree is one text block, not string literals: rename it line by line.
    tree = ROOT / 'crates/engine/src/menus.rs'
    src = tree.read_text(encoding='utf-8')
    out = '\n'.join(rename(l) if '|' in l or l.startswith('[mac] ') else l for l in src.split('\n'))
    if out != src:
        tree.write_text(out, encoding='utf-8')
        changed.append(tree)
    changed += [p for p in RUST_FILES() if rebrand_rust(p)]
    changed += [p for p in sorted((ROOT / 'crates/ui-egui/src/i18n').glob('*.tsv')) if rebrand_locale(p)]
    web = ROOT / 'apps/effectcraft-web/web/index.html'
    html = web.read_text(encoding='utf-8')
    branded = html.replace('<title>EffectCraft</title>', f'<title>{NAME}</title>').replace('Loading EffectCraft&hellip;', f"Loading {NAME}&hellip;").replace('Loading EffectCraft…', f'Loading {NAME}…').replace('content="EffectCraft:', f'content="{NAME}:')
    if branded != html:
        web.write_text(branded, encoding='utf-8')
        changed.append(web)
    plist = ROOT / 'packaging/macos/Info.plist.in'
    if plist.exists() and rebrand_plist(plist):
        changed.append(plist)
    for p in changed:
        print('rebranded', p.relative_to(ROOT))


if __name__ == '__main__':
    main()
