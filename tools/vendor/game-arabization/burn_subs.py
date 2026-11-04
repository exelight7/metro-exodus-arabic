#!/usr/bin/env python3
"""
burn_subs.py - Arabize a cutscene that has BURNED-IN English text:
  1. hide the original text      --cover box | blur | delogo | inpaint | none
  2. burn the Arabic .ass        (libass: real Arabic shaping + RTL, any TTF/OTF font)
  3. re-encode to the SAME resolution, frame rate, frame count and audio as the original
  4. verify the result against the original (and export QA screenshots)

Usage
  burn_subs.py in.mp4 out.mp4 --ass ar.ass --cover blur --region 0,560,1280,150
  burn_subs.py in.mp4 out.mp4 --ass ar.ass --cover inpaint --region 0,560,1280,150 --times subs.csv
  burn_subs.py in.webm out.webm --ass ar.ass --cover box --region ... --fontsdir ./fonts
  burn_subs.py in.mp4 test.mp4 --ass ar.ass --cover blur --region ... --from 10 --duration 6   (preview)
  burn_subs.py in.mp4 out.mp4 --ass ar.ass --cover none --shots 3.5,7.0  (+ PNG screenshots)
  add --dry-run to print the ffmpeg command only
--times: CSV/SRT with start,end (e.g. hardsub_ocr.py output) -> cover only while English is on screen.
Codec: same family as the source by default (h264->libx264, vp9->libvpx-vp9, vp8->libvpx, hevc->libx265).
After this, put the video back in the game's container (USM/Bink/bundle) - see references/cutscenes.md.
Needs: ffmpeg with libass (ffmpeg -filters | grep subtitles); inpaint also needs opencv-python + numpy.
"""
import argparse
import csv
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile


def ffprobe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', path],
                         capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    v = next(s for s in d['streams'] if s['codec_type'] == 'video')
    aud = [s for s in d['streams'] if s['codec_type'] == 'audio']
    num, den = v.get('avg_frame_rate', '0/1').split('/')
    if float(den or 0) == 0 or float(num) == 0:
        num, den = v['r_frame_rate'].split('/')
    return {'codec': v['codec_name'], 'w': int(v['width']), 'h': int(v['height']), 'pix_fmt': v.get('pix_fmt', 'yuv420p'),
            'fps_str': '%s/%s' % (num, den), 'fps': float(num) / float(den),
            'duration': float(d['format'].get('duration') or v.get('duration') or 0),
            'audio': [(s['codec_name'], s.get('channels')) for s in aud]}


def count_frames(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets',
                          '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', path],
                         capture_output=True, text=True).stdout.strip()
    try:
        return int(out.split(',')[0])
    except ValueError:
        return -1


def parse_time(t):
    t = t.strip().replace(',', '.')
    if re.fullmatch(r'\d+(\.\d+)?', t):
        return float(t)
    p = t.split(':')
    return (int(p[-3]) * 3600 if len(p) >= 3 else 0) + (int(p[-2]) * 60 if len(p) >= 2 else 0) + float(p[-1])


def load_times(path, pad):
    with open(path, encoding='utf-8-sig') as f:
        data = f.read()
    spans = []
    if path.lower().endswith('.srt'):
        for m in re.finditer(r'(\d[\d:,.]+)\s*-->\s*(\d[\d:,.]+)', data):
            spans.append((parse_time(m.group(1)), parse_time(m.group(2))))
    else:
        for r in csv.DictReader(io.StringIO(data)):
            spans.append((parse_time(r['start']), parse_time(r['end'])))
    return [(max(0.0, s - pad), e + pad) for s, e in spans]


def enable_expr(spans):
    if not spans:
        return None
    return '+'.join('between(t\\,%.3f\\,%.3f)' % (s, e) for s, e in spans)


def pick_encoder(info, out_ext, a):
    enc = a.codec
    if enc == 'auto':
        enc = {'h264': 'libx264', 'hevc': 'libx265', 'vp9': 'libvpx-vp9', 'vp8': 'libvpx',
               'theora': 'libtheora', 'mpeg2video': 'mpeg2video', 'mpeg1video': 'mpeg1video',
               'av1': 'libsvtav1'}.get(info['codec'], 'libx264')
        if out_ext == '.webm' and enc not in ('libvpx', 'libvpx-vp9', 'libsvtav1'):
            enc = 'libvpx-vp9'
        if out_ext in ('.mp4', '.mov') and enc in ('libvpx', 'libtheora'):
            enc = 'libx264'
    have = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'], capture_output=True, text=True).stdout
    if ' %s ' % enc not in have:
        print('note: encoder %s not available, using libx264' % enc)
        enc = 'libx264'
    args = ['-c:v', enc]
    if enc == 'libx264':
        args += ['-crf', str(a.crf if a.crf is not None else 18), '-preset', a.preset]
    elif enc == 'libx265':
        args += ['-crf', str(a.crf if a.crf is not None else 20), '-preset', a.preset]
    elif enc == 'libvpx-vp9':
        args += ['-crf', str(a.crf if a.crf is not None else 30), '-b:v', '0', '-row-mt', '1',
                 '-deadline', 'good', '-cpu-used', '4']
    elif enc == 'libvpx':
        args += ['-crf', str(a.crf if a.crf is not None else 8), '-b:v', '8M', '-deadline', 'good', '-cpu-used', '4']
    elif enc == 'libtheora':
        args += ['-q:v', '8']
    elif enc.startswith('mpeg'):
        args += ['-q:v', '2']
    pix = info['pix_fmt'] if info['pix_fmt'] in ('yuv420p', 'yuv422p', 'yuv444p', 'yuva420p') else 'yuv420p'
    args += ['-pix_fmt', pix]
    # audio: copy when the container allows it
    acodecs = [c for c, _ in info['audio']]
    if not acodecs:
        return args + ['-an'], enc
    ok_webm = all(c in ('opus', 'vorbis') for c in acodecs)
    ok_mp4 = all(c in ('aac', 'mp3', 'ac3', 'eac3', 'alac', 'opus') for c in acodecs)
    if out_ext == '.webm' and not ok_webm:
        args += ['-c:a', 'libopus', '-b:a', '160k']
    elif out_ext in ('.mp4', '.m4v', '.mov') and not ok_mp4:
        args += ['-c:a', 'aac', '-b:a', '192k']
    else:
        args += ['-c:a', 'copy']
    return args, enc


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='Cover burned-in text and burn Arabic subtitles.')
    ap.add_argument('input')
    ap.add_argument('output')
    ap.add_argument('--ass', help='Arabic .ass (make_ass.py) - omit to only cover/clean')
    ap.add_argument('--cover', choices=['none', 'box', 'blur', 'delogo', 'inpaint'], default='none')
    ap.add_argument('--region', help='x,y,w,h of the burned-in text')
    ap.add_argument('--times', help='CSV/SRT: cover only during these spans')
    ap.add_argument('--pad', type=float, default=0.15, help='seconds added around --times spans')
    ap.add_argument('--box-color', default='black@1.0', help='ffmpeg colour; below @1.0 the English shows through')
    ap.add_argument('--grow', type=int, default=5, help='inpaint: px added around text (outline + anti-aliasing)')
    ap.add_argument('--threshold', type=int, default=170, help='inpaint: brightness of text pixels')
    ap.add_argument('--fontsdir', help='folder with the .ttf/.otf used by the .ass')
    ap.add_argument('--codec', default='auto')
    ap.add_argument('--crf', type=int)
    ap.add_argument('--preset', default='veryfast', help='x264/x265 preset (veryfast = quick; slow = best)')
    ap.add_argument('--from', dest='start', type=float, help='preview: start time')
    ap.add_argument('--duration', type=float, help='preview: length in seconds')
    ap.add_argument('--shots', help='comma list of times to export as PNG for QA')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    if a.cover != 'none' and not a.region:
        ap.error('--cover needs --region x,y,w,h')
    if not shutil.which('ffmpeg'):
        sys.exit('ffmpeg not found')

    inp, outp = os.path.abspath(a.input), os.path.abspath(a.output)
    info = ffprobe(inp)
    W, H = info['w'], info['h']
    out_ext = os.path.splitext(outp)[1].lower()
    tmp = tempfile.mkdtemp(prefix='burnsubs_')
    spans = load_times(a.times, a.pad) if a.times else []
    en = enable_expr(spans)
    # ---- build the filter graph: [cover] -> [subtitles]
    if a.region:
        x, y, w, h = [int(v) for v in a.region.split(',')]
        x, y = max(0, x), max(0, y)
        w, h = min(w, W - x), min(h, H - y)
    on = ":enable='%s'" % en if en else ''
    graph, chain, cur = [], [], '0:v'
    if a.cover == 'blur':
        r = max(2, min(30, h // 4))
        graph.append('[0:v]split=2[base][tmp];[tmp]crop=%d:%d:%d:%d,boxblur=lr=%d:lp=3:cr=%d:cp=3[bl];'
                     '[base][bl]overlay=%d:%d%s[cov]' % (w, h, x, y, r, max(1, r // 2), x, y, on))
        cur = 'cov'
    elif a.cover == 'box':
        chain.append('drawbox=x=%d:y=%d:w=%d:h=%d:color=%s:t=fill%s' % (x, y, w, h, a.box_color, on))
    elif a.cover == 'delogo':
        dx, dy = max(1, x), max(1, y)
        chain.append('delogo=x=%d:y=%d:w=%d:h=%d%s' % (dx, dy, min(w, W - dx - 1), min(h, H - dy - 1), on))
    if a.ass:
        shutil.copy(a.ass, os.path.join(tmp, 'subs.ass'))
        fd = os.path.join(tmp, 'fonts')
        os.makedirs(fd)
        if a.fontsdir:
            for fn in os.listdir(a.fontsdir):
                if fn.lower().endswith(('.ttf', '.otf', '.ttc')):
                    shutil.copy(os.path.join(a.fontsdir, fn), fd)
    subs = 'subtitles=subs.ass:fontsdir=fonts' if a.ass else None

    enc_args, enc = pick_encoder(info, out_ext, a)
    common_out = ['-map_metadata', '0'] + enc_args + (['-movflags', '+faststart'] if out_ext in ('.mp4', '.mov', '.m4v') else [])
    start = a.start or 0.0
    in_seek = (['-ss', str(a.start)] if a.start is not None else []) + (['-t', str(a.duration)] if a.duration else [])

    if a.cover == 'inpaint':
        try:
            import numpy as np
            import cv2
        except ImportError:
            sys.exit('inpaint needs: pip install opencv-python-headless numpy')
        dec = ['ffmpeg', '-v', 'error'] + in_seek + ['-i', inp, '-map', '0:v:0', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-']
        enc_cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', '%dx%d' % (W, H),
                   '-framerate', info['fps_str'], '-i', '-'] + in_seek + ['-i', inp, '-map', '0:v', '-map', '1:a?']
        if subs:   # raw frames start at t=0: shift so the .ass times still match the original timeline
            enc_cmd += ['-vf', 'setpts=PTS+%f/TB,%s,setpts=PTS-%f/TB' % (start, subs, start) if start else subs]
        enc_cmd += common_out + ['-shortest', outp]
        print('decode: ' + ' '.join(dec))
        print('encode: ' + ' '.join(enc_cmd))
        if a.dry_run:
            return 0
        p_dec = subprocess.Popen(dec, stdout=subprocess.PIPE)
        p_enc = subprocess.Popen(enc_cmd, stdin=subprocess.PIPE, cwd=tmp)
        fsize = W * H * 3
        kernel = np.ones((3, 3), np.uint8)
        n = touched = 0
        while True:
            buf = p_dec.stdout.read(fsize)
            if len(buf) < fsize:
                break
            t = start + n / info['fps']
            frame = np.frombuffer(buf, np.uint8).reshape(H, W, 3).copy()
            if not spans or any(s0 <= t <= e0 for s0, e0 in spans):
                roi = frame[y:y + h, x:x + w]
                mask = (cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) >= a.threshold).astype(np.uint8) * 255
                mask = cv2.dilate(mask, kernel, iterations=a.grow)  # text + outline + anti-aliasing
                if mask.any():
                    frame[y:y + h, x:x + w] = cv2.inpaint(roi, mask, 5, cv2.INPAINT_TELEA)
                    touched += 1
            p_enc.stdin.write(frame.tobytes())
            n += 1
        p_enc.stdin.close()
        p_dec.wait()
        rc = p_enc.wait()
        print('frames %d, inpainted %d' % (n, touched))
        if rc:
            sys.exit('encoder failed (%d)' % rc)
    else:
        if subs:
            chain.append(subs)
        if chain:
            graph.append('[%s]%s[vout]' % (cur, ','.join(chain)))
            cur = 'vout'
        cmd = ['ffmpeg', '-v', 'error', '-y']
        if a.start is not None:
            cmd += ['-ss', str(a.start), '-copyts']        # keep original timestamps for .ass / --times
        cmd += ['-i', inp]
        cmd += (['-filter_complex', ';'.join(graph), '-map', '[%s]' % cur] if graph else ['-map', '0:v:0'])
        cmd += ['-map', '0:a?'] + (['-t', str(a.duration)] if a.duration else []) + common_out + [outp]
        print(' '.join(cmd))
        if a.dry_run:
            return 0
        r = subprocess.run(cmd, cwd=tmp)
        if r.returncode:
            sys.exit('ffmpeg failed (%d)' % r.returncode)

    # ---- verification
    new = ffprobe(outp)
    f_in, f_out = count_frames(inp), count_frames(outp)
    preview = a.start is not None or a.duration
    rows = [('resolution', '%dx%d' % (W, H), '%dx%d' % (new['w'], new['h'])),
            ('frame rate', '%.3f' % info['fps'], '%.3f' % new['fps']),
            ('frames', str(f_in), str(f_out)),
            ('duration s', '%.3f' % info['duration'], '%.3f' % new['duration']),
            ('video codec', info['codec'], new['codec']),
            ('audio', str(info['audio']), str(new['audio']))]
    print('\n%-12s %-28s %-28s' % ('', 'original', 'new'))
    for k, o, nn in rows:
        print('%-12s %-28s %-28s %s' % (k, o, nn, '' if o == nn else '<-'))
    bad = (W, H) != (new['w'], new['h']) or abs(info['fps'] - new['fps']) > 0.01
    if not preview:
        bad = bad or abs(f_in - f_out) > 1 or abs(info['duration'] - new['duration']) > 2.0 / info['fps']
    print('VERIFY: %s' % ('OK' if not bad else 'MISMATCH - the game may desync audio/subtitles or reject the file'))
    if a.shots:
        base = os.path.splitext(outp)[0]
        for t in a.shots.split(','):
            png = '%s_%ss.png' % (base, t.strip())
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', t.strip(), '-i', outp, '-frames:v', '1', png])
            print('shot: %s' % png)
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if not bad else 2


if __name__ == '__main__':
    sys.exit(main())
