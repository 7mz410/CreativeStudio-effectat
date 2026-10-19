//! effectat saves projects as `.effectat`; the same file under upstream's `.ecproj` still opens.

use serde_json::json;

use crate::Session;

#[test]
fn saved_projects_are_effectat_and_ecproj_still_opens() {
    let dir = std::env::temp_dir().join(format!("ec-studio-ext-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let mut s = Session::default();
    s.execute("comp.new", json!({"name": "Main", "width": 320, "height": 180, "duration": 2})).unwrap();
    let saved = dir.join("Intro.effectat");
    s.execute("file.saveAs", json!({"path": saved.to_string_lossy()})).unwrap();
    assert!(saved.is_file(), "Save As writes the .effectat file");
    // The same contents under the upstream extension still open.
    let legacy = dir.join("Old.ecproj");
    std::fs::copy(&saved, &legacy).unwrap();
    let mut t = Session::default();
    t.execute("file.open", json!({"path": legacy.to_string_lossy()})).unwrap();
    assert_eq!(*s.project, *t.project);
    let _ = std::fs::remove_dir_all(dir);
}

#[test]
fn autosave_slots_and_extensions_follow_effectat() {
    assert_eq!(crate::autosave::file_name("Intro", 2), "Intro auto-save 2.effectat");
    assert!(effectcraft_project::is_project_ext("EFFECTAT"));
    assert!(effectcraft_project::is_project_ext("ecproj"));
    assert!(!effectcraft_project::is_project_ext("ecprojx"));
}
