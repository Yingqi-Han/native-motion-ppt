"""Readable event timeline assembled from measured phases and local object traces."""
from .acceptance import sha

def timeline(phases,motion):
    result=[]
    for morph in phases['morphs']:
        if morph.get('observed_transition_seconds'):
            a,b=morph['observed_transition_seconds'];result.append({'kind':'incoming-morph','slide':morph['slide'],'object':morph['object'],'start':a,'end':b,'status':morph['status']})
    for obj in motion['objects']:
        for event in obj['observed_intervals']:
            result.append({'kind':'content-reveal' if obj['kind']=='bar' else 'page-local-motion','slide':obj['slide'],'object':obj['object'],
                           'start':event['start'],'end':event['end'],'status':obj['status']})
    for i,page in enumerate(phases['pages']):
        if page['status']!='passed':continue
        start,end=page['stable_interval_seconds']
        local=[e['end'] for e in result if e['slide']==page['slide']]
        begin=max([start,*local])
        if end-begin>=.45:result.append({'kind':'stable-hold-candidate','slide':page['slide'],'start':begin,'end':end,'status':'passed',
                                       'meaning':'Observed stable page and no tracked local motion; narration/reading sufficiency still requires review'})
        first=[e for e in phases['activity_intervals'] if e['start']>=phases['page_starts'][i]-.15 and e['start']<start]
        if first:result.append({'kind':'page-entry-and-reveal','slide':page['slide'],'start':first[0]['start'],'end':min(first[0]['end'],start),'status':'observed',
                                'meaning':'Composite page activity; fade/text entrance cannot always be separated by global pixels'})
    return {'origin':'measurement_of_actual_desktop_recording','recording_sha256':phases['recording_sha256'],'source_pptx_sha256':phases['source_pptx_sha256'],
            'events':sorted(result,key=lambda e:(e['start'],e['end'])),'scope':'Measured event ranges, no source animation evaluation. Composite entrances and reading candidates are explicitly labelled.'}
