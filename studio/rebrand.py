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
    # No community Discord button: an empty slot keeps the layout code as is (upstream #581 layout).
    ('crates/ui-egui/src/header.rs', '    let discord = Rect::from_min_max(pos2(rx - (10.0 + 14.0 + 6.0 + label.size().x + 12.0), cy - 13.0), pos2(rx, cy + 13.0));',
     '    // Creative Studio: no community Discord button yet.\n    let _ = label;\n    let discord = Rect::from_min_max(pos2(rx, cy - 13.0), pos2(rx, cy + 13.0));'),
    ('crates/ui-egui/src/header.rs', """    let dc = Color32::from_rgb(0x58, 0x65, 0xf2);
    p.rect_filled(discord, 13.0, if dresp.hovered() { dc.gamma_multiply(1.2) } else { dc });
    icons::paint(&p, Rect::from_center_size(pos2(discord.min.x + 17.0, cy), vec2(14.0, 14.0)), Icon::Chat, Color32::WHITE);
    p.galley(pos2(discord.min.x + 30.0, cy - label.size().y / 2.0), label, Color32::WHITE);
""", ''),
    ('crates/ui-egui/tests/it/ui_keyframes.rs', 'assert_eq!(copied, ["EffectCraft: 1 keyframe"]', 'assert_eq!(copied, ["effectat: 1 keyframe"]'),
    ('crates/ui-egui/tests/ui_panels.rs', """    // Padding 10, the 14 px icon, a 6 px gap, the text, padding 12.
    assert!((e.rect[2] - (text + 42.0)).abs() < 0.5, "{} for a {text} px label", e.rect[2]);""", """    // Creative Studio: no Discord pill; its slot is empty.
    let _ = text;
    assert!(e.rect[2].abs() < 0.5, "{} wide", e.rect[2]);"""),
    ('crates/ui-egui/src/header.rs', 'use crate::icons::{self, Icon};', 'use crate::icons::Icon;'),
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
        if not path.exists():
            continue
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


# Creative Studio: the macOS app folder in the .dmg and the volume name carry our name
# (packaging/macos/package.sh). Bundle and binary names inside the package stay as upstream has them.
PACKAGING_NAMES = {
    'packaging/macos/package.sh': [
        ('EffectCraft.app', 'effectat.app'),
        ('-volname "EffectCraft"', '-volname "effectat"'),
        ('-hfs-volume-name "EffectCraft"', '-hfs-volume-name "effectat"'),
    ],
}


def apply_packaging_names() -> list:
    changed = []
    for rel, pairs in PACKAGING_NAMES.items():
        path = ROOT / rel
        src = path.read_text(encoding='utf-8')
        out = src
        for a, b in pairs:
            out = out.replace(a, b)
        if out != src:
            path.write_text(out, encoding='utf-8')
            changed.append(path)
    return changed


# Creative Studio: effectat saves projects as `.effectat` (the same contents as upstream's `.ecproj`,
# which still opens). crates/project gets STUDIO_EXTENSION next to upstream's EXTENSION; the save
# defaults, dialog filters, autosave slots and the macOS document type follow it. `.ecprojx` (the XML
# copy, Save a Copy As XML) keeps its name. Applied as is, without the general rename.
EXT_BLOCK = '''
/// The extension upstream EffectCraft saves projects with; still opened.
pub const EXTENSION: &str = "ecproj";
/// The extension effectat saves projects with: the same contents as [`EXTENSION`].
pub const STUDIO_EXTENSION: &str = "effectat";

/// Is `ext` (without the dot, any case) a project file extension, `.effectat` or `.ecproj`?
pub fn is_project_ext(ext: &str) -> bool {
    ext.eq_ignore_ascii_case(STUDIO_EXTENSION) || ext.eq_ignore_ascii_case(EXTENSION)
}
'''
EXT_FILES = {
    'crates/project/src/lib.rs': [
        ('pub const APP_VERSION: &str = env!("CARGO_PKG_VERSION");\n',
         'pub const APP_VERSION: &str = env!("CARGO_PKG_VERSION");\n' + EXT_BLOCK),
    ],
    'crates/engine/src/autosave.rs': [
        ('const EXT: &str = "ecproj";', 'const EXT: &str = effectcraft_project::STUDIO_EXTENSION;'),
        ('auto-save N.ecproj', 'auto-save N.effectat'),
    ],
    'apps/effectcraft-web/src/store.rs': [
        ('Untitled Project auto-save 1.ecproj"));', 'Untitled Project auto-save 1.effectat"));'),
    ],
    'crates/engine/src/commands/file_more.rs': [
        ('format!("{folder}/{stem}.ecproj")', 'format!("{folder}/{stem}.{}", effectcraft_project::STUDIO_EXTENSION)'),
    ],
    'crates/engine/src/commands/import_project.rs': [
        ('lower.ends_with(".ecproj") || lower.ends_with(".ecprojx")',
         'lower.ends_with(".effectat") || lower.ends_with(".ecproj") || lower.ends_with(".ecprojx")'),
    ],
    'crates/engine/src/commands/watch_folder.rs': [
        ('p.extension().is_some_and(|x| x.eq_ignore_ascii_case("ecproj"))',
         'p.extension().and_then(|x| x.to_str()).is_some_and(effectcraft_project::is_project_ext)'),
    ],
    'crates/engine/src/media_browser.rs': [
        ('matches!(e, "ecproj" | "ectemplate" | "json5")', 'matches!(e, "effectat" | "ecproj" | "ectemplate" | "json5")'),
    ],
    'crates/project/src/render_queue.rs': [
        ('const PROJECT_EXTENSIONS: [&str; 2] = ["ecproj", "ecprojx"];',
         'const PROJECT_EXTENSIONS: [&str; 3] = ["effectat", "ecproj", "ecprojx"];'),
    ],
    'crates/ui-egui/src/lib.rs': [
        ('project: ext.eq_ignore_ascii_case("ecproj")', 'project: effectcraft_project::is_project_ext(&ext)'),
        ('if !ext.eq_ignore_ascii_case("ecproj")', 'if !effectcraft_project::is_project_ext(&ext)'),
    ],
    'crates/ui-egui/src/prefs_live.rs': [
        ('l.ends_with(".ecproj") || l.ends_with(".ecprojx")', 'l.ends_with(".effectat") || l.ends_with(".ecproj") || l.ends_with(".ecprojx")'),
    ],
    'crates/ui-egui/src/menus.rs': [
        ('Ask::Save("Untitled Project.ecproj")', 'Ask::Save("Untitled Project.effectat")'),
        ('Ask::Open(&["ecproj", "ecprojx"])', 'Ask::Open(&["effectat", "ecproj", "ecprojx"])'),
        ('"project Untitled Project.ecproj",', '"project Untitled Project.effectat",'),
        ('default: "Untitled Project.ecproj".into(), ext: "ecproj".into(), project: true',
         'default: "Untitled Project.effectat".into(), ext: "effectat".into(), project: true'),
    ],
    'crates/ui-egui/src/panels/unsaved.rs': [
        ('Untitled Project.ecproj', 'Untitled Project.effectat'),
    ],
    'crates/ui-egui/src/panels/home.rs': [
        ('Some("ecproj") => "effectat project",', 'Some("effectat" | "ecproj") => "effectat project",'),
    ],
    'apps/effectcraft/src/main.rs': [
        ('.is_some_and(|ext| ext.eq_ignore_ascii_case("ecproj") || ext.eq_ignore_ascii_case("ecprojx"))',
         '.is_some_and(|ext| ext.eq_ignore_ascii_case("effectat") || ext.eq_ignore_ascii_case("ecproj") || ext.eq_ignore_ascii_case("ecprojx"))'),
        ('add_filter("effectat Project", &["ecproj"])', 'add_filter("effectat Project", &["effectat", "ecproj"])'),
        ('add_filter("effectat Project", &["ecproj", "ecprojx"])', 'add_filter("effectat Project", &["effectat", "ecproj", "ecprojx"])'),
    ],
    'apps/effectcraft/src/sheet_dialogs.rs': [
        ('add_filter("effectat Project", &["ecproj", "ecprojx"])', 'add_filter("effectat Project", &["effectat", "ecproj", "ecprojx"])'),
        ('add_filter("effectat Project", &["ecproj"])', 'add_filter("effectat Project", &["effectat", "ecproj"])'),
    ],
    'apps/effectcraft-cli/src/main.rs': [
        ('position(|x| x.ends_with(".ecproj"))', 'position(|x| x.ends_with(".effectat") || x.ends_with(".ecproj"))'),
    ],
    'crates/engine/src/lib.rs': [
        ('#[cfg(test)]\nmod tests_settings;\n', '#[cfg(test)]\nmod tests_settings;\n#[cfg(test)]\nmod tests_studio_ext;\n'),
    ],
    'studio/CHANGES.md': [
        ('- App icon: the effectat tile (`assets/app-icon/`).\n',
         '- App icon: the effectat tile (`assets/app-icon/`).\n'
         '- Save format: projects save as `.effectat` (the same contents as `.ecproj`, which still opens), with the\n'
         '  effectat document icon (`assets/app-icon/effectat-document.*`); applied by `studio/rebrand.py`.\n'),
    ],
    'packaging/macos/package.sh': [
        ('cp "$ROOT/assets/app-icon/effectcraft.icns" "$APP/Contents/Resources/EffectCraft.icns"\n',
         'cp "$ROOT/assets/app-icon/effectcraft.icns" "$APP/Contents/Resources/EffectCraft.icns"\n'
         'cp "$ROOT/assets/app-icon/effectat-document.icns" "$APP/Contents/Resources/effectat-document.icns"\n'),
    ],
}
# Test expectations for the autosave slot names (`<stem> auto-save N.ecproj` is now `.effectat`).
EXT_TESTS = {
    'crates/engine/src/tests_settings.rs',
    'crates/automation/src/tests.rs',
}
EXT_REGEX = {
    'packaging/macos/Info.plist.in': [
        (r'<string>EffectCraft Project</string>', '<string>effectat Project</string>'),
        (r'(<key>CFBundleTypeIconFile</key>\s*<string>)EffectCraft(</string>)', r'\g<1>effectat-document\2'),
        (r'(<key>UTTypeIconFile</key>\s*<string>)EffectCraft(</string>)', r'\g<1>effectat-document\2'),
        (r'(<key>public\.filename-extension</key>\s*<array>\s*)<string>ecproj</string>',
         r'\1<string>effectat</string>\n          <string>ecproj</string>'),
        (r"EffectCraft's own format: the project \(\.ecproj\) and its XML copy \(\.ecprojx\)\.",
         r"effectat's own format: the project (.effectat; .ecproj still opens) and its XML copy (.ecprojx)."),
    ],
}
for _t in EXT_TESTS:
    EXT_REGEX.setdefault(_t, [])
    EXT_REGEX[_t].append((r'auto-save (\d+)\.ecproj', r'auto-save \1.effectat'))
# Collect Files writes the project as `.effectat`: the test looks for that file in the folder.
EXT_REGEX.setdefault('crates/automation/tests/qa/lifecycle.rs', []).append((r'f\.ends_with\("\.ecproj"\)', 'f.ends_with(".effectat")'))


def apply_extension() -> list:
    """Exact and regex rules: a pattern is skipped once its replacement is in the file, so a rerun changes nothing."""
    changed = []
    for rel in sorted(set(EXT_FILES) | set(EXT_REGEX)):
        path = ROOT / rel
        src = path.read_text(encoding='utf-8')
        out = src
        for a, b in EXT_FILES.get(rel, []):
            if b not in out:
                out = out.replace(a, b)
        for pat, rep in EXT_REGEX.get(rel, []):
            out = re.sub(pat, rep, out)
        if out != src:
            path.write_text(out, encoding='utf-8')
            changed.append(path)
    return changed


if __name__ == '__main__':
    main()
    for _p in apply_packaging_names():
        print('rebranded', _p.relative_to(ROOT))
    for _p in apply_extension():
        print('rebranded', _p.relative_to(ROOT))


# Creative Studio: the app's Arabic name in its Arabic interface (studio/arabic_names.py).
import sys  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import arabic_names  # noqa: E402
for _p in arabic_names.apply(ROOT, NAME, "تأثيرات"):
    print("rebranded", _p.relative_to(ROOT))
