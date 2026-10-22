"""Derived, SHA-bound explanations; never rewrite a raw acceptance verdict."""
import hashlib
import html
import json
import math
import os
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inside(root, name):
    if not isinstance(name, str):
        raise ValueError('Evidence path must be a relative string')
    path = root/name
    if Path(name).is_absolute() or not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
        raise ValueError('Evidence path escapes the selected run')
    return path


def finite(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def explanation(code):
    if 'unsupported' in code:
        return 'unsupported', '当前检测方法不覆盖该变换或几何；检查实际帧并使用独立追踪/绑定录像的复核。重跑同一算法不会增加覆盖。'
    if code == 'morph-no-isolated-color':
        return 'unsupported', '主体没有可靠的独立色轮廓。检查同色干扰与遮挡；需要新的追踪方法或实际帧复核，不能只放宽阈值。'
    if code in {'page-ambiguous', 'page-not-calibrated'}:
        return 'not_observed', '核对页序、完整参考页和停留时间；相同页面可能无法独立识别。修改 PPT 后新录，检查器修改后在新目录复算。'
    if code == 'page-entry-unobserved':
        return 'not_observed', '核对实际 F5 输入与开场画面是否完整。缺少开场活动需重新采集；不要把稳定画面当作入场证据。'
    if code in {'visibility-insufficient', 'morph-endpoints-unobserved'}:
        return 'not_observed', '检查主体是否遮挡、同色合并或未完全出现，并延长实际到位停留；采集缺失需要新录。'
    if code in {'motion-not-observed', 'morph-poses-insufficient', 'morph-arrival-unobserved', 'morph-no-shared-motion'}:
        return 'not_observed', '回看主体变化和到位平台，核对原生动画、同名对象及转场；静止或姿态不足不能证明运动通过。'
    if code == 'capture-gap':
        return 'capture', '检查录屏负载、丢帧和遮挡，使用新目录重新采集；不能从缺口直接认定播放器跳变。'
    return 'review', '回看相应真实片段及原始检查记录；失败项修复后重录/复测，待检项保留具体范围。'


def legacy_code(row):
    reason = row.get('reason', '')
    for token, code in [('缩放或旋转', 'unsupported-transform'), ('透明或旋转', 'unsupported-opacity-rotation'),
                        ('supports', 'unsupported-geometry'), ('需要单独标定', 'unsupported-bar-composition'),
                        ('当前追踪器支持', 'unsupported-geometry'), ('Text/complex', 'morph-unsupported-geometry'),
                        ('Rotated/translucent', 'morph-unsupported-transform'), ('No isolated', 'morph-no-isolated-color'),
                        ('No geometrically', 'morph-no-shared-motion'), ('可靠可见帧不足', 'visibility-insufficient'),
                        ('没有足够的可测位移', 'motion-not-observed'), ('Endpoint contours', 'morph-endpoints-unobserved'),
                        ('Insufficient measured', 'morph-poses-insufficient'), ('arrival plateau', 'morph-arrival-unobserved'),
                        ('reference match', 'page-ambiguous'), ('该页参考', 'page-not-calibrated'),
                        ('实际到位标定', 'page-not-calibrated'), ('entry activity', 'page-entry-unobserved'),
                        ('transition onset', 'page-entry-unobserved')]:
        if token in reason:
            return code
    return 'raw-state-'+row.get('status', 'pending')


def collect_diagnostics(root):
    root = Path(root).resolve()
    acceptance = root/'acceptance.json'
    data = json.loads(acceptance.read_text(encoding='utf-8'))
    if data.get('format_version', 1) < 2:
        raise ValueError('Diagnostics require a v1.6+ acceptance run with explicit recording bindings')
    inputs = {};findings = [];videos = {};rows = {c['id']: c for c in data['checks']}
    handled = set();integrity = []

    def bind(path):
        name = path.relative_to(root).as_posix()
        if path.is_file():
            inputs[name] = {'sha256': sha(path), 'bytes': path.stat().st_size}
        return name

    def read(name):
        path = inside(root, name);bind(path)
        return json.loads(path.read_text(encoding='utf-8'))

    def add(row, code, source, mode=None, pages=(), message=None, suggestion=None):
        category, repair = explanation(code)
        timestamp = row.get('timestamp')
        frame = row.get('frame_index')
        interval = next((p.get('stable_interval_seconds') for p in pages if p.get('slide') == row.get('slide')), None)
        if not isinstance(interval, list) or len(interval) != 2 or not all(finite(v) for v in interval) or interval[0] >= interval[1]:
            interval = None
        findings.append({'code': code, 'category': category, 'mode': mode, 'slide': row.get('slide'), 'object': row.get('object'),
                         'status': row.get('severity', row.get('status', 'pending')), 'source_report': source,
                         'timestamp': timestamp if finite(timestamp) else None,
                         'frame_index': frame if type(frame) is int and frame >= 0 else None,
                         'context_interval_seconds': interval,
                         'location_basis': 'actual_issue_timestamp' if finite(timestamp) else 'page_context_only' if interval else 'not_observed',
                         'message': message or row.get('message') or row.get('reason') or '原始检查需要复核',
                         'suggestion': suggestion or row.get('suggestion') or repair,
                         'classification_basis': 'structured_code' if row.get('reason_code') or row.get('code') else 'legacy_reason_or_check_state'})

    bind(acceptance)
    for mode, rec in data.get('recordings', {}).items():
        if mode not in {'manual', 'automatic'}:
            integrity.append('Unknown recording mode: '+str(mode));continue
        try:
            video = inside(root, rec['video']);pptx = inside(root, rec['pptx']);proof = read(rec['evidence'])
            if not video.is_file() or not pptx.is_file():
                raise ValueError('Bound recording or PPTX is missing')
            bind(video);bind(pptx)
            if proof.get('origin') != 'native_desktop_screen_capture' or proof.get('is_pptx_playback_recording') is not True:
                raise ValueError('Capture provenance is not actual desktop playback')
            if sha(video) != rec['recording_sha256'] or proof.get('recording_sha256') != rec['recording_sha256']:
                raise ValueError('Recording SHA differs from capture proof/index')
            if sha(pptx) != rec['source_pptx_sha256'] or proof.get('source_pptx_sha256') != rec['source_pptx_sha256'] or proof.get('opened_copy_sha256') != rec['source_pptx_sha256']:
                raise ValueError('PPTX SHA differs from capture proof/index')
            if proof.get('player') != rec['player']:
                raise ValueError('Recorded player differs from capture proof/index')
            if mode == 'automatic' and [a.get('key') for a in proof.get('actions', [])] != ['F5']:
                raise ValueError('Automatic capture contains advance keys or lacks its F5')
            videos[mode] = rec['video']
            phase = None
            for kind, name, list_key in [('phases', 'phase-audit.json', 'morphs'), ('motion', 'native-motion-playback-audit.json', 'objects')]:
                path = root/'qa'/mode/kind/name
                if not path.is_file():
                    continue
                rel = path.relative_to(root).as_posix();audit = read(rel)
                if audit.get('origin') != 'measurement_of_actual_desktop_recording' or audit.get('recording_sha256') != rec['recording_sha256'] or audit.get('source_pptx_sha256') != rec['source_pptx_sha256']:
                    raise ValueError('Audit belongs to another recording/PPTX: '+rel)
                source = root/'project.json'
                if source.is_file():
                    bind(source)
                    if audit.get('source_json_sha256') != sha(source):
                        raise ValueError('Audit source JSON changed: '+rel)
                if kind == 'phases':
                    phase = audit
                    if audit.get('format_version', 1) >= 2:
                        keys = [a.get('at_wall_seconds') for a in proof.get('actions', []) if a.get('key') == 'F5']
                        if audit.get('playback_evidence_sha256') != sha(root/rec['evidence']) or len(keys) != 1 or not finite(keys[0]) or audit.get('actual_show_key_seconds') != keys[0]:
                            raise ValueError('Phase capture input binding changed: '+rel)
                else:
                    if phase and audit.get('phase_evidence_sha256') != sha(root/'qa'/mode/'phases/phase-audit.json'):
                        raise ValueError('Motion phase dependency changed: '+rel)
                check_id = 'native-'+kind+'-'+mode;handled.add(check_id)
                canonical = rows.get(check_id)
                if canonical and canonical.get('automatic_status', canonical['status']) != audit['status']:
                    integrity.append('Raw measurement and formal check state disagree: '+check_id)
                pages = (phase or audit).get('pages', [])
                for page in audit.get('pages', []):
                    if page['status'] != 'passed':
                        add(page, page.get('reason_code') or legacy_code(page), rel, mode, pages)
                for obj in audit.get(list_key, []):
                    for issue in obj.get('issues', []):
                        add({**obj, **issue}, issue['code'], rel, mode, pages)
                    if obj['status'] != 'passed' and not obj.get('issues'):
                        add(obj, obj.get('reason_code') or legacy_code(obj), rel, mode, pages)
                for obj in audit.get('uncovered_morphs' if kind == 'phases' else 'uncovered_objects', []):
                    add(obj, obj.get('reason_code') or legacy_code(obj), rel, mode, pages)
        except (OSError, ValueError, KeyError) as exc:
            videos.pop(mode, None)
            findings[:] = [f for f in findings if f['mode'] != mode]
            integrity.append(mode+': '+str(exc))
    for check in data['checks']:
        if check['status'] == 'passed' or check['id'] in handled:
            continue
        code = 'visual-review-required' if check['id'] == 'visual-review' else 'check-'+check['id']
        add(check, code, 'acceptance.json', message=check.get('detail') or check['label'],
            suggestion='查看本次实际帧后追加绑定录像 SHA 的结构化审阅；不得用审阅覆盖自动失败。' if code == 'visual-review-required' else None)
    for message in integrity:
        add({'status': 'failed'}, 'evidence-binding-invalid', 'acceptance.json', message=message,
            suggestion='恢复原始绑定文件，或在新目录重新采集/验收；不要改写校验值来套用其他证据。')
        findings[-1]['category'] = 'evidence'
    return {'format_version': 1, 'origin': 'derived_acceptance_explanation', 'status': 'generated',
            'acceptance_status': data.get('acceptance_status', 'pending'),
            'automatic_acceptance_status': data.get('automatic_acceptance_status', 'pending'),
            'diagnostic_integrity': 'failed' if integrity else 'passed', 'source_inputs': inputs, 'videos': videos,
            'findings': findings, 'scope': 'Explains existing raw states. No new playback verdict, no invented timestamps, no acceptance file modification.'}


def verify_diagnostics(root, path):
    root = Path(root).resolve();report = json.loads(Path(path).read_text(encoding='utf-8'))
    if report.get('origin') != 'derived_acceptance_explanation' or report.get('format_version') != 1:
        raise ValueError('Unknown diagnostics format')
    for name, entry in report['source_inputs'].items():
        p = inside(root, name)
        if not p.is_file() or sha(p) != entry['sha256'] or p.stat().st_size != entry['bytes']:
            raise ValueError('Diagnostic source changed: '+name)
    return {'status': 'passed', 'bound_inputs': len(report['source_inputs'])}


def write_diagnostics(root, output, report):
    root = Path(root).resolve();output = Path(output);output.mkdir(parents=True, exist_ok=True)
    esc = lambda value: html.escape(str(value))
    videos = []
    for mode, name in report['videos'].items():
        href = os.path.relpath(inside(root, name), output).replace(os.sep, '/')
        videos.append(f'<div><h2>{"点击实录" if mode=="manual" else "自动实录"}</h2><video id="video-{mode}" src="{esc(href)}" controls preload="metadata"></video></div>')
    cards = []
    for finding in report['findings']:
        mode = finding['mode'];t = finding['timestamp'];context = finding['context_interval_seconds'];seek = ''
        if mode in report['videos'] and (t is not None or context):
            at = t if t is not None else context[0]
            label = f'{t:.3f}s · 原始帧 {finding["frame_index"]}' if t is not None else f'页面上下文 {context[0]:.3f}–{context[1]:.3f}s（非异常时刻）'
            seek = f'<button data-mode="{mode}" data-at="{at}">{esc(label)}</button>'
        href = os.path.relpath(inside(root, finding['source_report']), output).replace(os.sep, '/')
        cards.append(f'<article><strong>{esc(finding["code"])}</strong> · {esc(finding["status"])} · {esc(finding["category"])}<p>页 {esc(finding["slide"])} · 对象 {esc(finding["object"])} {seek}</p><p>{esc(finding["message"])}</p><p>{esc(finding["suggestion"])}</p><a href="{esc(href)}">原始检查记录</a></article>')
    document='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>验收问题与复验建议</title><style>body{max-width:1100px;margin:40px auto;padding:0 20px;background:#f4f2ea;color:#173330;font:15px/1.65 system-ui}video{width:100%;background:#102326}.videos{display:grid;grid-template-columns:1fr 1fr;gap:20px}article{border-top:1px solid #cad5cc;padding:18px 0}button{font:inherit;cursor:pointer;background:#e0eadf;border:1px solid #b4c7bc;padding:5px 10px}a{color:#00766a}strong{overflow-wrap:anywhere}@media(max-width:700px){.videos{grid-template-columns:1fr}}</style><h1>验收问题与复验建议</h1><p>原始最终状态：'''+esc(report['acceptance_status'])+'；原始自动状态：'+esc(report['automatic_acceptance_status'])+'；解释文件依赖完整性：'+esc(report['diagnostic_integrity'])+'''。</p><p>此报告解释已有结果，不改变验收状态。可定位的时间来自实际测量；页面上下文只帮助回看，没有时间证据时不生成定位按钮。</p><section class="videos">'''+''.join(videos)+'</section>'+(''.join(cards) or '<p>本次没有需要解释的失败或待检项；原始检查范围仍以验收报告为准。</p>')+'''<script>document.querySelectorAll('button[data-at]').forEach(button=>button.onclick=()=>{const video=document.getElementById('video-'+button.dataset.mode);const at=Number(button.dataset.at);if(video&&Number.isFinite(at)&&at>=0){video.currentTime=Math.max(0,at-.2);video.scrollIntoView({block:'center'});}});</script></html>'''
    (output/'diagnostics.html').write_text(document, encoding='utf-8')
    (output/'diagnostics.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
