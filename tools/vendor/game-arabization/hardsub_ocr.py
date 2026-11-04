#!/usr/bin/env python3
"""
hardsub_ocr.py - recover BURNED-IN text (hardsubs, captions, signs) from a cutscene video
with timings, so it can be translated and re-burned in Arabic.

Pipeline: ffmpeg samples the subtitle region N times per second -> each frame is binarized
(white text with dark outline by default) -> Tesseract OCR -> identical/similar consecutive
frames are merged into timed lines -> SRT + CSV (id,start,end,source,target) for translators.

Usage
  hardsub_ocr.py cutscene.mp4 --region 0,560,1280,150            (x,y,w,h of the text band)
  hardsub_ocr.py movie.webm --region 0,900,1920,180 --fps 5 --lang eng --out movie_subs
  hardsub_ocr.py movie.mp4 --region ... --text-color dark        (black text on light boxes)
  hardsub_ocr.py movie.mp4 --region ... --text-color FFFF00:80   (yellow subtitles)
  hardsub_ocr.py movie.mp4 --region ... --outline                (busy/bright backgrounds)
  hardsub_ocr.py movie.mp4 --region ... --preview 12.5           (save the processed crop at 12.5 s)
Tips
  * get the region from one screenshot (any image viewer shows pixel coordinates)
  * higher --fps = tighter timings but slower; 4 is a good default for dialogue
  * Japanese/Korean source: --lang jpn / kor (install the tesseract language data)
  * OCR is a draft: proof-read the CSV against the video before translating
Needs: ffmpeg, ffprobe, tesseract (CLI), Pillow
"""
import argparse
import csv
import difflib
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter

from PIL import Image, ImageOps, ImageFilter


def probe(video):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                          'stream=width,height,r_frame_rate:format=duration', '-of', 'json', video],
                         capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    st = d['streams'][0]
    num, den = st['r_frame_rate'].split('/')
    return st['width'], st['height'], float(num) / float(den), float(d['format']['duration'])


def text_mask(im, threshold, text_color, outline):
    """RGB crop -> 'L' image, 0 = text pixel, 255 = background."""
    rgb = im.convert('RGB')
    r, g, b = rgb.split()
    if text_color == 'white':                  # white text: ALL channels bright (rejects yellow/cyan areas)
        from PIL import ImageChops
        m = ImageChops.darker(ImageChops.darker(r, g), b).point(lambda v: 255 if v >= threshold else 0)
    elif text_color == 'light':
        m = rgb.convert('L').point(lambda v: 255 if v >= threshold else 0)
    elif text_color == 'dark':
        m = rgb.convert('L').point(lambda v: 255 if v <= 255 - threshold else 0)
    else:                                      # RRGGBB[:tolerance]  e.g. FFFF00:80 for yellow subtitles
        col, _, tol = text_color.partition(':')
        tol = int(tol or 70)
        tr, tg, tb = int(col[0:2], 16), int(col[2:4], 16), int(col[4:6], 16)
        px = rgb.load()
        m = Image.new('L', rgb.size, 0)
        mp = m.load()
        for yy in range(rgb.height):
            for xx in range(rgb.width):
                pr, pg, pb = px[xx, yy]
                if abs(pr - tr) + abs(pg - tg) + abs(pb - tb) <= tol:
                    mp[xx, yy] = 255
    if outline:                                # keep only text pixels close to a dark outline/shadow
        dark = rgb.convert('L').point(lambda v: 255 if v < 70 else 0).filter(ImageFilter.MaxFilter(7))
        from PIL import ImageChops
        m = ImageChops.multiply(m, dark)
    return m.point(lambda v: 0 if v else 255)


def preprocess(path, threshold, text_color, outline=False):
    bw = text_mask(Image.open(path), threshold, text_color, outline)
    bw = bw.filter(ImageFilter.MedianFilter(3))
    bw = bw.resize((bw.width * 2, bw.height * 2), Image.LANCZOS)
    return ImageOps.expand(bw, border=20, fill=255)


def ocr(img_path, lang, psm):
    r = subprocess.run(['tesseract', img_path, 'stdout', '-l', lang, '--psm', str(psm)],
                       capture_output=True, text=True)
    t = r.stdout.replace('\x0c', '').strip()
    t = re.sub(r'[ \t]+', ' ', t)
    t = '\n'.join(l.strip() for l in t.splitlines() if l.strip())
    return t


def signature(im):
    small = im.resize((96, 24)).point(lambda v: 255 if v > 128 else 0)
    return small.tobytes()


def sig_diff(a, b):
    if a is None or b is None:
        return 1.0
    return sum(1 for x, y in zip(a, b) if x != y) / len(a)


def ts_srt(t):
    ms = int(round(t * 1000))
    return '%02d:%02d:%02d,%03d' % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='OCR burned-in subtitles to timed SRT/CSV.')
    ap.add_argument('video')
    ap.add_argument('--region', required=True, help='x,y,w,h of the text area')
    ap.add_argument('--fps', type=float, default=4.0, help='samples per second (default 4)')
    ap.add_argument('--lang', default='eng', help='tesseract language (eng, jpn, kor, ...)')
    ap.add_argument('--psm', type=int, default=6, help='tesseract page segmentation mode (6 = block)')
    ap.add_argument('--threshold', type=int, default=170, help='binarization threshold 0-255')
    ap.add_argument('--text-color', default='white',
                    help='white (default) | light | dark | RRGGBB[:tolerance] e.g. FFFF00:80')
    ap.add_argument('--outline', action='store_true',
                    help='keep only text pixels next to a dark outline/shadow (busy or bright backgrounds)')
    ap.add_argument('--similar', type=float, default=0.75, help='merge lines with similarity >= this')
    ap.add_argument('--min-chars', type=int, default=2)
    ap.add_argument('--out', help='output base name (default: video name)')
    ap.add_argument('--preview', type=float, help='only save the processed crop at this time (s) and exit')
    ap.add_argument('--keep-frames', action='store_true')
    a = ap.parse_args()
    for tool in ('ffmpeg', 'ffprobe', 'tesseract'):
        if not shutil.which(tool):
            sys.exit('%s not found in PATH' % tool)
    x, y, w, h = [int(v) for v in a.region.split(',')]
    W, H, vfps, dur = probe(a.video)
    if x < 0 or y < 0 or x + w > W or y + h > H:
        sys.exit('region %s is outside the %dx%d video' % (a.region, W, H))
    base = a.out or os.path.splitext(os.path.basename(a.video))[0] + '_ocr'
    tmp = tempfile.mkdtemp(prefix='hardsub_')

    if a.preview is not None:
        raw = os.path.join(tmp, 'p.png')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(a.preview), '-i', a.video, '-frames:v', '1',
                        '-vf', 'crop=%d:%d:%d:%d' % (w, h, x, y), raw], check=True)
        preprocess(raw, a.threshold, a.text_color, a.outline).save(base + '_preview.png')
        Image.open(raw).save(base + '_crop.png')
        print('saved %s_crop.png and %s_preview.png - adjust --region / --threshold until the text is clean'
              % (base, base))
        print('OCR of preview: %r' % ocr(base + '_preview.png', a.lang, a.psm))
        return 0

    print('video %dx%d %.3f fps %.2f s | sampling %.1f/s in region %s' % (W, H, vfps, dur, a.fps, a.region))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a.video, '-vf',
                    'fps=%s,crop=%d:%d:%d:%d' % (a.fps, w, h, x, y), os.path.join(tmp, 'f_%06d.png')], check=True)
    frames = sorted(glob.glob(os.path.join(tmp, 'f_*.png')))
    texts = []
    prev_sig = prev_text = None
    ocr_calls = 0
    for i, fp in enumerate(frames):
        im = preprocess(fp, a.threshold, a.text_color, a.outline)
        sig = signature(im)
        if prev_sig is not None and sig_diff(sig, prev_sig) < 0.01:
            t = prev_text                      # same picture -> same text, skip OCR
        else:
            pp = fp[:-4] + '_bw.png'
            im.save(pp)
            t = ocr(pp, a.lang, a.psm)
            ocr_calls += 1
        if len(re.findall(r'\w', t)) < a.min_chars:
            t = ''
        texts.append((i / a.fps, t))
        prev_sig, prev_text = sig, t
    # merge consecutive similar frames
    segs = []
    for t0, t in texts:
        if segs and t and segs[-1]['texts'] and \
                difflib.SequenceMatcher(None, segs[-1]['texts'][-1], t).ratio() >= a.similar and \
                abs(segs[-1]['end'] - t0) < 1.5 / a.fps:
            segs[-1]['texts'].append(t)
            segs[-1]['end'] = t0 + 1 / a.fps
        elif t:
            segs.append({'start': t0, 'end': t0 + 1 / a.fps, 'texts': [t]})
    rows = []
    for s in segs:
        if len(s['texts']) < 2 and a.fps >= 2:
            continue                           # one-frame flicker = noise
        best = Counter(s['texts']).most_common(1)[0][0]
        rows.append((s['start'], min(s['end'], dur), best))
    with open(base + '.srt', 'w', encoding='utf-8') as f:
        for n, (s, e, t) in enumerate(rows, 1):
            f.write('%d\n%s --> %s\n%s\n\n' % (n, ts_srt(s), ts_srt(e), t))
    with open(base + '.csv', 'w', encoding='utf-8-sig', newline='') as f:
        wr = csv.writer(f)
        wr.writerow(['id', 'start', 'end', 'source', 'target'])
        for n, (s, e, t) in enumerate(rows, 1):
            wr.writerow([n, ts_srt(s), ts_srt(e), t, ''])
    print('frames %d, OCR runs %d, lines %d -> %s.srt / %s.csv' % (len(frames), ocr_calls, len(rows), base, base))
    for s, e, t in rows:
        print('  %s --> %s  %s' % (ts_srt(s), ts_srt(e), t.replace('\n', ' / ')))
    if a.keep_frames:
        print('frames kept in %s' % tmp)
    else:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
