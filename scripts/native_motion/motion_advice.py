"""Geometry-based authoring advice; never an acceptance result or automatic source edit."""
import math

def advise(doc):
    w,h=doc['canvas']['width'],doc['canvas']['height'];items=[]
    for i,slide in enumerate(doc['slides']):
        if i and slide['transition']['kind']=='morph':
            old={o['id']:o for o in doc['slides'][i-1]['objects']};changes=[]
            for o in slide['objects']:
                a=old.get(o['id'])
                if not a:continue
                b,c=a['box'],o['box'];distance=math.hypot((c[0]+c[2]/2-b[0]-b[2]/2)/w,(c[1]+c[3]/2-b[1]-b[3]/2)/h)
                scale=max(abs(math.log(c[2]/b[2])),abs(math.log(c[3]/b[3]))) if min(b[2:]+c[2:])>0 else 0
                if distance<.005 and scale<.01:continue
                changes.append({'object':o['id'],'normalized_center_distance':distance,'log_scale_change':scale})
            if changes:
                duration=round(min(2400,max(500,600+1500*max(c['normalized_center_distance'] for c in changes)+650*max(c['log_scale_change'] for c in changes)+35*max(0,len(changes)-1)))/100)*100
                items.append({'slide':i+1,'kind':'morph-duration','current_ms':slide['transition']['duration'],'suggested_ms':duration,'changed_objects':changes,
                              'note':'Starting point based on distance, scale and object count. Real playback and intended narration decide; never apply globally without review.'})
    return {'origin':'source_geometry_authoring_advice','is_playback_measurement':False,'items':items,
            'scope':'Suggestions only; source is unchanged. Geometry cannot certify visual quality, reading comprehension or target-player smoothness.'}
