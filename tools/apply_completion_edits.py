"""Reviewed completion corrections for the user's loading/dialogue examples."""
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    path=ROOT/'03_translation/overrides_by_id.json'
    edits=json.loads(path.read_text(encoding='utf-8'))
    effects={'[chuckles]':'[ضحكة خافتة]','[Laughter]':'[ضحك]',
        '[Cough]':'[سعال]','[A quiet whimper]':'[أنين خافت]',
        '[A short, agreeing growl]':'[زمجرة قصيرة موافقة]',
        '[A short, quiet angry growl]':'[زمجرة غاضبة قصيرة وخافتة]',
        '<ffx:wonder_strong>- [Gasp] -':'<ffx:wonder_strong>- [شهقة] -',
        '<a mutant in the cage growls>AAAARGGGGHHHHHH!':'<a mutant in the cage growls>آآآآآه!'}
    rows=list(csv.DictReader((ROOT/'03_translation/tables/game.csv').open(encoding='utf-8-sig')))
    for r in rows:
        if r['source'] in effects:edits[r['id']]=effects[r['source']]
    prefix='voices\\m3_02_dead_moscow\\'
    edits['voices\\m3_10_yamantau\\yam_099_cannibal_attack_03_08']='ييييه!'
    edits['voices\\m3_dlc2\\dlc2_001_enteringtown_03_01']='همم، ترى ما سبب تلك الضوضاء...'
    edits[prefix+'dmc_000_narration_01']=(
        '<tab>بعد سنوات لم يسمع فيها أحد عبر المذياع سوى التشويش والضجيج، من سيظل يؤمن بأننا لسنا وحدنا على هذه الأرض؟'
        '<br><br><tab>زوجتي، ورفاقي في التنظيم، وأصدقائي، وأهل محطتي... لا أحد يصدقني. إنهم واثقون من أن المذياع لا يلتقط شيئًا، وأنه لم ينج أحد من الحرب الأخيرة سوى من احتموا بمترو موسكو مثلنا. نحن وحدنا على هذا الكوكب، وهذه حقيقة يعرفها الجميع في المترو.'
        '<br><br><tab>لكنني سمعت ذلك النداء عبر المذياع بأذني! نعم، غطاه التشويش فورًا، لكنني سمعته! وهذا يعني أن هناك، في مكان ما تحت السماء، بقعة لا تزال صالحة للعيش. لسنا محكومين بقضاء بقية حياتنا تحت الأرض!'
        '<br><br><tab>ومع ذلك، لا أحد يصدقني...<br><br>')
    edits[prefix+'dmc_000_narration_part1']=(
        '<tab>بعد سنوات لم يسمع فيها أحد عبر المذياع سوى التشويش والضجيج، من سيظل يؤمن بأننا لسنا وحدنا على هذه الأرض؟ زوجتي، ورفاقي في التنظيم، وأصدقائي، وأهل محطتي... لا أحد يصدقني.<br><br>')
    edits[prefix+'dmc_004_02_spartanscene_01_19']=(
        '<ffx:smile>عفوًا أيها السادة! أفسحوا الطريق! <ffx:wonder>أرتيوم! بضع ندبات أخرى، <ffx:wide_smile_light>ولن تستطيع أي امرأة مقاومة سحرك! <ffx:wonder>وبالمناسبة، كيف كانت الممرضات في المستشفى؟<ffx:neutral>')
    path.write_text(json.dumps(edits,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Reviewed exact-source sound effects and the reported Moscow loading/dialogue examples')
if __name__=='__main__':main()
