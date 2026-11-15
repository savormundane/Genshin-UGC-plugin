from pathlib import Path
import argparse,importlib,sys
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root),str(root/'private_extensions')]
TOOLS=['parse_gia_to_graph_ir', 'gia_to_readable_json', 'export_graph_ir_from_package', 'generate_graph_code_from_package', 'export_graph_model_json_from_graph_code', 'export_project_graphs_to_gia', 'gia_graph_ir_to_gia', 'export_ui_workbench_bundles_from_html', 'check_graph_variable_writeback_contract']
def main():
    p=argparse.ArgumentParser(description='Bundled offline file tools; no GUI/OCR/automation')
    subs=p.add_subparsers(dest='mode',required=True)
    t=subs.add_parser('tool');t.add_argument('name',choices=TOOLS);t.add_argument('args',nargs=argparse.REMAINDER)
    from ugc_file_tools.unified_cli.project import add_subparser_project
    add_subparser_project(subs)
    a=p.parse_args()
    if a.mode=='tool':
        m=importlib.import_module('ugc_file_tools.commands.'+a.name)
        m.main(a.args)
    else:a.entrypoint(a)
if __name__=='__main__':main()
