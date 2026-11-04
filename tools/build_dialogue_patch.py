"""Deploy all available translations, not a deliberately reduced milestone subset."""
import csv,json,re
from pathlib import Path
from package_patch import build_package
ROOT=Path(__file__).resolve().parents[1]
def main():
    rows=list(csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig')))
    def visible(s):return re.sub('<[^>]+>','',s)
    eligible=[r for r in rows if re.search('[A-Za-z]',visible(r['source']))]
    remaining=[r for r in eligible if r['status']=='todo']
    timed=[r for r in rows if '<time=' in r['source']]
    assert all(r['status']=='reviewed' and re.search('[\u0600-\u06ff]',r['target']) for r in timed)
    translated=sum(r['status'] in ('draft','reviewed') for r in eligible)
    extra=dict(phase=75,revision='dialogue_r1',phase_status='expanded_translation_draft',
        source_untranslated_entries=len(remaining),untranslated_entries=len(remaining),
        total_text_entries=len(eligible),translated_or_reviewed_entries=translated,
        coverage_basis='All available text translations; not reviewed quality or complete game assets',
        native_speaker_labels_suppressed=True,speaker_names_integrated_on_right=True,
        reviewed_timed_entries=len(timed),reviewed_video_timelines=['intro','dlc1_intro','dlc2_intro','dlc2_outro_good','dlc2_outro_bad'])
    build_package(ROOT/'06_build/stage',ROOT/'07_patch/phases/75_dialogue_r1','metro_arabic_75_dialogue_r1.vfs0',extra)
    (ROOT/'03_translation/review/remaining_after_dialogue.json').write_text(json.dumps(remaining,ensure_ascii=False,indent=1),encoding='utf-8')
    print('All 39 timed entries reviewed; remaining other entries:',len(remaining))
if __name__=='__main__':main()
