"""Audit the entire table against formal vocabulary and verify the actual package."""
import csv,json,re,collections,argparse
from pathlib import Path
from formal_terms import formal_terms,DATA,TAG
from subtitle_layout import GameRenderer
from verify_graphics_fonts import package
from metro_archive import index,extract
from audit_comprehensive_review import category
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--revision',default='formal_terms_r1');args=ap.parse_args()
    rows=list(csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig')))
    baseline={'formal_terms_r2':'formal_terms_r1','formal_terms_r3':'formal_terms_r2','formal_terms_r4':'formal_terms_r3','comprehensive_r1':'formal_terms_r4','comprehensive_r2':'comprehensive_r1','comprehensive_r3':'comprehensive_r2','final_review_r1':'comprehensive_r3'}.get(args.revision,'input_spacing_r1')
    before=package(baseline,100);after=package(args.revision,100)
    assert before['chars']==after['chars'] and before['fonts']==after['fonts']
    renderer=GameRenderer();changes=[];residual=[]
    forbidden=re.compile(r'(?<![\u0621-\u064a])(?:كراوتش|كرواتش|كروتش|ميدكيت|ميد كيت|ستيلث|كرافتينغ|كرافتنج|شوتجن|شوتغن|سنايبر|ريلود|توجل|فيلتر)(?![\u0621-\u064a])')
    for r in rows:
        key=r['id'];text=after['strings'][key]
        assert collections.Counter(TAG.findall(r['source']))==collections.Counter(TAG.findall(r['target'])),key
        assert text==renderer.render(key,r['target']),key
        if 'credits' not in key and forbidden.search(r['target']):residual.append(key)
        if text!=before['strings'][key]:
            assert formal_terms(key,r['source'],r['target'])==r['target'],('non-idempotent',key)
            assert (key in DATA['contextual'] or TAG.sub('',r['source']).strip().casefold() in DATA['labels'] or TAG.sub('',r['source']).strip() in DATA['voice_labels'] or any(re.search(rule['source'],TAG.sub('',r['source']),re.I) for rule in DATA['rules'])),key
            changes.append(dict(id=key,source=r['source'],target=r['target']))
    assert not residual,residual
    by={r['id']:r for r in rows}
    assert 'الانحناء' in by['m3_crouch_hint']['target']
    for k in ['$med_name','$medkit_easy_hint','menu_item_medkit_name']:assert 'حقيبة الإسعافات' in by[k]['target']
    assert by['menu_customize_nvscope_name']['target']=='منظار رؤية ليلية'
    assert by['menu_customize_cat_scope_name']['target']=='أدوات التصويب'
    if args.revision=='formal_terms_r3':
        assert by['ammo_arrows_name']['target']=='أسهم النشاب'
        for k in ['menu_customize_system_pneumo_autopump_dsc','menu_customize_system_pneumo_autopump_flame_dsc']:
            assert 'تعيده' in by[k]['target'] and 'بإيقافه' not in by[k]['target']
        assert 'إفقاده الوعي' in by['general_hint_81']['target']
    if args.revision=='formal_terms_r4':
        assert 'طلقات إضافية' in by['$general_hint_27']['target']
        assert 'جولات' not in by['$general_hint_27']['target']
        assert 'الرخويات' not in by['ammo_0_44_apinc_dsc']['target']
        assert 'الطلقة' not in by['ammo_12_70_dsc']['target']
        assert 'قذائف' not in by['m3_general_hint_46']['target']
    if args.revision in ('comprehensive_r1','comprehensive_r2','comprehensive_r3'):
        assert by['m3_dlc2_task_02_04']['target']=='اعثر على بدلات الحماية'
        assert 'فقداني الوعي' in by['m3_m08_des_brif_III_12_task_1_note']['target']
        assert 'إفقاده الوعي' in by['m3_loader_diary_desert_02_stun']['target']
        assert 'قتله دفاعا' in by['m3_loader_diary_desert_02_kill']['target']
        assert 'دبابة' not in by['$general_hint_15']['target']
        assert 'الكاشف الشامل' in by['m3_dlc02_general_hint_8']['target']
        assert 'كمية محددة' in by['m3_general_hint_56']['target']
        assert '50' in by['ACH_polite saboteur_DESC']['target']
        assert 'الطائرة' not in by['m3_m13_main_task_6_note']['target']
    if args.revision in ('comprehensive_r2','comprehensive_r3'):
        assert by['menu_customize_scope_low_name']['target']=='منظار 4X'
        assert by['menu_customize_scope_high_name']['target']=='منظار 6X'
        assert 'يتسرب سريعا' in by['$tihar_dsc']['target']
        assert 'أنقذت حياتي' in by['m3_dia_weapon_kalash_intro']['target']
        assert 'صواميله' in by['m3_dia_weapon_bastard_intro']['target']
        assert 'أسهمه' in by['m3_dia_weapon_helsing_intro']['target']
        assert 'مكسرات' not in by['m3_dia_weapon_bastard_intro']['target']
        for r in rows:
            if not r['id'].startswith('voices\\') and 'credits' not in r['id'] and re.search('magazin',r['source'],re.I):
                assert not re.search('مجلة|مجلات|مجلتك|المجل',r['target']),r['id']
    if args.revision=='comprehensive_r3':
        assert 'مكسرات' in by['m3_12_val_diary_23_dsc']['target']
        assert 'صواميل' not in by['m3_12_val_diary_23_dsc']['target']
        assert 'صواميله' in by['m3_dia_weapon_bastard_intro']['target']
        assert 'انفجار' not in by['m3_general_hint_33']['target']
        assert 'تحرر' in by['m3_08_final_yes']['target']
        assert 'أي من حقائب الإسعافات' in by['ACH_dlc_01_just_scratch_DESC']['target']
        assert 'سددت ثقب' in by['ACH_martian_DESC_unlocked']['target']
        assert 'أنت هناك' in by['m3_13_nvs_diary_6_dsc']['target']
        for r in rows:
            if r['id'].startswith('voices\\') and re.search(r'\bIdiot\b',r['source']):assert 'إيديوت' in r['target'],r['id']
            if re.search(r'\bguitar\b',r['source'],re.I):assert 'قيثارة' in r['target'],r['id']
    # Existing approved names and the explicit English graphics exceptions.
    for k in renderer.actors & after['strings'].keys():assert after['strings'][k]==before['strings'][k]
    for k in ['video_skip_hint','video_skip_hint_cstm','video_skip_hint_xbox','$video']:
        assert after['strings'][k]==before['strings'][k],k
    payloads=[]
    for rev in [baseline,args.revision]:
        folder=ROOT/f'07_patch/phases/100_{rev}';idx=index(folder/'patch_04.vfx')
        payloads.append({e['path']:extract(folder,idx,e) for e in idx['entries'] if e.get('pak')==len(idx['packs'])-1})
    changed_assets=[k for k in payloads[0] if payloads[0][k]!=payloads[1][k]]
    assert len(changed_assets)==1 and changed_assets[0].endswith('stable_us.lng')
    report=dict(revision=args.revision,audited_rows=len(rows),canonical_labels=len(DATA['labels']),context_rules=len(DATA['rules']),
        changed_entries=len(changes),unrelated_entries_preserved=len(after['strings'])-len(changes),
        forbidden_transliterations_remaining=residual,other_payloads_identical=True,canonical_speaker_names_preserved=True,
        tags_and_timelines_preserved=True,runtime_tested=False,changes=changes,
        language_scope='Whole-table terminology rules and contextual corrections; not a full manual sentence review.')
    report['audited_categories']=dict(collections.Counter(category(r['id']) for r in rows))
    report['changed_categories']=dict(collections.Counter(category(r['id']) for r in changes))
    if args.revision in ('comprehensive_r1','comprehensive_r2'):
        context_name,voice_name=('comprehensive_context_review.json','comprehensive_voice_review.json') if args.revision=='comprehensive_r1' else ('comprehensive_r2_context.json','comprehensive_r2_voice.json')
        context=json.loads((ROOT/'03_translation'/context_name).read_text(encoding='utf-8'))
        phrases=json.loads((ROOT/'03_translation'/voice_name).read_text(encoding='utf-8'))
        phrase_rows=[r['id'] for r in rows if r['id'].startswith('voices\\') and TAG.sub('',r['source']).strip() in phrases and len([s for s in re.split('(<[^>]+>)',r['source']) if s.strip() and not s.startswith('<')])==1]
        report.update(new_full_context_review_entries=len(context),new_exact_voice_phrases=len(phrases),matching_voice_entries=len(phrase_rows),reviewed_context_keys=list(context),reviewed_voice_keys=phrase_rows)
    if args.revision=='comprehensive_r3':
        reviewed=json.loads((ROOT/'03_translation/review/comprehensive_r3_approved.json').read_text(encoding='utf-8'))
        report.update(new_full_context_review_entries=reviewed['reviewed_entries'],root_reviewed=reviewed['root_reviewed'],reviewed_groups=dict(collections.Counter(r['category'] for r in reviewed['changes'])),numeric_word_equivalence=reviewed['number_in_words_exception'])
    if args.revision=='final_review_r1':
        context=json.loads((ROOT/'03_translation/final_review_r1_context.json').read_text(encoding='utf-8'))
        report.update(new_full_context_review_entries=len(context),reviewed_context_keys=list(context))
    (ROOT/f'08_qa/audit/{args.revision}_language.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['changes','reviewed_context_keys','reviewed_voice_keys']}))
if __name__=='__main__':main()
