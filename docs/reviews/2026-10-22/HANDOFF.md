# Google-TTS-For-NVDA engineering handoff

Review date: **22 October 2026**. All findings remain **OPEN**. This handoff contains proposed repairs and release checks; no source fixes or new runtime acceptance are claimed.

**Reviewed source:** [`main` at `2593b5409c29417965cd34db645a63ecdcaf6af7`](https://github.com/wwongw21/Google-TTS-For-NVDA/tree/2593b5409c29417965cd34db645a63ecdcaf6af7).

The full structured handoff is in [report.json](report.json). Historical commands retain their original review-workspace paths; read the prerequisites before running them. A new portable source probe is attached under [evidence](evidence/portable_probe.json). The original `/workspace/review/edge_nvda.json` and browser-capture logs were not available in this checkout and were not recreated.

## Audience and required outcome

### Audience

1. NVDA add-on maintainer

2. Simplified Chinese translator

3. Accessibility/runtime acceptance reviewer

4. Release packager

### Outcome

#### Summary

One confirmed Low defect remains OPEN: the zh_CN locale has stale 0.5.5 release information and lacks the new 0.6 background-runtime strings. Python/JavaScript syntax and the isolated Linux packaging build passed; all-locale validation failed for zh_CN.

#### Review mode

Read-only source review, localization validation and isolated packaging check

#### Source change status

No project source edits, commits, pushes or releases

#### Scope limit

No independently reproduced Windows/NVDA runtime defect was established. Passing syntax and packaging do not establish usable screen-reader speech, cancellation or standby behavior.

#### Counts

##### Open low

1

##### Closed

0

#### Release decision

Update and validate zh_CN before representing localization as current. Windows, NVDA and browser/WASM acceptance still need an actual supported runtime.

## Scope and reviewed branches

1. Repository AGENTS constraints

2. synth startup/queue/cancel/teardown and speech cache

3. browser/CDP bridge and local HTTP path handling

4. standby handoff and voice package storage/verification

5. catalog/dependency handling

6. updater core/download/UI lifecycle

7. packaging and localization

## Architecture

### Product

Windows NVDA synthesizer add-on exposing Google's bundled WASM TTS engine through an installed Chromium browser runtime, with user-managed voice packages.

### Runtime flow

1. The global plugin registers settings, voice-manager UI, optional startup update checks and optional background browser-runtime standby preparation.

2. SynthDriver loads the bundled engine/catalog, filters installed usable voice packages, creates a WavePlayer and either claims a ready standby bridge or creates one.

3. NVDA speech sequences enter a worker queue. The driver segments text, resolves normal settings or automatic language profiles, handles indexes/prosody and uses a short in-memory PCM cache.

4. ChromeTtsBridge coordinates BrowserProcessManager, CdpClient and WasmTtsEngineBridge. A loopback HTTP server serves the harness, bundled engine and installed voice packages.

5. The selected Chrome/Edge/Brave runtime loads the harness. CDP Runtime.evaluate invokes synthesis; Runtime.bindingCalled returns base64 PCM audio and progress events.

6. Python validates PCM and feeds nvwave.WavePlayer. Cancellation and teardown must stop queued/current work and release or terminate browser/CDP resources.

7. Voice Manager explicitly downloads/imports/removes packages. The updater independently checks a stable manifest, validates downloaded size/SHA256 and delegates installation to NVDA.

### Components

#### Item 1

##### Paths

1. googleTtsForNvda/synthDrivers/googleTtsForNvda/__init__.py

##### Responsibility

NVDA synth driver, worker queue, settings, language profiles, segmentation, indexes, silence shortening, PCM cache and player lifecycle

#### Item 2

##### Paths

1. googleTtsForNvda/synthDrivers/googleTtsForNvda/bridge.py

##### Responsibility

Loopback server and path handling, browser startup/fallback/profiles, CDP transport, WASM request/events, runtime recycle and cleanup

#### Item 3

##### Paths

1. googleTtsForNvda/synthDrivers/googleTtsForNvda/standby.py

##### Responsibility

Optional background readiness, directory-change watchers, bridge handoff and cancellation

#### Item 4

##### Paths

1. googleTtsForNvda/synthDrivers/googleTtsForNvda/catalog.py

2. googleTtsForNvda/synthDrivers/googleTtsForNvda/voice_store.py

##### Responsibility

Engine/catalog inspection, language/speaker/package metadata, dependencies, package storage and size/SHA256 verification caches

#### Item 5

##### Paths

1. googleTtsForNvda/synthDrivers/googleTtsForNvda/language_detector.py

2. googleTtsForNvda/synthDrivers/googleTtsForNvda/cld2

##### Responsibility

Automatic language detection and architecture-specific Windows CLD2 DLL selection

#### Item 6

##### Paths

1. googleTtsForNvda/synthDrivers/googleTtsForNvda/web/bridgeHarness.js

2. googleTtsForNvda/synthDrivers/googleTtsForNvda/WasmTtsEngine/20260723.1

##### Responsibility

Browser harness and bundled Google WASM engine; audio processing and session-token guarding

#### Item 7

##### Paths

1. googleTtsForNvda/globalPlugins/googleTtsForNvda/settings.py

2. googleTtsForNvda/globalPlugins/googleTtsForNvda/voiceManager.py

3. googleTtsForNvda/globalPlugins/googleTtsForNvda/uiUtils.py

##### Responsibility

Settings, voice package operations and accessible read-only status controls

#### Item 8

##### Paths

1. googleTtsForNvda/globalPlugins/googleTtsForNvda/updater.py

2. googleTtsForNvda/globalPlugins/googleTtsForNvda/updateGui.py

3. make_update_manifest.py

##### Responsibility

Stable update metadata, download verification, UI/controller state and release-manifest generation

#### Item 9

##### Paths

1. build_i18n.py

2. TRANSLATING.md

3. googleTtsForNvda/locale

##### Responsibility

Source-string extraction, translation checks, .mo compilation and localized manifest generation

##### Review relevance

NVDA-1 belongs to this workflow.

#### Item 10

##### Paths

1. build.bat

2. build.sh

3. googleTtsForNvda/manifest.ini

4. googleTtsForNvda/buildInfo.json

##### Responsibility

Version/build metadata, syntax/conflict/voice-data checks and .nvda-addon ZIP packaging

### Declared support

#### Minimum nvda

2024.1.0

#### Last tested nvda in manifest

2026.1.0

#### Evidence limit

These are repository declarations; this review did not run NVDA 2024.1 or 2026.1.

#### Platforms

Interactive speech runtime requires Windows and a supported installed Chrome, Edge or Brave browser.

#### Edge runtime

Microsoft Edge WebView2 is required when Edge is the effective browser runtime; Chrome and Brave must not acquire this requirement.

### Review coverage

1. Synth startup/queue/cancel/teardown and speech cache

2. Browser/CDP bridge and loopback file routing

3. Standby handoff and package verification/storage

4. Catalog/dependency handling

5. Updater core and UI/controller lifetime

6. Localization and build scripts

### Contracts to preserve

1. Voice downloads are explicit Voice Manager actions; speech and preload must never download packages.

2. Expose only installed usable voices and preserve dependency relationships.

3. Long operations remain off the NVDA GUI thread; workers marshal UI changes through wx.CallAfter.

4. Cancellation must remain responsive and late audio must not enter another request or the cache.

5. Use focusable read-only controls with real label association for status/help text; localized strings must remain wrapped in the translation mechanism.

6. Background readiness remains off by default and disabled in secure mode.

7. Keep Chrome/Edge/Brave fallback, runtime-specific profiles, cancellation propagation and bridge ownership intact.

8. Retain size/SHA256 verification for packages/updates and the existing loopback path-safety/isolation controls.

9. Do not bundle .zvoice files, browser profiles or __pycache__ in the add-on.

10. The localized changelog must match the base manifest version; generated .mo and localized manifests come from source translations.

11. Try the configured browser runtime first, then Chrome, Edge and Brave with duplicates removed. If process startup, speech-page discovery, CDP setup or harness readiness fails, clean up that attempt and try the next usable runtime. Cancellation must stop startup without trying a fallback. If Edge lacks WebView2, skip it when Chrome or Brave can run; show the WebView2 repair prompt only when no usable fallback remains and Edge WebView2 is the blocking condition.

### Test inventory

No automated interactive/runtime test suite was found. build.sh validates conflicts, Python/JavaScript syntax, source-tree voice-data exclusion and archive structure; build_i18n.py provides concrete localization validation. These checks do not establish NVDA speech or accessibility behavior.

## Immediate mitigations

### Item 1

#### Finding

NVDA-1

#### Action

Treat zh_CN release notes as stale and consult the current English 0.6 changelog when explaining the new background-readiness setting.

#### Limit

This does not translate the new setting/status strings or make the localized package current. Default background readiness remains off; do not silently enable it as a workaround.

### Item 2

#### Finding

NVDA-1

#### Action

Keep the localization failure visible in release review and avoid claiming all supported translations are current until the check passes.

#### Limit

The normal packaging script can succeed while localization is incomplete because i18n is intentionally a separate workflow.

## Implementation sequence

### Item 1

#### Step

1

#### Action

Pin the candidate to the reviewed snapshot and reproduce the zh_CN-only failure using the existing check-only command.

#### Dependencies

None recorded.

#### Completion

The existing failure and generated/source ownership are understood; no runtime refactor is needed.

### Item 2

#### Step

2

#### Action

Update zh_CN source translations for the 0.6 changelog and every missing background-runtime setting/status message.

#### Dependencies

1. 1

#### Findings

1. NVDA-1

### Item 3

#### Step

3

#### Action

Remove/retire obsolete 0.5.5 source entries as required by the validator, preserving translator-authored current translations and formatting placeholders.

#### Dependencies

1. 2

### Item 4

#### Step

4

#### Action

Generate zh_CN .mo/localized manifest using build_i18n.py, then run the complete all-locale check.

#### Dependencies

1. 3

#### Completion

No zh_CN missing/obsolete source errors; other locale checks remain green.

### Item 5

#### Step

5

#### Action

Inspect generated diffs and build the candidate add-on in an isolated checkout using the existing package builder.

#### Dependencies

1. 4

#### Completion

Correct translated files are packaged; root manifest and exclusion rules remain correct.

### Item 6

#### Step

6

#### Action

Perform Simplified Chinese settings/release-info acceptance on supported Windows NVDA; separately record broader runtime acceptance still not exercised here.

#### Dependencies

1. 5

#### Completion

The translated controls and 0.6 release information are verified using NVDA itself.

## Findings and implementation handoff

### NVDA-1 Low: Simplified Chinese release text, help and runtime translations are stale

**Status:** OPEN. [Pinned source](https://github.com/wwongw21/Google-TTS-For-NVDA/blob/2593b5409c29417965cd34db645a63ecdcaf6af7/googleTtsForNvda/locale/zh_CN/manifest.ini#L3).

#### Evidence classification

Confirmed

#### Observed mechanism

The Simplified Chinese localized manifest/changelog still describes version 0.5.5 while the base manifest is 0.6. The locale catalog also lacks the new background browser runtime setting and status strings.

#### Impact and scope

Simplified Chinese users receive stale release information and English fallback text for the new background-readiness feature. The repository's all-locale validation fails for this locale.

#### Repair direction

Update zh_CN source translations/changelog to 0.6, add all new background-runtime setting/status messages, update the localized help page, regenerate the .mo and localized manifest, then run the all-locale check. Manually compare the translated settings, memory/runtime-file warning and release information with the English help page; `build_i18n.py` does not validate localized help-page content.

#### Verification already obtained

python build_i18n.py --check --all-languages reports zh_CN missing changelog/new runtime strings and obsolete 0.5.5 msgid. ru, uk, vi and zh_TW pass. NVDA locale language-code validation was skipped because NVDA is not installed.

#### Confidence

Confirmed

#### Related locations

##### Item 1

###### File

googleTtsForNvda/locale/zh_CN/LC_MESSAGES/nvda.po

###### Lines

965-969

###### Purpose

Obsolete 0.5.5 changelog msgid

##### Item 2

###### File

googleTtsForNvda/globalPlugins/googleTtsForNvda/settings.py

###### Lines

274-285

###### Purpose

Current translatable background-runtime labels

##### Item 3

###### File

googleTtsForNvda/globalPlugins/googleTtsForNvda/settings.py

###### Lines

499-506

###### Purpose

Current translatable background-runtime status messages

##### Item 4

###### File

googleTtsForNvda/manifest.ini

###### Lines

6-14

###### Purpose

Current version 0.6 and source changelog

#### Detailed handoff evidence

The zh_CN localized manifest still begins its changelog with 0.5.5. The all-locale checker reports a missing 0.6 manifest changelog, six missing background-runtime setting/status messages, and an obsolete 0.5.5 msgid. ru, uk, vi and zh_TW passed the same selected categories.

#### User impact

Simplified Chinese users see outdated release information and English fallback text for the new optional background-ready browser runtime feature.

#### Change surface

##### Item 1

###### File

googleTtsForNvda/locale/zh_CN/LC_MESSAGES/nvda.po

###### Ownership

Translator-authored source; update strings and changelog here.

##### Item 2

###### File

googleTtsForNvda/locale/zh_CN/LC_MESSAGES/nvda.mo

###### Ownership

Generated binary; regenerate with build_i18n.py, never hand-edit.

##### Item 3

###### File

googleTtsForNvda/locale/zh_CN/manifest.ini

###### Ownership

Generated localized manifest; regenerate from the source catalog.

##### Item 4

###### File

googleTtsForNvda/locale/nvda.pot

###### Ownership

Template output may be refreshed by the build workflow; inspect any generated diff before inclusion.

#### Missing messages

1. &Keep Google TTS browser runtime ready in the background

2. Background browser runtime status

3. Keep Google TTS browser runtime ready in the background

4. Off. Google TTS For NVDA will start the browser runtime only when you choose Google TTS as the current synthesizer.

5. On. Google TTS For NVDA is the current synthesizer, so no separate background browser runtime will be started.

6. On. After you press OK or Apply, Google TTS For NVDA can keep the browser runtime ready in the background. This may use more memory and keep runtime files open until you turn it off or exit NVDA.

#### Missing message caveat

The full long enabled-status message was read from settings.py:506-508 for this handoff; the original checker console abbreviated it. Use current extraction if source changes before implementation.

#### Concrete repair steps

1. Read TRANSLATING.md and use the current extracted source messages; do not translate from a shortened console diagnostic.

2. Add reviewed Simplified Chinese translations for the new background-readiness labels/status strings and the exact version 0.6 source changelog.

3. Preserve accelerator markers, formatting placeholders, punctuation and multiline PO quoting.

4. Retire the obsolete 0.5.5 changelog entry to satisfy the repository's obsolete-source check; do not delete unrelated current translations.

5. Run python build_i18n.py --language zh_CN to regenerate the .mo and localized manifest, then inspect the generated files/diff.

6. Run python build_i18n.py --check --all-languages; supply a real NVDA locale directory when available to also validate NVDA language-code support.

7. Update googleTtsForNvda/doc/zh_CN/readme.html to describe the background-readiness setting, its extra memory and open-runtime-files warning, and the Version 0.6 release notes.

8. Manually compare the zh_CN and English help pages for the setting, warnings and release information. Record that comparison separately because build_i18n.py checks gettext catalogs/manifests, not localized help-page completeness.

9. Package and inspect the candidate in an isolated checkout, then verify the Simplified Chinese UI with an actual NVDA installation.

#### Invariants

1. Runtime behavior and the default-off background-readiness setting do not change.

2. zh_CN localized release information describes the same version and feature semantics as the base manifest.

3. The enabled-status text accurately states that background readiness may use additional memory and keep runtime files open until disabled or NVDA exits.

4. All translated placeholders remain equivalent to source placeholders; accelerators remain usable.

5. Generated .mo and localized manifest remain consistent with nvda.po.

6. Other locales, voice catalogs, languageSort.json, engine files and package/download behavior are unaffected.

7. No translated text promises that browser startup timing is completely fixed.

#### Acceptance criteria

1. The all-locale validator reports no zh_CN missing translation or obsolete source-string errors.

2. The localized manifest contains the 0.6 changelog rather than 0.5.5 release information.

3. On NVDA with a Simplified Chinese UI, the checkbox, group/status label and off/on messages are translated and understandable.

4. The checkbox retains a working accelerator and the status field remains keyboard focusable with its label read before the read-only edit role.

5. Settings preview still saves only through OK/Apply; Cancel does not persist a change.

6. Other four currently validated locales continue passing.

7. The final archive includes the regenerated zh_CN files and excludes __pycache__, .zvoice data and browser profiles.

8. The translated help page contains the background-readiness setting, the memory/runtime-files warning and Version 0.6 release information, as confirmed by a manual comparison against the English help page.

#### Regression scenarios

1. Background readiness off, on while Google TTS is current, and on while another synth is current.

2. Settings OK/Apply versus Cancel with the runtime-ready checkbox changed.

3. Long translated status strings wrap and remain fully readable through keyboard review.

4. Translator placeholder/accelerator/multiline quoting mistakes are caught by checks or manual review.

5. Fresh installation versus updating an existing add-on: correct localized release information is visible in the resulting package.

6. No unrelated locale or normal speech setting changes in the diff.

#### Risks

1. Editing generated .mo or manifest directly can appear to fix the archive while the next i18n build overwrites the repair.

2. A translation can pass structural checks yet misstate the memory/startup trade-off; native-language review is still needed.

3. Longer translated strings may expose Windows dialog layout issues that Linux syntax/build checks cannot detect.

4. A full i18n build may refresh a shared template or other generated outputs; keep the final diff restricted and inspect it.

#### Rollback

Revert the zh_CN source and its generated artifacts together if a translation/layout regression is found, rebuild the package and mark the localization defect OPEN again. Avoid reverting runtime code or changing version/support declarations as part of this translation rollback.

#### Help-page comparison

At the pinned source, the English help page documents the optional background-readiness setting, says it is off by default, and warns that enabling it may use more memory and keep runtime files open until disabled or NVDA exits. The Simplified Chinese help page lists browser selection/status but omits that setting and warning. Its newest release heading is Version 0.5.5, while the English help page includes Version 0.6. The source catalogs and localized manifest are not a completeness check for this HTML help page, so the planned repair includes a direct manual comparison.

#### Detailed handoff validation

##### Recorded status

CONFIRMED

##### Command

```
python /workspace/repos/Google-TTS-For-NVDA/build_i18n.py --check --all-languages
```

##### Recorded result

FAILED for zh_CN; ru, uk, vi and zh_TW passed.

##### Limitations

NVDA language-code support check was skipped because no installed NVDA locale folder was available.

##### Post repair status

NOT RUN

## Source directory

/workspace/repos/Google-TTS-For-NVDA

## Snapshot

### Branch

main

### Commit

2593b5409c29417965cd34db645a63ecdcaf6af7

### Review date

2026-10-22

### Manifest version

0.6

## Checks and reproductions

### Item 1

#### Name

All-locale check

#### Command

```
python /workspace/repos/Google-TTS-For-NVDA/build_i18n.py --check --all-languages
```

#### Prerequisites

1. Python 3.12.14 was used

2. Repository source and locale files

3. No Windows/NVDA required for structural checks

#### Side effects

Check-only; no generated translations written.

#### Recorded result

FAILED for zh_CN only. ru, uk, vi and zh_TW passed the selected structural categories.

#### Recorded errors

1. zh_CN: missing translation for manifest changelog beginning Version 0.6

2. Missing new background runtime checkbox/name/status translations

3. Obsolete source string beginning Version 0.5.5

#### Recorded warning

NVDA locale folder was not found; language-code support check is skipped.

#### Interpretation

This is the direct reproduction for NVDA-1. Structural translation validation is separate from screen-reader/UI acceptance.

### Item 2

#### Name

Candidate translation regeneration

#### Command

```
python build_i18n.py --language zh_CN
python build_i18n.py --check --all-languages
```

#### Working directory

A writable candidate checkout of Google-TTS-For-NVDA

#### Prerequisites

1. Corrected zh_CN nvda.po

2. Python

3. Optional real NVDA locale directory via --nvda-locale-dir

#### Recorded result

NOT RUN; these are future implementation commands.

#### Side effects

The first command writes the template, .mo and localized manifest; it belongs only in the future authorized repair workflow.

### Item 3

#### Name

Python syntax

#### Command

```
python - <<'PY'
from pathlib import Path
ps = list(Path('/workspace/repos/Google-TTS-For-NVDA').rglob('*.py'))
for p in ps:
    compile(p.read_bytes(), str(p), 'exec')
print(len(ps), 'Python files compile')
PY
```

#### Prerequisites

1. Python 3.12.14 was used

#### Recorded result

PASS: all 30 Python sources compile.

#### Interpretation

Does not import NVDA-only modules, load CLD2 DLLs or run Windows code.

### Item 4

#### Name

Harness JavaScript syntax

#### Command

```
node --check /workspace/repos/Google-TTS-For-NVDA/googleTtsForNvda/synthDrivers/googleTtsForNvda/web/bridgeHarness.js
```

#### Prerequisites

1. Node.js available

#### Recorded result

PASS

#### Interpretation

Syntax only; no browser/WASM engine or audio worklet execution.

### Item 5

#### Name

Isolated Linux package build

#### Command

```
bash build.sh
```

#### Working directory

/workspace/review/nvda-build-177bd6ea

#### Preparation

Copied the reviewed repository to this disposable directory with .git and __pycache__ excluded. The builder was run in that copy to preserve the original checkout.

#### Prerequisites

1. Bash

2. python3

3. Node.js

4. zip

5. Standard GNU utilities used by build.sh

#### Recorded result

PASS: all seven build stages completed; exit code 0.

#### Recorded stages

1. Build-artifact cleanup

2. Conflict-marker scan

3. Python syntax

4. JavaScript syntax

5. No .zvoice files in source

6. Removal of generated __pycache__

7. ZIP packaging

#### Artifact

##### Path

/workspace/review/nvda-build-177bd6ea/dist/googleTtsForNvda-0.6.nvda-addon

##### Bytes

10765832

##### Archive entries

99

##### Manifest at root

true

##### Pycache entries

0

#### Interpretation

The builder intentionally does not run build_i18n.py. A green package build therefore coexists with the confirmed localization failure.

### Item 6

#### Name

Archive structure inspection

#### Command

```
python - <<'PY'
from pathlib import Path
import zipfile
package = next(Path('/workspace/review/nvda-build-177bd6ea/dist').glob('*.nvda-addon'))
with zipfile.ZipFile(package) as archive:
    names = archive.namelist()
    print('archive_files=', len(names), 'manifest_at_root=', 'manifest.ini' in names, 'pycache_files=', sum('__pycache__' in name for name in names))
PY
```

#### Prerequisites

1. Python standard library

2. The existing isolated build artifact

#### Recorded result

PASS: 99 entries, manifest.ini at root, zero __pycache__ entries.

#### Interpretation

Archive structure only; does not establish successful NVDA installation or speech.

### Item 7

#### Name

Windows package build

#### Command

```
build.bat
```

#### Working directory

A disposable Windows candidate checkout

#### Prerequisites

1. Windows

2. Python and Node.js on PATH

3. PowerShell/archive tooling required by the existing script

#### Recorded result

NOT RUN

#### Interpretation

Existing supported Windows packaging entry point; its checks still do not replace actual NVDA runtime acceptance.

### Item 8

#### Name

Pinned-source portable handoff probe

#### Command

```
python docs/reviews/2026-10-22/evidence/portable_probe.py
```

#### Prerequisites

1. Python 3

2. Pinned source commit `2593b5409c29417965cd34db645a63ecdcaf6af7` available in the local Git object store

#### Recorded result

PASS: eight source-control-flow probes using fake collaborators. The direct English/zh_CN help comparison confirmed the missing setting/warning and stale 0.5.5 release heading.

#### Interpretation

The probe runs selected functions from the pinned source with fake process, CDP and harness collaborators. It checks runtime order, cleanup/fallback, cancellation and Edge WebView2 selection logic. It does not run native browser processes, WebView2, NVDA, screen-reader accessibility or speech. Native acceptance remains NOT RUN.

## Remaining acceptance

### Browser-runtime fallback acceptance

**Status:** NOT RUN on native Windows/NVDA. The attached portable probe checks source control flow with fake collaborators only.

1. With each saved runtime configured, confirm it is tried first, followed by Chrome, Edge and Brave with duplicates removed.
2. Cause a process-launch or speech-page/WebSocket discovery failure after startup; confirm the failed process/profile is cleaned up before the next runtime starts.
3. Cause CDP connection, domain setup or harness-readiness failure; confirm the failed runtime is closed and the next usable runtime is tried.
4. Cancel during startup or CDP/harness readiness; confirm cancellation propagates and no fallback runtime starts.
5. With Edge selected, Edge executable present, WebView2 missing and Brave usable, confirm Edge is skipped and Brave starts without a WebView2 prompt.
6. With Edge executable present, WebView2 missing and no usable Chrome/Brave fallback, confirm the WebView2 repair prompt is shown. If Edge itself is unavailable, confirm the generic no-runtime message is used.

### Item 1

#### Status

NOT RUN

#### Area

Simplified Chinese accessibility and wording

#### Prerequisites

1. Supported Windows NVDA installation using Simplified Chinese UI

2. Candidate add-on

3. Native-language reviewer

#### Criteria

1. Verify translated checkbox/status names and 0.6 changelog.

2. Tab through the status field; confirm real label association, wrapping and arrow-key review.

3. Verify accelerator, OK/Apply and Cancel behavior.

### Item 2

#### Status

NOT RUN

#### Area

Supported NVDA architecture/version coverage

#### Prerequisites

1. Supported 32-bit and 64-bit NVDA environments as applicable to declared support

2. Candidate package

#### Criteria

1. Install/load the add-on on the intended supported versions.

2. Confirm correct CLD2 DLL selection and representative English/Vietnamese language detection.

3. Do not infer architecture compatibility from the Linux compile run.

### Item 3

#### Status

NOT RUN

#### Area

Browser/WASM speech

#### Prerequisites

1. Windows user session

2. Chrome, Edge or Brave

3. Edge WebView2 when Edge is effective

4. At least one explicitly installed usable voice package

#### Criteria

1. Speak short and long text through the actual WASM engine.

2. Verify audio output, rate/pitch/volume, boundary indexes and output-device change behavior.

3. Confirm missing voices prompt clearly and do not auto-download.

### Item 4

#### Status

NOT RUN

#### Area

Cancellation, synth switching and standby

#### Prerequisites

1. NVDA runtime with candidate package

2. Usable voices and browser runtime

#### Criteria

1. Cancel during browser startup, preload and active speech; no late audio enters the next request.

2. Switch away during speech/preload and back again; no hung NVDA thread or orphan browser.

3. Test background readiness off and on, Voice Manager package-change refresh, and secure-mode gating.

4. Verify normal settings and automatic-language profile paths.

### Item 5

#### Status

NOT RUN

#### Area

Voice package operations and live downloads

#### Prerequisites

1. Explicitly chosen Voice Manager package operation

2. Network access to configured package source

#### Criteria

1. Verify install/import/remove feedback and dependency order on actual NVDA.

2. Verify size/SHA256 rejection and cleanup on failed package data.

3. Verify operations and progress remain accessible and do not block the main thread.

### Item 6

#### Status

NOT RUN

#### Area

Updater/runtime installation

#### Prerequisites

1. Controlled trusted update fixture or approved release package

2. NVDA installer UI

#### Criteria

1. Verify check/download/cancel/install lifecycle independently of Settings panel lifetime.

2. Verify size and checksum failure handling, temporary-file cleanup, no-update silence for startup checks, and manual error feedback.

3. Do not test by publishing or replacing a real release.

### Item 7

#### Status

NOT RUN

#### Area

Browser-runtime fallback on native Windows/NVDA

#### Criteria

1. Verify configured runtime order, failure cleanup/fallback after process launch and CDP/harness readiness, and cancellation without fallback.

2. Verify Edge without WebView2 falls through to usable Brave without an Edge prompt, and shows the WebView2 repair prompt only when no usable fallback remains.

## Evidence files

1. [Portable probe source](evidence/portable_probe.py)

2. [Portable probe result](evidence/portable_probe.json)

The historical `/workspace/review/edge_nvda.json`, browser-capture logs and Linux package artifact are not present in this checkout. Their recorded results above remain historical report entries; they are not attached artifacts and were not recreated.

## Handoff completion

NVDA-1 remains OPEN. No localization repair or native Windows/NVDA runtime acceptance is claimed. The portable probe is source-level evidence from the pinned snapshot and does not certify a release.

## Delivery and diagnostic files

### Destination repository

wwongw21/Google-TTS-For-NVDA

### Status

All findings remain OPEN; documentation transfer only.

### Portable evidence

This JSON retains the complete repository-specific handoff. The attached portable probe was captured from the pinned Git source on 22 October 2026. Historical `/workspace` paths are report references only, not portable links to included artifacts.

### Diagnostics included

1. `docs/reviews/2026-10-22/evidence/portable_probe.py` — rerunnable source-level probe using fake browser/CDP collaborators.

2. `docs/reviews/2026-10-22/evidence/portable_probe.json` — captured result and limitations.

### Not included

The original `/workspace/review/edge_nvda.json`, browser-capture logs and historical Linux package artifact were unavailable in this checkout and were not recreated. Original environments, model weights, user data and complete source snapshots are also not included. The portable probe checks pinned source control flow with fakes; it is not a live runtime test or a substitute for those original artifacts.


## Remaining review limits

1. Windows NVDA, Chrome/Edge/Brave runtime, CLD2 DLL execution, voice package synthesis, screen-reader accessibility, and live cancellation/standby races could not be exercised on Linux.

2. No automated runtime test suite found; release builder checks syntax/package structure, which does not prove screen-reader runtime behavior.

3. No independently confirmed security vulnerability found in reviewed paths; not a formal security scan.

