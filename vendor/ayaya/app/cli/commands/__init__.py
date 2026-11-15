from .graph_validation import register_graph_validation_commands
from .project_tools import register_project_tools_commands
from .ui_tools import register_ui_tools_commands
def register_all_graph_tools_commands(p):
    register_graph_validation_commands(p)
    register_project_tools_commands(p)
    register_ui_tools_commands(p)
