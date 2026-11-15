"""Common evidence envelope; manual records never promote another layer."""
from authoring_io import schema,sha,read_json,resolve
LAYERS=('static','offline','software_preview','editor','host','user_acceptance')
STATUSES=('passed','failed','not_checked','not_applicable')

def manual_records(path):
    spec=read_json(path);schema(spec,('schema','records'),('records',),version=1);rows=[]
    for row in spec['records']:
        schema(row,('artifact','sha256','layer','status','environment','source','scope'),('artifact','sha256','layer','status','environment','source','scope'))
        if row['layer'] not in ('editor','host','user_acceptance') or row['status'] not in STATUSES:raise ValueError('Invalid manual evidence layer/status')
        if any(not isinstance(row[k],str) or not row[k].strip() for k in ('environment','source','scope')):raise ValueError('Manual evidence requires environment, source and scope')
        artifact=resolve(path.parent,row['artifact']);current=artifact.is_file() and sha(artifact.read_bytes())==row['sha256']
        rows.append({**row,'status':row['status'] if current else 'not_checked','current':current,'reported_not_automatically_observed':True})
    return rows

def finding(code,severity,status,layer,subject,detail,source=None,scope=None):
    if severity not in ('error','warning','info') or status not in STATUSES or layer not in LAYERS:raise ValueError('Invalid finding classification')
    return {'code':code,'severity':severity,'status':status,'layer':layer,'subject':str(subject),'detail':detail,'source':source,'scope':scope}
