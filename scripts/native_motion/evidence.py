"""Independent playback/review verification for dual recording runs."""
import json
from pathlib import Path
from .acceptance import sha,STATES
from .desktop_workflow import inspect_recordings


def verify_reviews(root,data):
    checks=data['checks'];bindings={k:r['recording_sha256'] for k,r in data.get('recordings',{}).items()}
    for c in checks:
        automatic=c.get('automatic_status',c['status']);reviewed=c.get('reviewed_status')
        if automatic not in STATES or (reviewed is not None and reviewed not in STATES):raise ValueError('Invalid automatic/reviewed state')
        if c['status']!=(reviewed if reviewed is not None else automatic):raise ValueError('Final state contradicts automatic/reviewed states')
        if reviewed is None:continue
        if automatic=='failed' and reviewed=='passed':raise ValueError('Review cannot override failed automated evidence')
        if c['id']=='target-player' or c['id'].startswith('target-player-'):raise ValueError('Player coverage cannot be reviewed into a different backend')
        path=root/c['review']
        if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():raise ValueError('Unsafe review path')
        r=json.loads(path.read_text())
        if r['check_id']!=c['id'] or r['automatic_status']!=automatic or r['reviewed_status']!=reviewed or r['recordings']!=bindings:raise ValueError('Review belongs to another check or recording')
        machine=sha(root/c['evidence']) if c.get('evidence') else None
        if r['machine_evidence_sha256']!=machine:raise ValueError('Reviewed machine evidence changed')
        for e in r['evidence']:
            p=root/e['path']
            if not p.resolve().is_relative_to(root.resolve()) or p.is_symlink() or sha(p)!=e['sha256']:raise ValueError('Reviewed frame/measurement evidence changed')


def verify_dual_recordings(root,data):
    recordings=data.get('recordings',{})
    if not recordings:
        if any(c['status']=='passed' and c['id'].startswith(('desktop-recording','target-player')) for c in data['checks']):raise ValueError('Passed playback check has no bound recordings')
        return
    actual=inspect_recordings(root,data['requested_target_player'])
    if actual!=recordings:raise ValueError('Recording index differs from actual evidence')
    rows={c['id']:c for c in data['checks']}
    for name,r in recordings.items():
        for path in (root/'qa'/name).rglob('*audit.json'):
            d=json.loads(path.read_text())
            if d.get('origin')=='measurement_of_actual_desktop_recording':
                if d.get('recording_sha256')!=r['recording_sha256'] or d.get('source_pptx_sha256')!=r['source_pptx_sha256']:raise ValueError('Measurement belongs to another recording: '+str(path))
            if path.name=='native-motion-playback-audit.json':
                phases=root/'qa'/name/'phases/phase-audit.json';plan=phases.parent/'observed-playback-plan.json'
                if d['source_json_sha256']!=sha(root/'project.json') or d['planned_input_sha256']!=sha(plan) or d.get('phase_evidence_sha256')!=sha(phases):raise ValueError('Motion dependencies changed')
                check=rows.get('native-motion-'+name)
                if check and check.get('automatic_status',check['status'])!=d['status']:raise ValueError('Automatic motion state contradicts actual measurements')
            if path.name=='phase-audit.json':
                if d['source_json_sha256']!=sha(root/'project.json'):raise ValueError('Phase source changed')
                if d.get('format_version',1)>=2:
                    proof_path=root/r['evidence']
                    if d.get('playback_evidence_sha256')!=sha(proof_path):raise ValueError('Phase playback input evidence changed')
                    proof=json.loads(proof_path.read_text());keys=[a['at_wall_seconds'] for a in proof['actions'] if a['key']=='F5']
                    if len(keys)!=1 or d.get('actual_show_key_seconds')!=keys[0]:raise ValueError('Phase actual show key differs from capture input')
                if name=='manual' and d['planned_input_sha256']!=sha(root/'plans/manual-input.json'):raise ValueError('Phase manual input plan changed')
                check=rows.get('native-phases-'+name)
                if check and check.get('automatic_status',check['status'])!=d['status']:raise ValueError('Phase state contradicts measurements')
    diag=root/'diagnostic/morph-audit.json'
    if diag.is_file():
        r=json.loads(diag.read_text());proof=json.loads((diag.parent/'capture/playback-evidence.json').read_text())
        if r['recording_sha256']!=sha(diag.parent/'capture/player-recording.mp4') or r['source_pptx_sha256']!=sha(diag.parent/'deck.pptx'):raise ValueError('Morph diagnostic changed')
        main=json.loads((root/recordings['manual']['evidence']).read_text())
        if proof['player']!=recordings['manual']['player'] or proof['recording_sha256']!=r['recording_sha256'] or proof['source_pptx_sha256']!=r['source_pptx_sha256']:raise ValueError('Morph diagnostic uses a different actual player or PPTX')
        for key in ['version','installed_vendor_package']:
            if proof.get(key)!=main.get(key):raise ValueError('Morph diagnostic uses a different player build')
