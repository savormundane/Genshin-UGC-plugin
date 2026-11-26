"""Layer-specific case requirements, with no inferred editor/host success."""

from authoring_io import PLUGIN, read_json

LAYERS = (
    'rules',
    'generation',
    'readback',
    'lua_model',
    'native_graph_model',
    'software_preview',
    'editor',
    'host',
    'user_acceptance',
)


def describe(proof, verified, layer_cases=None):
    declarations = read_json(PLUGIN / 'scripts/capability-layers.json')
    if declarations.get('schema') != 1:
        raise ValueError('Unknown capability layer schema')
    passed = {
        row['test'] + '::' + case['id']
        for row in (proof or {}).get('results', [])
        if row.get('passed') is True and row.get('exit_code') == 0
        for case in row.get('cases', [])
        if case.get('status') == 'passed'
    }
    result = {}
    for name, registered in declarations['capabilities'].items():
        if set(registered) - set(LAYERS):
            raise ValueError('Unknown capability layer')
        result[name] = {}
        for layer in LAYERS:
            entry = registered.get(layer)
            if entry is None:
                result[name][layer] = {
                    'implementation': 'not_registered',
                    'status': 'not_checked',
                    'scope': 'No executable layer contract registered',
                    'required_cases': [],
                }
                continue
            cases = (layer_cases or {}).get(name, {}).get(layer, [])
            if layer_cases is not None and (not cases or len(cases) != len(set(cases))):
                raise ValueError('Unique nonempty layer cases required')
            if layer in ('editor', 'host', 'user_acceptance'):
                raise ValueError('Offline cases cannot certify editor, host or user acceptance')
            result[name][layer] = {
                'implementation': entry['implementation'],
                'scope': entry['scope'],
                'status': 'passed'
                if verified and cases and set(cases) <= passed
                else 'not_checked',
                'required_cases': cases,
                'missing_cases': sorted(set(cases) - passed),
            }
    return result
