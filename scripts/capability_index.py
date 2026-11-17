"""Stable technical ownership; workflows and persisted owners are not Skill discovery."""
DOMAINS={
    'editor':'qianxing-editor','graph':'qianxing-graph-code','client':'client-controls-lua',
    'gil':'qianxing-gil','assets':'qianxing-assets'}
DOMAIN_TOOLS={
    'editor':['docs','platform','project','resources','ids','ui'],
    'graph':['nodes','build'],'client':['client','simulate'],
    'gil':['native','level','inspect','verify'],'assets':['assets']}
# Capability IDs remain those published by capabilities.py. Empty ownership means
# a shared tool, not an invented sixth platform domain.
OWNERS={
    'knowledge':('editor','client'),'diagnosis':(), 'asset_fit':('assets',),'asset_inspection':('assets',),
    'mcp':(), 'native':('gil',),'storage':('editor','graph','client','gil'),
    'protocol':('graph','client'),'ui':('client',),'assembly':('client',),
    'simulation':('graph','client'),'algorithms':('client',),'native_assets':('assets','gil'),
    'production':(), 'platform':('editor',),'project':('editor',),'native_changes':('gil',)}
WORKFLOWS={
    'multiplayer':{'domains':['graph','client'],'capabilities':['protocol','simulation'],'guide':'references/workflows/qianxing-multiplayer/README.md'},
    'animation':{'domains':['client','assets'],'capabilities':['ui','assembly'],'guide':'references/workflows/qianxing-animation/README.md'},
    'storage':{'domains':['editor','graph','client','gil'],'capabilities':['storage'],'guide':'references/storage-authoring.md'},
    'gil-assembly':{'domains':['gil','graph','client'],'capabilities':['native','production'],'guide':'references/workflows/qianxing-gil-assembly-pipeline/README.md'},
    'catalog-merge':{'domains':['client','assets'],'capabilities':['assembly','native_assets'],'guide':'references/workflows/generated-lua-catalog-merge/README.md'},
    'diagnosis':{'domains':list(DOMAINS),'capabilities':['diagnosis','project','native_changes'],'guide':'references/workflows/qianxing-release-integrity-triage/README.md'}}
LEGACY_OWNERS={
    'qianxing-multiplayer':'multiplayer','qianxing-animation':'animation',
    'qianxing-gil-assembly-pipeline':'gil-assembly','generated-lua-catalog-merge':'catalog-merge',
    'qianxing-release-integrity-triage':'diagnosis'}

def resolve_owner(owner):
    if owner in DOMAINS.values():return {'kind':'domain','id':next(k for k,v in DOMAINS.items()if v==owner),'skills':[owner]}
    workflow=LEGACY_OWNERS.get(owner,owner)
    if workflow in WORKFLOWS:
        return {'kind':'workflow','id':workflow,'skills':[DOMAINS[d]for d in WORKFLOWS[workflow]['domains']]}
    if owner in OWNERS:return {'kind':'capability','id':owner,'skills':[DOMAINS[d]for d in OWNERS[owner]]}
    raise ValueError('Unknown workflow owner: '+str(owner))

def describe():
    from capabilities import CAPABILITIES,SUPPORT
    if set(CAPABILITIES)!=set(OWNERS):raise ValueError('Capability ownership registration differs')
    return {'schema':1,'domains':DOMAINS,'domain_tools':DOMAIN_TOOLS,'shared_tools':['knowledge','diagnose','logs','doctor','capabilities','produce','workflow','experiment','beyond','mcp'],
            'workflows':WORKFLOWS,'legacy_owners':LEGACY_OWNERS,
            'capabilities':{key:{'domains':list(OWNERS[key]),'entry':'scripts/'+entry,'guide':'references/'+guide,
                                 'operations':SUPPORT[key].get('operations',[])}for key,(entry,guide)in CAPABILITIES.items()},
            'scope':'implementation and task ownership only; no execution or host evidence'}
