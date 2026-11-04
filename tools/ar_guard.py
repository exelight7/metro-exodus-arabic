#!/usr/bin/env python3
"""ar_guard.py - keeps Arabization projects from getting lost or clobbered (std 1.0, stdlib only).
  init DIR --game NAME            create the standard tree (skips if project.json exists) + register
  where [--scan DIR]...           list every known project on this machine (registry + scan)
  start --session S --claim P...  show handoff, journal tail, locks; claim paths (refuses overlaps)
  log --session S "what" [FILE..] one journal line
  end --session S --next "..."    release claim, list files changed (warn outside claim), handoff, zip
  status                          locks + last journal lines + NEXT
Run inside a project (searches up for project.json) or pass --root."""
import argparse, datetime as dt, json, os, re, socket, sys, zipfile

REG = os.path.join(os.path.expanduser('~'), '.ar_projects.json')
DIRS = ['00_admin/locks', '01_original', '02_extracted', '03_translation/tables', '03_translation/tm',
        '04_fonts/src', '04_fonts/build', '05_media', '06_build', '07_patch', '08_qa/shots', '09_release',
        'tools', 'backups']
AUTHORED = ['project.json', 'STATUS.md', 'README.md', 'AGENTS.md', '00_admin', '03_translation', '04_fonts/src', '04_fonts/maps', '05_media', '08_qa', 'tools']
STALE_H = 12


def now():
    return dt.datetime.now().strftime('%Y-%m-%d %H:%M')


def find_root(start):
    d = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(d, 'project.json')):
            return d
        if os.path.dirname(d) == d:
            sys.exit('ERROR: no project.json here or above (use --root, or init)')
        d = os.path.dirname(d)


def rd(p, default=''):
    try:
        with open(p, encoding='utf-8') as f:
            return f.read()
    except OSError:
        return default


def wr(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write(s)


def journal(root, session, msg, files=()):
    p = os.path.join(root, '00_admin', 'JOURNAL.md')
    if not os.path.exists(p):
        wr(p, '# JOURNAL (append only)\n| time | session | what | files |\n|---|---|---|---|\n')
    with open(p, 'a', encoding='utf-8') as f:
        f.write('| %s | %s | %s | %s |\n' % (now(), session, msg.replace('|', '/'), ', '.join(files)))


def registry():
    try:
        return json.loads(rd(REG, '{}'))
    except ValueError:
        return {}


def register(root, **kw):
    r = registry()
    e = r.get(root, {})
    pj = json.loads(rd(os.path.join(root, 'project.json'), '{}') or '{}')
    e.update(name=(pj.get('game') or {}).get('name', os.path.basename(root)), created=pj.get('created', ''), seen=now(), **kw)
    for old in [k for k, v in r.items() if k != root and v.get('created') and v.get('created') == e['created']
                and v.get('name') == e['name'] and not os.path.isfile(os.path.join(k, 'project.json'))]:
        e.setdefault('moved_from', old)
        del r[old]            # same project found at a new path: the old entry was a move
    r[root] = e
    with open(REG, 'w', encoding='utf-8') as f:
        json.dump(r, f, ensure_ascii=False, indent=1)


def locks(root):
    d = os.path.join(root, '00_admin', 'locks')
    out = []
    for n in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if n.endswith('.json'):
            try:
                L = json.loads(rd(os.path.join(d, n)))
            except ValueError:
                continue
            age = (dt.datetime.now() - dt.datetime.strptime(L['started'], '%Y-%m-%d %H:%M')).total_seconds() / 3600
            L['stale'] = age > STALE_H
            out.append(L)
    return out


def overlap(a, b):
    a, b = a.strip('/'), b.strip('/')
    return a == b or a.startswith(b + '/') or b.startswith(a + '/') or a == '.' or b == '.'


def next_block(root):
    m = re.search(r'<!-- NEXT -->(.*?)<!-- /NEXT -->', rd(os.path.join(root, 'STATUS.md')), re.S)
    return m.group(1).strip() if m else '(no NEXT block in STATUS.md)'


def tail(root, n=8):
    return [l for l in rd(os.path.join(root, '00_admin', 'JOURNAL.md')).splitlines() if l.startswith('| 20')][-n:]


def cmd_init(a):
    root = os.path.abspath(a.dir)
    for d in DIRS:
        os.makedirs(os.path.join(root, d), exist_ok=True)
    if not os.path.exists(os.path.join(root, 'project.json')):
        wr(os.path.join(root, 'project.json'), json.dumps({'std': '1.0', 'created': now(), 'game': {
            'name': a.game, 'engine': a.engine, 'version': a.game_version}, 'render': {'mode': 'undecided'},
            'tables': []}, ensure_ascii=False, indent=2) + '\n')
    if not os.path.exists(os.path.join(root, 'STATUS.md')):
        wr(os.path.join(root, 'STATUS.md'), '# %s - status\n\n<!-- NEXT -->\n- start: snapshot originals into 01_original/<ver>/\n<!-- /NEXT -->\n\n## facts (with evidence)\n-\n## open\n- [ ]\n' % a.game)
    if not os.path.exists(os.path.join(root, '00_admin', 'DECISIONS.md')):
        wr(os.path.join(root, '00_admin', 'DECISIONS.md'), '# DECISIONS (append only, D-001...)\n')
    journal(root, 'init', 'project created')
    register(root)
    print('project ready + registered: %s' % root)


def cmd_where(a):
    r = registry()
    for base in a.scan or []:
        for dp, dns, fns in os.walk(base):
            dns[:] = [d for d in dns if d not in ('.git', '01_original', '02_extracted', '06_build', '07_patch', 'backups', 'node_modules')]
            if 'project.json' in fns and os.path.isfile(os.path.join(dp, 'STATUS.md')):
                register(os.path.abspath(dp))
                dns[:] = []
        r = registry()
    if not r:
        print('no projects registered. Try: where --scan <drive or folder>')
    for p, e in sorted(r.items(), key=lambda x: x[1].get('seen', ''), reverse=True):
        ok = os.path.isfile(os.path.join(p, 'project.json'))
        lk = ', '.join(L['session'] for L in locks(p)) if ok else ''
        print('%-28s %-16s %s%s%s' % (e.get('name', '?')[:28], e.get('seen', ''), p,
                                     '' if ok else '   [MISSING - moved? where --scan]', ('   locks: ' + lk) if lk else ''))


def cmd_start(a):
    root = a.root or find_root('.')
    print('PROJECT %s\nNEXT:\n%s\nJOURNAL (last):' % (root, next_block(root)))
    print('\n'.join(tail(root)) or '  (empty)')
    mine = [c.strip('/') or '.' for c in a.claim]
    clash = []
    for L in locks(root):
        if L['session'] == a.session:
            continue
        hit = [c for c in mine for o in L['claims'] if overlap(c, o)]
        print('LOCK %s on %s since %s%s' % (L['session'], L['claims'], L['started'], ' (STALE)' if L['stale'] else ''))
        if hit and not (L['stale'] and a.take_stale):
            clash.append((L['session'], hit))
    if clash:
        for s, h in clash:
            print('REFUSED: %s already claims %s - pick other paths, or ask; stale locks: --take-stale' % (s, h))
        sys.exit(3)
    wr(os.path.join(root, '00_admin', 'locks', a.session + '.json'), json.dumps(
        {'session': a.session, 'claims': mine, 'started': now(), 'host': socket.gethostname(), 'note': a.note or ''}, indent=1))
    journal(root, a.session, 'start: ' + (a.note or ''), mine)
    register(root, last_session=a.session)
    print('CLAIMED %s for %s' % (mine, a.session))


def cmd_log(a):
    root = a.root or find_root('.')
    journal(root, a.session, a.msg, a.files)
    print('logged')


def changed_since(root, t0):
    ts = dt.datetime.strptime(t0, '%Y-%m-%d %H:%M').timestamp() - 60
    out = []
    for base in AUTHORED + ['06_build', '07_patch']:
        p = os.path.join(root, base)
        it = [p] if os.path.isfile(p) else [os.path.join(dp, f) for dp, _, fs in os.walk(p) for f in fs] if os.path.isdir(p) else []
        for f in it:
            r = os.path.relpath(f, root).replace(os.sep, '/')
            if os.path.getmtime(f) >= ts and not r.startswith('00_admin/') and r != 'STATUS.md':
                out.append(r)
    return sorted(set(out))


def cmd_end(a):
    root = a.root or find_root('.')
    lp = os.path.join(root, '00_admin', 'locks', a.session + '.json')
    if not os.path.exists(lp):
        sys.exit('ERROR: %s has no claim (start first)' % a.session)
    L = json.loads(rd(lp))
    others = [o for o in locks(root) if o['session'] != a.session]
    ch = changed_since(root, L['started'])
    for r in ch:
        inside = any(overlap(r, c) for c in L['claims'])
        foreign = [o['session'] for o in others if any(overlap(r, c) for c in o['claims'])]
        flag = '' if inside else ('  !! OUTSIDE CLAIM' + ('  !! owned by ' + ','.join(foreign) if foreign else ''))
        print('changed: %s%s' % (r, flag))
    s = rd(os.path.join(root, 'STATUS.md'))
    blk = '<!-- NEXT -->\n- %s (%s): %s\n<!-- /NEXT -->' % (now(), a.session, a.next)
    s = re.sub(r'<!-- NEXT -->.*?<!-- /NEXT -->', lambda m: blk, s, flags=re.S) if '<!-- NEXT -->' in s else blk + '\n\n' + s
    wr(os.path.join(root, 'STATUS.md'), s)
    z = os.path.join(root, 'backups', 'handoff_%s_%s.zip' % (a.session, dt.datetime.now().strftime('%Y%m%d-%H%M')))
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for base in AUTHORED:
            p = os.path.join(root, base)
            for f in ([p] if os.path.isfile(p) else [os.path.join(dp, x) for dp, _, fs in os.walk(p) for x in fs] if os.path.isdir(p) else []):
                zf.write(f, os.path.relpath(f, root))
    os.remove(lp)
    journal(root, a.session, 'end: ' + a.next, [r for r in ch][:20])
    register(root, last_session=a.session)
    print('released %s | NEXT written | snapshot %s (%d files changed)' % (a.session, os.path.relpath(z, root), len(ch)))


def cmd_status(a):
    root = a.root or find_root('.')
    print('NEXT:\n' + next_block(root))
    for L in locks(root):
        print('LOCK %s %s since %s%s' % (L['session'], L['claims'], L['started'], ' (STALE)' if L['stale'] else ''))
    print('\n'.join(tail(root)))


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root')
    sp = ap.add_subparsers(dest='c', required=True)
    p = sp.add_parser('init'); p.add_argument('dir'); p.add_argument('--game', required=True)
    p.add_argument('--engine', default='other'); p.add_argument('--game-version', default='unknown'); p.set_defaults(f=cmd_init)
    p = sp.add_parser('where'); p.add_argument('--scan', action='append'); p.set_defaults(f=cmd_where)
    p = sp.add_parser('start'); p.add_argument('--session', required=True); p.add_argument('--claim', nargs='+', required=True)
    p.add_argument('--note'); p.add_argument('--take-stale', action='store_true'); p.set_defaults(f=cmd_start)
    p = sp.add_parser('log'); p.add_argument('--session', required=True); p.add_argument('msg'); p.add_argument('files', nargs='*'); p.set_defaults(f=cmd_log)
    p = sp.add_parser('end'); p.add_argument('--session', required=True); p.add_argument('--next', required=True); p.set_defaults(f=cmd_end)
    p = sp.add_parser('status'); p.set_defaults(f=cmd_status)
    a = ap.parse_args()
    if a.root:
        a.root = os.path.abspath(a.root)
    a.f(a)


if __name__ == '__main__':
    main()
