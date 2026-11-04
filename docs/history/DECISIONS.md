# سجل القرارات
> سجل إلحاقي: لا يحذف قرار ولا يعدل. للتغيير أضف قرارا جديدا "يلغي D-00X".
> أضف بـ: `python tools/l10n_ws.py decision "القرار" --why "السبب" --evidence 08_qa/shots/...`

## D-001 — اعتماد معيار L10N-STD 1.0 لتنظيم ملفات المشروع
- التاريخ: 2026-11-02 · الدور: tech
- السبب: تنظيم واحد متزامن مع skills: game-arabization-workspace وgame-arabization (ومنها دليلا Unity وUnreal)

## D-002 — Offline-only development; no game launch. Visual Arabic rendering is an unverified assumption.
- التاريخ: 2026-11-02 · الدور: tech
- السبب: Explicit user request prohibits starting the game; only file-level checks and offline previews are permitted.

## D-003 — Keep current output as an incomplete private draft; do not install or publish as complete.
- التاريخ: 2026-11-02 · الدور: tech
- السبب: 941 entries remain untranslated after the public translation service returned HTTP 429; machine drafts still require review.

## D-004 — Install cumulative private text drafts at 25, 50 and 75 percent; keep 100 percent blocked until remaining entries and review are complete.
- التاريخ: 2026-11-02 · الدور: tech
- السبب: User explicitly requested staged installation at 25/50/75/100. Percentages count visible English text entries; game launch remains prohibited.
- يلغي: D-003

## D-005 — Correct settings manually and retain graphics technology names in English. Rebuild the LCD font with native independent R/G masks, opaque glyph alpha rectangles and separate-channel mipmaps.
- التاريخ: 2026-11-02 · الدور: tech
- السبب: User screenshots show poor small-screen text and incorrect settings translations; user requested English technology labels.
- الدليل: USER_HOME/Videos/Radeon ReLive/Metro Exodus/Metro Exodus_2026.11.02-13.09.png

## D-006 — Interpret source bitmap rectangle x/y as signed 16-bit coordinates before cropping; validate all packaged ASCII letters and digits across every localized font.
- التاريخ: 2026-11-02 · الدور: tech
- السبب: User screenshots match menu glyphs c/d/k/S disappearing. Original source x=65535 means -1, not an out-of-image positive position. Correct signed crops recover the exact missing glyphs; 496 packaged glyph checks pass.
- الدليل: 08_qa/render_tests/graphics_font_before_after.png

## D-007 — Build Arabic subtitles from logical speaker plus body, then wrap before visual reordering. Suppress native left-side actor prefixes and preserve each time-marker boundary independently. Install all available translations and reviewed cinematic timelines.
- التاريخ: 2026-11-02 · الدور: tech
- السبب: User screenshots show name on left, glued prefixes, reversed automatic wraps and English timed cinematics. Actor IDs were recovered from native sound records and dramatis personae. User requests names on the right and all cinematics translated.
- الدليل: 08_qa/render_tests/subtitle_order_preview.png

## D-008 — Deploy all extracted LNG text; white dialogue and unchanged orange right-side names use complementary native subtitle controls.
- التاريخ: 2026-11-02 · الدور: tech
- السبب: User explicitly confirmed separate colors. Original menu database supplies subtitle colors; source paragraph and dialogue examples were untranslated. 100 percent denotes extracted-table assignment, not complete linguistic or visual QA. Native overlay subscription requires user in-game confirmation.
- الدليل: 08_qa/audit/text_complete_r1.json

## D-009 — Apply explicit RTL Arabic globally and wrap logical prose before bidi; right-align traced text contexts using native font advances. Accelerate unsupported LTR loading reveal without claiming RTL animation.
- التاريخ: 2026-11-02 · الدور: tech
- السبب: User screenshots demonstrate LTR progressive reveal and rewrapping of visual Arabic. 31787 entries have alignment profiles, 695 dynamic prose entries still lack exact rectangle tracing. Preserve English technologies, numbers and orange speaker names. Never launch the game.
- الدليل: 08_qa/audit/rtl_r1.json

## D-010 — Withdraw masked subtitle overlay and invisible RTL padding after user screenshots showed names without dialogue and large loading gaps. Restore one native control, full font, original loader timing and ordinary logical wrapping.
- التاريخ: 2026-11-02 · الدور: tech
- السبب: In-game evidence invalidates the previous offline overlay and padding simulations. White speaker names are temporary; orange separation, exact right alignment and true RTL typewriter remain unfinished. Preserve all text coverage and cinematic timing.
- الدليل: 08_qa/audit/repair_r1.json
- يلغي: D-009

## D-011 — Install review_r1 with semantic corrections and two verified missing registry references; keep the stable single-control renderer.
- التاريخ: 2026-11-02 · الدور: tech
- السبب: User requests full completion. Main-table assignment is complete, but 36,839 sentences remain machine drafts. Normalize terms without falsely marking whole sentences reviewed; manually review 80 magazine UI strings and contextual errors. Append only the two absent keys explicitly referenced by current sound/menu/config registries. Do not equate table assignment with full asset or linguistic completion.
- الدليل: 08_qa/audit/review_r1.json، review_r1_coverage.json، review_r1_install_restore.json، 03_translation/review/*_review_receipt.json.
- الحدود: orange speaker name, exact native RTL alignment/typewriter and runtime confirmation remain unresolved. No game launch.

## D-012 — spelling_r1: conservative whole-table spelling scan and canonical settings/control glossary.
- التاريخ: 2026-11-02 · الدور: tech
- طلب المستخدم: تصحيح الإملاء وتوحيد أسماء الإعدادات. روجعت 213 تسمية و118 سياق همزة، وصُححت 48 جملة قصيرة. المجموع 284 خانة تغيرت. لا تستبدل همزة «إنه/أنه» آليًا بلا سياق؛ التصحيحات السياقية مقيدة بالمفاتيح التي فُحصت. لا تحول تصحيح كلمة إلى ادعاء مراجعة الجملة كلها.
- الدليل: 08_qa/audit/spelling_r1_language.json، spelling_r1.json، spelling_r1_install_restore.json.
- التركيب: حزمة مستقلة فريدة؛ فُحصت جميع بصمات الملفات المثبتة، والأصل قابل للاسترجاع. لا تشغيل للعبة ولا إعادة لتجارب العرض الفاشلة.

## D-013 — spelling_r2: continue inspected missing-hamza and imperative corrections.
- التاريخ: 2026-11-03 · الدور: tech
- الدليل: 203 changed entries, including 44 reviewed short contexts; all 213 settings labels retained. See 08_qa/audit/spelling_r2_language.json, spelling_r2.json and spelling_r2_install_restore.json. Changes traced in 03_translation/review/spelling_r2_changes.json.
- الضوابط: avoid global hamza substitutions for ambiguous words; reviewed context edits preserve native tags. 36,611 main entries remain machine drafts, no full linguistic certification or runtime claim. Keep withdrawn overlay/padding disabled and never launch the game.

## D-014 — loading_r1: native right alignment and metric wrapping for completed loading paragraphs.
- التاريخ: 2026-11-03 · الدور: tech
- طلب المستخدم: after Continue both reveal direction and completed text layout are wrong. Local read-only inspection established Left=0/Right=1/Center=2/Justify=3; four loading text controls were Justify=3. Patch to Right=1, font 22; preserve all geometry and clean loader timing. Strip native left tabs and blank separator lines in loading display only; source tables retain tags. Wrap before bidi using verified actual regular advances. No private spacer glyphs or executable edits.
- الدليل: loading_native_evidence.json، loading_r1_layout.json، loading_r1.json، loading_r1_install_restore.json. 283 changed loading entries only, 37940 others identical; Moscow fits ten estimated lines. Static reconstruction checked. Live payloads/EXE hashes verified.
- ما لم يُحل: native LTR typewriter animation. Do not call faster text RTL; withdrawn build_rtl_loader remains disabled. Runtime appearance untested; never launch game.

## D-015 — graphics_label_r1: honor VIDEO=الرسوميات; loading reveal fix remains unachieved after user evidence.
- التاريخ: 2026-11-03 · الدور: tech
- الدليل: user 12:54 screenshots show visual-prefix growth. Read-only investigation traced native reveal increment at 0x14072b30e and randomized delay at 0x14072b331. No verified data-only RTL/skip switch found; do not equate native alignment or faster timing with reversed reveal. No speculative timing/EXE edits.
- التركيب: only $video differs from loading_r1. All other text/assets identical; all 213 settings labels verified with updated glossary, live payload/EXE hashes checked. See graphics_label_r1_layout.json and loading_r1_user_failure.json. Never launch game.

## D-016 — loading_complete_r1: complete native loading text on its first reveal tick.
- التاريخ: 2026-11-03 · الدور: tech
- طلب المستخدم: «صلحه وبي أعلى جودة». بعد فشل المحاذاة وحدها، تتبع روتين الرسم الكامل وحدوده، ثم نفذ تعليماته الأصلية والمعدلة داخل محاكاة معزولة دون تشغيل اللعبة. التعديل يبدل زيادة العداد/قراءته في RVA 0x72b30e بموازنة عرض ثابتة ومحدودة. تُحفظ جميع فروع حدود السجلات والرسم الكامل وإكمال الصوت؛ لا تغيير للتوقيت ولا تجاوز حماية.
- الدليل: 08_qa/audit/loading_complete_r1_emulation.json: إعادة إنتاج الخلل القديم، 351 نص تحميل، حالات فارغة ومختلطة و300 سطر، ثبات الإطارات. 08_qa/audit/loading_complete_r1_install_test.json: تركيب/إزالة وإعادة تركيب واسترجاع بايتي ورفض إصدار مجهول، وإزالة موحدة تعيد الملف التنفيذي والفهرس.
- التركيب: 10 بايتات مختلفة ضمن 12 بايتًا؛ نسخة أمان أصلية متحققة ومثبت مقيد ببصمة الملف. الحزمة النصية graphics_label_r1 بقيت كما هي. وصفة الفرق فقط في 07_patch/native/loading_complete_r1. لا يُسمى العرض الكامل حركة كتابة RTL. الاختبار داخل اللعبة لم يحدث، وتأكيد المستخدم ما زال مطلوبًا.
- يتجاوز قيد عدم وجود تنفيذ متحقق في D-015 ببرهان محاكاة التعليمات، ولا يلغي ضرورة تأكيد المظهر الفعلي أو منع تشغيل اللعبة أو منع المباعدات/الخطوط المقنعة.

## D-017 — diary_r1: fix every collectible note and related reading screen with native right alignment and logical metric wrapping.
- التاريخ: 2026-11-03 · الدور: tech
- الدليل: user 16:14 screenshot shows left-aligned/justified note prose and a split «Missiles are flying» line. Menu 88 hint_desc was Justify=3, regular24, width650; menu42 journal uses typewriter18/width415. Both require their own actual font metrics. Menu100 advice shares the defective note layout. All three set Right=1; title right edges now match each body column. Original scrolling/font sizes retained. Tabs are removed before shaping, repeated blank breaks compacted, source tables keep logical tags.
- النطاق: 116 note bodies, 112 titles, 84 reference pages, 20 advice pages. 174 reviewed translations including all titles, complete screenshot note, all Moscow notes and all pause advice bodies. Remaining note prose is still partly machine draft; structural repair is not full language certification. 327 changed LNG entries, 37896 unrelated preserved. All loading strings and all fonts/atlases unchanged.
- التحقق: diary_r1.json, diary_r1_layout.json, diary_r1_install_restore.json. Actual atlas preview inspected, metric bounds for every line/title passed, only menu records42/88/100 added to existing51/67 patches. Full independent install + native companion + unified clean restore passed. Live hashes checked. Never launch game; user confirmation pending.

## D-018 — input_spacing_r1: separate Arabic words around input icons before shaping.
- التاريخ: 2026-11-03 · الدور: tech
- الدليل: skip screenshot shows joined «على/للتخطي». Original logical strings have no spaces around menu_ok/xpad_x, causing Arabic joining through the protected tag. A strict known-input whitelist inserts only missing separators in non-voice Arabic UI. Timing/format/voice tags excluded. Three reviewed skip variants use two normal spaces each side (16 actual regular-font units), preserving dynamic bindings.
- النطاق: 284 UI entries changed; 37939 preserved. Three skip variants match independently shaped words plus exact spaces. No note/journal/advice profile changes;26 loading icon hints get separation. Font/LNG chars unchanged; all non-LNG payloads byte-identical to diary_r1. See input_spacing_r1_spacing.json, input_spacing_r1.json and input_spacing_r1_live.json.
- التركيب: unique input_spacing_r1 payload with backup; all live hashes and native loading companion checked. Preview uses actual game glyphs and a representative E icon, not a game screenshot. Never launch game; runtime confirmation pending.

## D-019 — formal_terms_r1: formal Arabic meanings are the primary terminology rule.
- التاريخ:2026-11-03 · الدور:tech
- طلب المستخدم: no phonetic English such as كراوتش/ميدكيت; review terminology across the complete localization. Added formal_terms.json with68 labels,20 guarded contextual rules and inspected full phrases; normalize after translation memory and overrides so old drafts cannot restore those mistakes. Proper people/place names and explicit English graphics exceptions retained. Weapon barrels restricted to weapon keys to protect oil barrels.
- الدليل: formal_terms_r1_language.json covers38221 rows;201 changed runtime strings,38022 preserved,zero listed forbidden transliterations. Notes,dialogue and interface strings rendered from current logical targets; source tags/timelines preserved,all non-LNG assets identical. verify_repair_patch font/cue/menu checks pass; live hashes verified. Rule scan does not mark partially corrected sentences reviewed or claim full linguistic perfection. Never launch game.

## D-020 — formal_terms_r2: second contextual review, including grammar introduced by noun-only replacement.
- التاريخ:2026-11-03 · الدور:tech
- النطاق:57 explicit context edits plus canonical/rule cleanup;67 additional runtime changes,38156 preserved.75 labels/22 guarded rules,38221-row audit. Correct rate of fire/sight/shot/weapon receiver/barrel plural and grammar. Ranger mode is الحارس شديد الصعوبة. Preserve proper character names and source control/timing tags; oil barrels unchanged.
- الدليل:formal_terms_r2_language.json,formal_terms_r2.json,formal_terms_r2_live.json. All non-LNG assets identical to r1; live native companion unchanged. Main-table status does not falsely mark partly normalized draft sentences fully reviewed. Never launch game; runtime appearance and full sentence review not certified.

## D-021 — formal_terms_r3: third source-context review of tutorials and equipment.
- التاريخ:2026-11-03 · الدور:tech
- النطاق:40 explicit contextual edits plus label reuse,43 runtime entries changed,38180 preserved. Source pump “tops it off” restores pressure; bolts are crossbow arrows; knock-out is loss of consciousness. Corrected harness, buckshot, pneumatic/flamethrower pump instructions, knife retrieval and duplicate tutorials using the same source/bindings.79 labels,22 rules;38221-row terminology audit.
- الدليل:formal_terms_r3_language.json,formal_terms_r3.json,formal_terms_r3_live.json. Font chars336 unchanged,39 timed records/311 cues preserved,all non-LNG assets identical. Live executable loading companion and all payload hashes verified. No game launch; not full manual review of every dialogue sentence.

## D-022 — formal_terms_r4: additional contextual review of ammunition and protective equipment.
- التاريخ:2026-11-03 · الدور:tech
-31 complete contextual corrections in formal_terms_r4_context.json: ammunition rounds/slugs, monster shells, buckshot, armor construction and tradeoffs, carrier vest, detector and charger. No blanket replacements for ambiguous words; source meanings inspected.38221 rows audited;38192 unrelated runtime strings and all non-LNG assets identical. Names,control tags,39 timed records/311 cues,fonts and loading native companion preserved. Reports:formal_terms_r4_language.json,formal_terms_r4.json,formal_terms_r4_live.json. Never launch game; no claim of full manual sentence review.

## D-023 - comprehensive_r1: broad contextual review across localization categories.
- 2026-11-03.265 additional runtime corrections;160 dialogue,64 tasks,24 hints,9 diary/journal,6 interface,2 equipment.117 source-key contextual corrections,129 reviewed source phrases matching141 voice entries; source-guarded Aurora proper-name rule. Fix out-cold/carrying capacity/beasts/green-stuff idioms/cover fire/weapon tank and stock/family relationships/mission imperatives. Preserve approved people names,graphics exceptions,branch meanings and bindings.
- All38221 table rows rendered/audited;37958 other runtime strings and all non-LNG payloads identical to formal_terms_r4. Font336 characters unchanged,39 timed records/311 cues and10699 speaker lines pass.116 note/84 journal/20 advice profiles fit native metrics. Live index/all21 owned payloads/EXE companion verified;originals preserved. Never launched game.
- Evidence:08_qa/audit/comprehensive_r1_language.json,comprehensive_r1_integrity.json,comprehensive_r1.json,comprehensive_r1_live.json;human-readable08_qa/comprehensive_r1_review_ar.md. Most prose remains draft; all-row checks are not full manual proofreading or in-game certification. Orange speaker coloring remains pending.

## D-024 - comprehensive_r2: semantic follow-up for weapon names, journals and dialogue idioms.
-2026-11-03.95 additional runtime corrections (48 dialogue,18 equipment,13 UI,8 hints,8 notes/journal).55 full contexts,22 reviewed source phrases matching23 entries,12 unified labels. Magazine means ammo magazine;scope is optical;weapon pressure vents before long,not after a long time;submachine guns differ from light machineguns. Correct improvised equipment,weapon journal nuts/idioms,helmets and suit reference,combat reload calls,and context-dependent colloquial dialogue. Read adjacent turns to resolve Me too/Everyone did.
-38221 rows audited;38128 strings/all non-LNG assets byte-identical to comprehensive_r1. Preserve all earlier review files,originals,native loading_complete_r1,actor names,graphics exceptions,input tags,39 timed records/311 cues.116 notes/84 journal/20 advice pages fit actual metrics. Live index/all22 payloads and EXE verified. No game launch;not full manual proofreading;orange speaker name still pending.
-Evidence:08_qa/audit/comprehensive_r2_language.json,comprehensive_r2_integrity.json,comprehensive_r2.json,comprehensive_r2_live.json;08_qa/comprehensive_r2_review_ar.md. Current three verification commands use --revision comprehensive_r2.

## D-025 - comprehensive_r3: parallel contextual review, root approval and installed verification.
-2026-11-03.162 explicit source-key changes;63 dialogue,58 UI/other,23 hints,15 notes/journal,3 equipment.48 achievement-description rows include locked/unlocked pairs. Four proposal files (notes15,equipment32,dialogue38,names18),root achievements48 and misc11;root independently read originals and suggestions,corrected note speaker subject,clarified charger comparison and preserved one-month quantity naturally in words.162-row approval receipt kept with source/before/target/reason.
-Fix go-off Geiger sound,break-free command,medical item descriptions,ammo fouling,visor,light exposure;food nuts vs mechanical nuts,slaves vs slavers,smokehouse/pens/mailed fist,idioms and name references.27 capitalized Idiot occurrences are real name references;18 explicit corrections applied without changing name pipeline or generic insults.12 guitar references unified to formal Arabic;jam/shanty meanings corrected.
-38221-row render/tag audit;38061 runtime strings/all non-LNG payloads match comprehensive_r2. Numeric assertion caught canonical medkit normalization producing bad grammar;source rewritten to any of the medkits before final build. Narrow reviewed numeric equivalence:1mo -> one month in words in one provisions-note id;all other number tokens remain strict.39 timed records/311 cues,10699 speaker lines,font336 chars,116 notes/84 journal/20 advice metrics pass.11 graphics entries untouched. Live index/all23 owned payloads/native loading companion EXE verified. No game launch. Most prose remains draft;orange speaker color pending.
-Evidence:03_translation/review/comprehensive_r3_approved.json;08_qa/audit/comprehensive_r3_language.json,comprehensive_r3_integrity.json,comprehensive_r3.json,comprehensive_r3_live.json;08_qa/comprehensive_r3_review_ar.md. Three current verifiers use --revision comprehensive_r3.

## D-026 - final_review_r1: closing review of the current installed build.
-2026-11-03.11 confirmed residual corrections:7 UI/other,2 hints,1 dialogue,1 equipment. Correct Options>Video route to actual Arabic settings labels,aim border,Iron Mode title consistency,bear-threat subject,console ammo hold instruction,chambering,quicksave date order,downloading and one green-stuff phrase. No speculative broad replacements.
-Closing checks cover38221 rows with full normalize/spelling/input pipeline idempotence and all protected-format Counters;193 exact glossary settings and32 repeated control groups agree.Only11 approved IDs differ from comprehensive_r3;38212 runtime strings/all non-LNG payloads unchanged. Standard checks preserve39 timed records/311 cues,10699 speaker lines,actual reading/font metrics,English graphics exceptions. Live index/all24 owned payloads/native loading_complete_r1 EXE hashes verified. Original and backups preserved. Never launched game.
-Current three verification commands use --revision final_review_r1;tools/verify_final_review.py adds closure checks. Evidence:08_qa/audit/final_review_r1_closing.json,final_review_r1_language.json,final_review_r1_integrity.json,final_review_r1.json,final_review_r1_live.json;03_translation/review/final_review_r1_approved.json;08_qa/final_review_r1_review_ar.md. Final means closing current-build checks,not completed manual review of all dialogue or confirmed in-game appearance;independent orange speaker coloring remains pending.

## D-027 - Native Arabic installer, Windows EXE and Proton AppImage review.
- 2026-11-04. User requested both executable formats, Metro-inspired appearance and final design approval; clarified AppImage is for the Windows game under Proton and requires explicit instructions. Design approval remains pending; nothing published or installed in the live game.
- Python/PySide6 RTL UI, bundled OFL font, original geometric rail illustration, dark/orange palette, Steam library discovery, manual folder choice, edition/hash validation, offline delta reconstruction, atomic writes with lock/journal, verified original backup, rollback/recovery and restore. Optional text-language switch only; preserve audio, saves, unrelated configuration edits and historical installer payloads.
- Shipped differences: 477-byte forward index delta,412-byte reverse delta,2977383-byte asset delta plus version-locked loading recipe. No whole game EXE/archive redistributed. Preserves final_review_r1 and loading_complete_r1. Unknown editions, native Linux and conflicting modifications refused.
- Real Windows EXE startup initially exposed a dependency search contamination: unrelated Poppler ICU DLL and libheif API-set stubs were collected from the host PATH. Build now limits dependency search to the pinned Python/Qt and Windows directories, includes a matching vendor CRT set, rejects contaminated outputs. Final GUI EXE exits successfully in screenshot/review mode.
- Linux x86_64 ELF type2 runtime + SquashFS contains CPython3.12, Qt6.12 and Debian library closure/notices. It booted in isolated Linux/glibc2.36 via QEMU with no network/shared folders. Actual AppImage extract-and-run opened the Arabic Qt UI;20 backend cases passed. Windows20 backend +3 Qt-control cases passed; final EXE captured. Real asset/executable deltas installed,reinstalled,restored in private fixture;26 live game files byte-identical before/after.
- Evidence:08_qa/audit/installer_review.json,installer_windows_smoke.json,installer_real_transaction.json;08_qa/render_tests/installer_windows_exe.png,installer_linux.png;09_release/installer-review/build-metadata.json,SHA256SUMS.txt and source ZIP. Steam Deck hardware/Proton gameplay and in-game visuals not tested. Existing dialogue/manual-proofreading/orange speaker limitations are explicitly retained in About/README. Do not equate installer readiness with full linguistic certification or user design acceptance.

## D-028 - Publish the authorized repository and first public beta.
- 2026-11-04. User explicitly requested uploading the full current Arabic patch to exelight7/metro-exodus-arabic, publishing a GitHub Release and choosing a tag. This authorizes publication without another permission round, superseding D-027's earlier publication hold for this task. Chose v0.1.0-beta.1 to reflect existing manual-proofreading/runtime limits honestly.
- Preserved the owner's existing MIT LICENSE and initial commit. Added Arabic README with screenshot/downloads, Windows/Proton guide, QA/build docs, installer source/resources, font/dependency notices and logical Arabic data. Exported38221 id/target/status rows,37413 nonempty targets,808 intentionally empty originals; no nonempty source lacks a target. No original source-text bulk, full game archives/EXE, local receipts/backups, user paths or credentials published. Outbound scan105 source files;23 tests passed from the clean publication checkout.
- Source commit cd505aae10b24a504e750e7c998633fcf9df10b4 on main, annotated v0.1.0-beta.1. GitHub connector used for repository/profile/readback; existing scoped Git Credential Manager authentication used for Git and Releases because connector has no release-asset upload tool. Credentials remained in memory/child-only Git environment and were neither persisted nor printed.
- Created a draft, uploaded/verified all seven assets, then published as a public prerelease. Windows EXE43075872bytes,sha256 e8f23bc3f45984582d0c09781f68a06ce0791167ab0de2009192251edb21bee8;AppImage119773688bytes,sha25602f071edda49cadb64f0b92cce7e088e70cdc9b772e2129cb71184c672188b68. Other assets:source ZIP,INSTALLATION_AR.md,QA.json,build-metadata.json,SHA256SUMS.txt. Existing tested binaries unchanged.
- Public unauthenticated API confirms published/prerelease,tag-to-commit and seven uploaded sizes/SHA256 digests. Actual public guide download matches local hash. URL:https://github.com/exelight7/metro-exodus-arabic/releases/tag/v0.1.0-beta.1. Receipts:00_admin/github_release_receipt.json;08_qa/audit/github_publication_preflight.json,github_publication_verified.json. No game execution or live installation. Do not rewrite the published tag/assets; future changes receive a new tag.
