from pathlib import Path
import argparse,sys
from engine.utils.workspace import init_settings_for_workspace
def main():
    p=argparse.ArgumentParser(description="Headless Graph Code validation")
    p.add_argument("action",choices=["validate-file","validate-project","validate-ui"])
    p.add_argument("file",nargs="?")
    p.add_argument("--strict",action="store_true")
    p.add_argument("--package-id",default="")
    a=p.parse_args();a.apply_fixes=False;a.fix_dry_run=False
    root=Path(__file__).resolve().parents[2]
    init_settings_for_workspace(workspace_root=root,load_user_settings=False)
    if a.action=="validate-file":
        from app.cli.commands.graph_validation import run_validate_file
        if not a.file:p.error("file required")
        return run_validate_file(a,root)
    if a.action=="validate-project":
        from app.cli.commands.project_tools import run_validate_project
        return run_validate_project(a,root)
    from app.cli.commands.ui_tools import run_validate_ui
    return run_validate_ui(a,root)
if __name__=="__main__":raise SystemExit(main())
