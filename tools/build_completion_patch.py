"""Package all extracted text, retaining the distinction between coverage and QA."""
import csv,json,argparse
from pathlib import Path
from package_patch import build_package
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--revision',default='text_complete_r1');args=ap.parse_args()
    assert args.revision in ('text_complete_r1','rtl_r1','repair_r1','review_r1','spelling_r1','spelling_r2','loading_r1','graphics_label_r1','diary_r1','input_spacing_r1','formal_terms_r1','formal_terms_r2','formal_terms_r3','formal_terms_r4','comprehensive_r1','comprehensive_r2','comprehensive_r3','final_review_r1')
    report=json.loads((ROOT/'08_qa/audit/localization_build.json').read_text())
    assert not report['issues'] and not report['statuses'].get('todo',0)
    rows=list(csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig')))
    assert len(rows)==38221
    extra=dict(phase=100,revision=args.revision,phase_status='complete_extracted_text_draft',
        total_entries=report.get('runtime_entries',len(rows)),statuses=report['statuses'],supplemental_reviewed_entries=report.get('supplemental_reviewed_entries',0),source_untranslated_entries=0,
        coverage_basis='100% of extracted LNG entries assigned; not a claim of fully reviewed game assets',
        speaker_names_integrated_on_right=True,native_speaker_labels_suppressed=True,
        dialogue_color='white',speaker_color='orange',color_method='complementary_native_control_overlay',
        color_runtime_verified=False,runtime_tested=False)
    if args.revision=='rtl_r1':extra.update(arabic_base_direction='rtl',wrap_before_bidi=True,alignment='native_metric_right_padding',loading_click_time_ms=1,rtl_animation_supported=False)
    if args.revision in ('repair_r1','review_r1','spelling_r1','spelling_r2','loading_r1','graphics_label_r1','diary_r1','input_spacing_r1','formal_terms_r1','formal_terms_r2','formal_terms_r3','formal_terms_r4','comprehensive_r1','comprehensive_r2','comprehensive_r3','final_review_r1'):extra.update(dialogue_color='white',speaker_color='white_pending_independent_color_fix',
        color_method='single_native_control_full_font',native_subtitle_controls=1,invisible_padding=False,
        masked_fonts=False,loading_timing='restored_original',arabic_base_direction='rtl',wrap_before_bidi=True)
    if args.revision in ('loading_r1','graphics_label_r1','diary_r1','input_spacing_r1','formal_terms_r1','formal_terms_r2','formal_terms_r3','formal_terms_r4','comprehensive_r1','comprehensive_r2','comprehensive_r3','final_review_r1'):extra.update(loading_alignment='native_right_1',loading_wrap='actual_regular_glyph_advances',rtl_typewriter_fixed=False)
    if args.revision in ('diary_r1','input_spacing_r1','formal_terms_r1','formal_terms_r2','formal_terms_r3','formal_terms_r4','comprehensive_r1','comprehensive_r2','comprehensive_r3','final_review_r1'):extra.update(diary_alignment='native_right_1',diary_wrap='actual_regular_glyph_advances',diary_tabs_removed_at_render=True,native_loading_companion='loading_complete_r1')
    if args.revision in ('input_spacing_r1','formal_terms_r1','formal_terms_r2','formal_terms_r3','formal_terms_r4','comprehensive_r1','comprehensive_r2','comprehensive_r3','final_review_r1'):extra.update(input_icon_words_separated_before_shaping=True,skip_prompt_gap='two_regular_spaces_each_side')
    build_package(ROOT/'06_build/stage',ROOT/f'07_patch/phases/100_{args.revision}',
        f'metro_arabic_100_{args.revision}.vfs0',extra)
if __name__=='__main__':main()
