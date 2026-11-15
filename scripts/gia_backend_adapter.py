"""Schema 2 GIA export adapters; upstream files and GraphModels remain unchanged."""
from pathlib import Path
import runpy,sys


def collect_signals(collect,*,graph_payload,signal_params_by_name,composite_mgr,composite_loaded):
    # Registered event nodes carry their signal name as title, not as an input.
    # Adapt only the dependency collector's view, including composite subgraphs.
    queue=[graph_payload];visited=set();specs={}
    while queue:
        payload=queue.pop(0);nodes=[]
        for node in payload.get('nodes',[]):
            title=node.get('title');reference=node.get('node_def_ref',{})
            if reference.get('kind')=='event' and title in signal_params_by_name:
                constants=node.get('input_constants',{})
                if '信号名'in constants and constants['信号名']!=title:
                    raise ValueError('Signal event title disagrees with selector: '+title)
                node={**node,'title':'监听信号','input_constants':{**constants,'信号名':title}}
            nodes.append(node)
            ident=node.get('composite_id')
            if composite_mgr is not None and ident and ident not in visited:
                visited.add(ident)
                if ident not in composite_loaded:
                    if not composite_mgr.load_subgraph_if_needed(ident):
                        raise ValueError('Cannot load signal dependency composite: '+ident)
                    composite_loaded[ident]=composite_mgr.get_composite_node(ident)
                child=composite_loaded[ident]
                if child is None:raise ValueError('Missing signal dependency composite: '+ident)
                if child.sub_graph is not None:queue.append(child.sub_graph)
        for spec in collect(graph_payload={**payload,'nodes':nodes},signal_params_by_name=signal_params_by_name,
                            composite_mgr=None,composite_loaded=composite_loaded):
            name=spec['signal_name']
            if name in specs and specs[name]!=spec:raise ValueError('Conflicting signal dependency: '+name)
            specs[name]=spec
    return list(specs.values())


def main():
    runner=Path(sys.argv[1]).resolve();runtime=runner.parent.parent
    sys.path[:0]=[str(runtime),str(runner.parent)]
    from ugc_file_tools.pipelines.project_export_gia_parts import pipeline
    from ugc_file_tools.signal_writeback import gia_export
    collect=pipeline._collect_used_signal_specs_from_graph_payload
    pipeline._collect_used_signal_specs_from_graph_payload=lambda **kwargs:collect_signals(collect,**kwargs)
    allocate=gia_export._set_node_def_id_inplace
    def set_id(node_def,*,node_def_id_int):
        meta=node_def['4'];kernel=meta.get('2',{})
        client_kernel=kernel=={'1':10001,'2':20002,'3':22000,'5':2000}
        allocate(node_def,node_def_id_int=node_def_id_int)
        if client_kernel:meta['2']['5']=2000
    gia_export._set_node_def_id_inplace=set_id
    sys.argv=[str(runner),*sys.argv[2:]]
    runpy.run_path(str(runner),run_name='__main__')


if __name__=='__main__':main()
