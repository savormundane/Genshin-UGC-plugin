"""The plugin's evidence-bound value port contracts."""
from functools import lru_cache
import json

from authoring_io import PLUGIN, sha


REGISTRY = PLUGIN / 'scripts/node-contracts.json'


@lru_cache(maxsize=1)
def node_contracts():
    raw = REGISTRY.read_bytes()
    data = json.loads(raw.decode('utf-8-sig'))
    if data['schema'] != 1:
        raise ValueError('Unknown supported node contract schema')
    source = {'path': REGISTRY.relative_to(PLUGIN).as_posix(), 'sha256': sha(raw)}
    contracts = {(row['scope'], row['call']): {**row, 'contract': source} for row in data['nodes']}
    if len(contracts) != len(data['nodes']):
        raise ValueError('Node contract scope and call must be unique')
    return contracts


def port_evidence(scope, call):
    from platform_profiles import documents

    contract = node_contracts()[(scope, call)]
    document = documents(contract['platform_version'])[contract['document_id']]
    if document['source_sha256'] != contract['source_sha256'] or document['inherited']:
        raise ValueError(f'{document["source_version"]} {call} port evidence differs from its contract')
    return {
        **{key: document[key] for key in ('id', 'path', 'sha256', 'source_kind', 'official_url',
                                         'source_version', 'source_sha256')},
        'source_section': contract['section'],
        'source_line': contract['source_line'],
        'scope': 'documented_value_ports',
        'contract': dict(contract['contract']),
        'documented_inputs': [{'name': name, 'type': kind} for name, kind in contract['inputs']],
        'documented_outputs': [{'name': name, 'type': kind} for name, kind in contract['outputs']],
    }


def calibrated_ports(scope, call, directions):
    contract = node_contracts().get((scope, call))
    if contract is None:
        return directions
    return {
        **directions,
        **{
            side: [
                *[pin for pin in directions.get(side, ()) if pin[1] == '流程'],
                *[tuple(pin) for pin in contract[side]],
            ]
            for side in ('inputs', 'outputs')
        },
    }
