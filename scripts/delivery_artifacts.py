"""Delivery roles for generated production files, independent of file extensions."""
from pathlib import PurePosixPath

def roles(files):
    result={}
    evidence={'manifest.json','production-report.json','build-report.json','compiler-report.json',
              'replacement-report.json','report.json','native-report.json','native-audit.json',
              'dependency-graph.json','environment.json','simulation.json','experiment.json','external-simulation.json',
              'source-map.json','client-bindings.json','client-check.json','client-replies.json','storage-mount.json',
              'protocol-client-targets.json','platform-report.json','resource-report.json','client-resource-report.json','project-report.json','native-diff.json','native-plan.json'}
    intermediate={'base.gil','legacy-job.json','graph-job.json','graph-bindings.json','resource-job.json'}
    for name in files:
        path=PurePosixPath(name)
        # Generated native resource definitions are deliverables even when their
        # project-selected basename resembles a report or uses an unusual suffix.
        resource=any(part in path.parts for part in ('merged-resources','protocol-graph-resources'))or any(path.parts[i:i+2]==('storage','resources')or path.parts[i:i+2]==('protocol-native','resources')for i in range(len(path.parts)-1))
        role='delivery'
        if not resource:
            if path.parts[0]=='portable':role='input_snapshot'
            elif 'logs'in path.parts or path.name in evidence:role='evidence'
            elif path.name in intermediate or 'graphs'in path.parts and 'models'in path.parts:role='intermediate'
        result[name]={'role':role,'comparison':'bytes'if role=='delivery'else'recorded_only'}
    return result

def compare(before,after,left,right):
    if set(before)!=set(after):
        return {'differences':sorted(set(before)^set(after)),'compared':0,'role_changes':[]}
    changed=[name for name in before if before[name]!=after[name]]
    byte_files=[name for name,item in before.items()if item['comparison']=='bytes']
    differences=[name for name in byte_files if not(right/name).is_file()or(left/name).read_bytes()!=(right/name).read_bytes()]
    return {'differences':differences,'compared':len(byte_files),'role_changes':changed}
