"""Stable technical ownership; workflows and persisted owners are not Skill discovery."""
DOMAINS={
    'editor':'qianxing-editor','graph':'qianxing-graph-code','client':'qianxing-editor',
    'gil':'qianxing-gil','assets':'qianxing-assets'}
DOMAIN_TOOLS={
    'editor':['docs','platform','project','resources','ids','ui','scene'],
    'graph':['nodes','graph','build'],'client':['client','simulate'],
    'gil':['native','level','inspect','verify'],'assets':['assets']}
TASK_ENTRYPOINTS = {
    'game': {'cli': ['produce JOB.json --out DIR'], 'mcp': ['produce']},
    'editor': {'cli': ['project search INPUT QUERY', 'docs search --version VERSION QUERY'],
               'mcp': ['project_inspect', 'docs_search']},
    'nodes': {'cli': ['nodes QUERY', 'graph check SOURCE.py', 'build SPEC.json --out DIR'],
              'mcp': ['nodes_lookup', 'graph_check']},
    'lua': {'cli': ['knowledge api SYMBOL', 'client check INPUT'], 'mcp': ['api_lookup', 'client_check']},
    'gil': {'cli': ['project search INPUT QUERY', 'native plan INPUT --spec PATCH.json --out PLAN.json',
                    'native apply INPUT --plan PLAN.json --out EDITED.gil', 'native diff INPUT EDITED.gil'],
            'mcp': ['project_inspect', 'native_plan', 'native_apply', 'native_diff']},
    'assets': {'cli': ['assets preview INPUT --out DIR',
                       'assets generate --from-preview REPORT.json --candidate NAME --out DIR',
                       'assets batch preview SPEC.json --out DIR', 'assets batch generate REPORT.json --out DIR',
                       'assets fit SOURCE.png --spec SPEC.json --out DIR'],
               'mcp': ['resources_lookup', 'asset_preview', 'asset_generate']},
    'animation': {'cli': ['client assemble SPEC.json --out SOURCE.lua', 'simulate preview SPEC.json --out DIR'], 'mcp': ['client_check']},
    'diagnosis': {'cli': ['diagnose SPEC.json'], 'mcp': ['diagnose']},
    'storage': {'cli': ['storage --help', 'produce JOB.json --out DIR'], 'mcp': ['produce']},
    'protocol': {'cli': ['produce JOB.json --out DIR', 'simulate run SCENE.json'], 'mcp': ['produce','simulate']},
}
# Capability IDs remain those published by capabilities.py. Empty ownership means
# a shared tool. The client domain shares the Editor Skill.
OWNERS={
    'knowledge':('editor','client'),'diagnosis':(), 'asset_fit':('assets',),'asset_inspection':('assets',),'asset_batch':('assets',),
    'mcp':(), 'native':('gil',),'storage':('editor','graph','client','gil'),
    'protocol':('graph','client'),'ui':('client',),'assembly':('client',),
    'simulation':('graph','client'),'algorithms':('client',),'native_assets':('assets','gil'),
    'production':(), 'platform':('editor',),'project':('editor',),'native_changes':('gil',),'scene':('editor','gil','assets')}
WORKFLOWS={
    'multiplayer':{'domains':['graph','client'],'capabilities':['protocol','simulation'],'guide':'references/workflows/qianxing-multiplayer/README.md'},
    'animation':{'domains':['client','assets'],'capabilities':['ui','assembly'],'guide':'references/assets/animation.md'},
    'storage':{'domains':['editor','graph','client','gil'],'capabilities':['storage'],'guide':'references/workflows/storage-authoring.md'},
    'gil-assembly':{'domains':['gil','graph','client'],'capabilities':['native','production'],'guide':'references/workflows/qianxing-gil-assembly-pipeline/README.md'},
    'catalog-merge':{'domains':['client','assets'],'capabilities':['assembly','native_assets'],'guide':'references/workflows/generated-lua-catalog-merge/README.md'},
    'diagnosis':{'domains':list(DOMAINS),'capabilities':['diagnosis','project','native_changes'],'guide':'references/workflows/qianxing-release-integrity-triage/README.md'}}
LEGACY_OWNERS={
    'qianxing-multiplayer':'multiplayer','qianxing-animation':'animation',
    'qianxing-gil-assembly-pipeline':'gil-assembly','generated-lua-catalog-merge':'catalog-merge',
    'qianxing-release-integrity-triage':'diagnosis'}

def resolve_owner(owner):
    if owner=='client-controls-lua':return {'kind':'domain','id':'client','skills':[DOMAINS['client']]}
    if owner in DOMAINS.values():return {'kind':'domain','id':next(k for k,v in DOMAINS.items()if v==owner),'skills':[owner]}
    workflow=LEGACY_OWNERS.get(owner,owner)
    if workflow in WORKFLOWS:
        return {'kind':'workflow','id':workflow,'skills':list(dict.fromkeys(DOMAINS[d] for d in WORKFLOWS[workflow]['domains']))}
    if owner in OWNERS:return {'kind':'capability','id':owner,'skills':list(dict.fromkeys(DOMAINS[d] for d in OWNERS[owner]))}
    raise ValueError('Unknown workflow owner: '+str(owner))

def describe():
    from capabilities import CAPABILITIES,SUPPORT
    if set(CAPABILITIES)!=set(OWNERS):raise ValueError('Capability ownership registration differs')
    return {'schema':1,'domains':DOMAINS,'domain_tools':DOMAIN_TOOLS,'task_entrypoints':TASK_ENTRYPOINTS,
            'shared_tools':['knowledge','diagnose','logs','doctor','capabilities','produce','workflow','experiment','beyond','mcp'],
            'workflows':WORKFLOWS,'legacy_owners':LEGACY_OWNERS,
            'capabilities':{key:{'domains':list(OWNERS[key]),'entry':'scripts/'+entry,'guide':guide,
                                 'operations':SUPPORT[key].get('operations',[])}for key,(entry,guide)in CAPABILITIES.items()},
            'scope':'implementation and task ownership only; no execution or host evidence'}
