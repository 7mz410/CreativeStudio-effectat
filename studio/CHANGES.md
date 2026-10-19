# effectat: changes from upstream EffectCraft

Required by the Apache License 2.0 (section 4b): files we changed carry this notice through
this list.

- Branding (user-visible only, applied by `studio/rebrand.py`): the app name effectat,
  the bundle id `ps.creative.studio.effectat`, Help links to studio.creative.ps and this repository. Crate names
  and file formats keep their upstream names.
- App icon: the effectat tile (`assets/app-icon/`).
- Save format: projects save as `.effectat` (the same contents as `.ecproj`, which still opens), with the
  effectat document icon (`assets/app-icon/effectat-document.*`); applied by `studio/rebrand.py`.
- Removed upstream's ArtCraft brand assets (`docs/brand/`), as their brand terms require of forks.
- README and NOTICE: the fork, its credits and the Creative Studio suite.
- The ArtCraft mark (tools bar, About) gives way to the effectat icon; the Help menu's links
  go to studio.creative.ps and this repository; the upstream Discord is labelled as the upstream community.
