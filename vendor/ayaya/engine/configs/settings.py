"""全局设置模块 - 控制程序行为和调试选项

这个模块提供了一个集中的配置系统，用于控制程序的各种行为。
支持从配置文件加载和保存设置，并提供UI界面进行设置。

使用方法：
    from engine.configs.settings import settings
    from engine.utils.logging.logger import log_info
    
    if settings.LAYOUT_DEBUG_PRINT:
        log_info("调试信息")
    
    # 保存设置
    settings.save()
    
    # 加载设置
    settings.load()
"""
import json
from pathlib import Path
from typing import Any, Dict, Optional
from engine.utils.logging.logger import log_info, log_warn
DEFAULT_USER_SETTINGS_RELATIVE_PATH = Path('app/runtime/cache/user_settings.json')

class Settings:
    """全局设置类
    
    所有设置项都是类属性，可以直接访问和修改。
    """
    LAYOUT_DEBUG_PRINT: bool = False
    NODE_LOADING_VERBOSE: bool = False
    NODE_ALIAS_INJECT_IN_LIBRARY: bool = True
    GRAPH_UI_VERBOSE: bool = False
    UI_TWO_ROW_FIELD_DEBUG_PRINT: bool = False
    PREVIEW_VERBOSE: bool = False
    VALIDATOR_VERBOSE: bool = False
    RUNTIME_NODE_GRAPH_VALIDATION_ENABLED: bool = True
    STRICT_ENTITY_INPUTS_WIRE_ONLY: bool = False
    SAFETY_NOTICE_SUPPRESSED: bool = False
    NODE_IMPL_LOG_VERBOSE: bool = False
    DEBUG_LOG_VERBOSE: bool = False
    UI_UNHANDLED_EXCEPTION_DIALOG_ENABLED: bool = False
    APP_PERF_MONITOR_ENABLED: bool = False
    APP_PERF_OVERLAY_ENABLED: bool = False
    APP_PERF_STALL_THRESHOLD_MS: int = 250
    APP_PERF_CAPTURE_STACKS_ENABLED: bool = True
    AUTO_SAVE_INTERVAL: float = 0.0
    GRAPH_PARSER_VERBOSE: bool = False
    GRAPH_GENERATOR_VERBOSE: bool = False
    UGC_GIA_NODE_POS_SCALE: float = 2.0
    UI_THEME_MODE: str = 'auto'
    RESOURCE_LIBRARY_AUTO_REFRESH_ENABLED: bool = True
    RUNTIME_CACHE_ROOT: str = 'app/runtime/cache'
    PRIVATE_EXTENSION_ENABLED: bool = True
    PRIVATE_EXTENSION_SYS_PATHS: list[str] = []
    PRIVATE_EXTENSION_MODULES: list[str] = []
    LAYOUT_DATA_LAYER_SORT: str = 'none'
    LAYOUT_ENABLE_GEOMETRIC_SLOT: bool = False
    LAYOUT_STRICT_NODE_KIND: bool = False
    LAYOUT_TIGHT_BLOCK_PACKING: bool = True
    LAYOUT_NODE_SPACING_X_PERCENT: int = 100
    LAYOUT_NODE_SPACING_Y_PERCENT: int = 100
    LAYOUT_COMPACT_DATA_Y_IN_BLOCK: bool = True
    LAYOUT_DATA_Y_COMPACT_PULL: float = 0.6
    LAYOUT_DATA_Y_COMPACT_SLACK_THRESHOLD: float = 200.0
    DATA_NODE_CROSS_BLOCK_COPY: bool = True
    LAYOUT_AUTO_INSERT_LOCAL_VAR_RELAY: bool = False
    LAYOUT_LOCAL_VAR_RELAY_MAX_BLOCK_DISTANCE: int = 5
    LAYOUT_ALGO_VERSION: int = 2
    LAYOUT_MAX_CHAINS_PER_NODE: int = 32
    LAYOUT_MIN_PATHS_PER_INPUT: int = 1
    LAYOUT_MAX_CHAINS_PER_START: int = 512
    LAYOUT_DEBUG_MAX_PORTS: int = 5
    SHOW_BASIC_BLOCKS: bool = True
    BASIC_BLOCK_ALPHA: float = 0.2
    SHOW_LAYOUT_Y_DEBUG: bool = False
    GRAPH_NODE_CONTENT_ALPHA: float = 0.7
    GRAPH_PERF_PANEL_ENABLED: bool = False
    GRAPH_SCENE_LRU_CACHE_SIZE: int = 2
    GRAPH_CONSTANT_WIDGET_VIRTUALIZATION_ENABLED: bool = True
    GRAPH_FAST_PREVIEW_ENABLED: bool = False
    GRAPH_FAST_PREVIEW_NODE_THRESHOLD: int = 500
    GRAPH_FAST_PREVIEW_EDGE_THRESHOLD: int = 900
    GRAPH_FAST_PREVIEW_BATCHED_EDGES_ENABLED: bool = True
    GRAPH_READONLY_BATCHED_EDGES_ENABLED: bool = True
    GRAPH_READONLY_BATCHED_EDGES_EDGE_THRESHOLD: int = 900
    GRAPH_AUTO_FIT_ALL_ENABLED: bool = False
    GRAPH_LOD_ENABLED: bool = True
    GRAPH_LOD_NODE_DETAILS_MIN_SCALE: float = 0.55
    GRAPH_LOD_NODE_TITLE_MIN_SCALE: float = 0.28
    GRAPH_LOD_PORT_MIN_SCALE: float = 0.3
    GRAPH_LOD_EDGE_MIN_SCALE: float = 0.22
    GRAPH_LOD_EDGE_HITTEST_MIN_SCALE: float = 0.28
    GRAPH_GRID_MIN_PX: float = 12.0
    GRAPH_GRID_ENABLED: bool = True
    GRAPH_PAN_HIDE_ICONS_ENABLED: bool = True
    GRAPH_PAN_FREEZE_VIEWPORT_ENABLED: bool = False
    GRAPH_ZOOM_FREEZE_VIEWPORT_ENABLED: bool = False
    GRAPH_LOD_PORT_VISIBILITY_EXIT_SCALE: float = 0.33
    GRAPH_LOD_EDGE_VISIBILITY_EXIT_SCALE: float = 0.24
    GRAPH_BLOCK_OVERVIEW_ENABLED: bool = True
    GRAPH_BLOCK_OVERVIEW_ENTER_SCALE: float = 0.1
    GRAPH_BLOCK_OVERVIEW_EXIT_SCALE: float = 0.12
    GRAPH_BLOCK_OVERVIEW_GRID_MIN_PX: float = 24.0
    TEXT_INPUT_METHOD: str = 'clipboard'
    FINGERPRINT_ENABLED: bool = True
    FINGERPRINT_K: int = 10
    FINGERPRINT_ROUND_DIGITS: int = 3
    FINGERPRINT_MAX_DIST: float = 0.2
    FINGERPRINT_MIN_OVERLAP: int = 4
    FINGERPRINT_DEBUG_LOG: bool = False
    UNIQUE_NODE_FALLBACK_ENABLED: bool = True
    UNIQUE_NODE_FALLBACK_DEFAULT_SCALE: float = 1.0
    _config_file: Optional[Path] = None
    _workspace_root: Optional[Path] = None

    def __repr__(self) -> str:
        """返回所有设置的字符串表示"""
        settings_dict = {key: value for key, value in self.__class__.__dict__.items() if not key.startswith('_') and key.isupper()}
        return f'Settings({settings_dict})'

    @classmethod
    def set_config_path(cls, workspace_path: Path):
        """设置配置文件路径
        
        Args:
            workspace_path: 工作空间根目录
        """
        config_file = workspace_path / DEFAULT_USER_SETTINGS_RELATIVE_PATH
        log_info('[BOOT][Settings] set_config_path: workspace_path={} -> config_file={}', workspace_path, config_file)
        cls._config_file = config_file
        cls._workspace_root = workspace_path.resolve()

    def _get_all_settings(self) -> Dict[str, Any]:
        """获取所有设置项的字典
        
        注意：从实例获取属性，以支持实例属性覆盖类属性的情况
        """
        return {key: getattr(self, key) for key in dir(self.__class__) if not key.startswith('_') and key.isupper()}

    def save(self) -> bool:
        """保存设置到配置文件
        
        Returns:
            是否保存成功
        """
        if self.__class__._config_file is None:
            log_warn('⚠️  警告：配置文件路径未设置，无法保存设置')
            return False
        settings_dict = self._get_all_settings()
        self.__class__._config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.__class__._config_file, 'w', encoding='utf-8') as file:
            json.dump(settings_dict, file, indent=2, ensure_ascii=False)
        return True

    def load(self) -> bool:
        """从配置文件加载设置
        
        Returns:
            是否加载成功
        """
        config_file = self.__class__._config_file
        if config_file is None:
            log_info('[BOOT][Settings] load: _config_file 未设置，跳过加载，使用类默认值')
            return False
        if not config_file.exists():
            log_info('[BOOT][Settings] load: 配置文件不存在（{}），跳过加载，使用类默认值', config_file)
            return False
        log_info('[BOOT][Settings] load: 准备从 {} 加载配置', config_file)
        with open(config_file, 'r', encoding='utf-8') as file:
            settings_dict = json.load(file)
        applied_count = 0
        for key, value in settings_dict.items():
            if hasattr(self.__class__, key) and key.isupper():
                setattr(self, key, value)
                applied_count += 1
        self.RESOURCE_LIBRARY_AUTO_REFRESH_ENABLED = True
        log_info('[BOOT][Settings] load: 配置加载完成，共应用 {} 个键', applied_count)
        return True

    @classmethod
    def reset_to_defaults(cls):
        """重置所有设置为默认值"""
        cls.LAYOUT_DEBUG_PRINT = False
        cls.NODE_LOADING_VERBOSE = False
        cls.UI_TWO_ROW_FIELD_DEBUG_PRINT = False
        cls.PREVIEW_VERBOSE = False
        cls.VALIDATOR_VERBOSE = False
        cls.RUNTIME_NODE_GRAPH_VALIDATION_ENABLED = False
        cls.AUTO_SAVE_INTERVAL = 0.0
        cls.GRAPH_PARSER_VERBOSE = False
        cls.GRAPH_GENERATOR_VERBOSE = False
        cls.UGC_GIA_NODE_POS_SCALE = 2.0
        cls.SAFETY_NOTICE_SUPPRESSED = False
        cls.UI_UNHANDLED_EXCEPTION_DIALOG_ENABLED = False
        cls.APP_PERF_MONITOR_ENABLED = False
        cls.APP_PERF_OVERLAY_ENABLED = False
        cls.APP_PERF_STALL_THRESHOLD_MS = 250
        cls.APP_PERF_CAPTURE_STACKS_ENABLED = True
        cls.RUNTIME_CACHE_ROOT = 'app/runtime/cache'
        cls.RESOURCE_LIBRARY_AUTO_REFRESH_ENABLED = True
        cls.PRIVATE_EXTENSION_ENABLED = True
        cls.PRIVATE_EXTENSION_SYS_PATHS = []
        cls.PRIVATE_EXTENSION_MODULES = []
        cls.LAYOUT_DATA_LAYER_SORT = 'none'
        cls.LAYOUT_ENABLE_GEOMETRIC_SLOT = True
        cls.LAYOUT_STRICT_NODE_KIND = False
        cls.LAYOUT_TIGHT_BLOCK_PACKING = True
        cls.LAYOUT_NODE_SPACING_X_PERCENT = 100
        cls.LAYOUT_NODE_SPACING_Y_PERCENT = 100
        cls.DATA_NODE_CROSS_BLOCK_COPY = True
        cls.LAYOUT_AUTO_INSERT_LOCAL_VAR_RELAY = False
        cls.LAYOUT_LOCAL_VAR_RELAY_MAX_BLOCK_DISTANCE = 5
        cls.SHOW_BASIC_BLOCKS = True
        cls.BASIC_BLOCK_ALPHA = 0.2
        cls.SHOW_LAYOUT_Y_DEBUG = False
        cls.GRAPH_NODE_CONTENT_ALPHA = 0.7
        cls.GRAPH_PERF_PANEL_ENABLED = False
        cls.GRAPH_SCENE_LRU_CACHE_SIZE = 2
        cls.GRAPH_CONSTANT_WIDGET_VIRTUALIZATION_ENABLED = True
        cls.GRAPH_FAST_PREVIEW_ENABLED = False
        cls.GRAPH_FAST_PREVIEW_NODE_THRESHOLD = 500
        cls.GRAPH_FAST_PREVIEW_EDGE_THRESHOLD = 900
        cls.GRAPH_FAST_PREVIEW_BATCHED_EDGES_ENABLED = True
        cls.GRAPH_READONLY_BATCHED_EDGES_ENABLED = True
        cls.GRAPH_READONLY_BATCHED_EDGES_EDGE_THRESHOLD = 900
        cls.GRAPH_AUTO_FIT_ALL_ENABLED = False
        cls.GRAPH_LOD_ENABLED = True
        cls.GRAPH_LOD_NODE_DETAILS_MIN_SCALE = 0.55
        cls.GRAPH_LOD_NODE_TITLE_MIN_SCALE = 0.28
        cls.GRAPH_LOD_PORT_MIN_SCALE = 0.3
        cls.GRAPH_LOD_EDGE_MIN_SCALE = 0.22
        cls.GRAPH_LOD_EDGE_HITTEST_MIN_SCALE = 0.28
        cls.GRAPH_GRID_MIN_PX = 12.0
        cls.GRAPH_GRID_ENABLED = True
        cls.GRAPH_PAN_HIDE_ICONS_ENABLED = True
        cls.GRAPH_PAN_FREEZE_VIEWPORT_ENABLED = False
        cls.GRAPH_ZOOM_FREEZE_VIEWPORT_ENABLED = False
        cls.GRAPH_LOD_PORT_VISIBILITY_EXIT_SCALE = 0.33
        cls.GRAPH_LOD_EDGE_VISIBILITY_EXIT_SCALE = 0.24
        cls.GRAPH_BLOCK_OVERVIEW_ENABLED = True
        cls.GRAPH_BLOCK_OVERVIEW_ENTER_SCALE = 0.1
        cls.GRAPH_BLOCK_OVERVIEW_EXIT_SCALE = 0.12
        cls.GRAPH_BLOCK_OVERVIEW_GRID_MIN_PX = 24.0
        cls.TEXT_INPUT_METHOD = 'clipboard'
        cls.FINGERPRINT_ENABLED = True
        cls.FINGERPRINT_K = 10
        cls.FINGERPRINT_ROUND_DIGITS = 3
        cls.FINGERPRINT_MAX_DIST = 0.2
        cls.FINGERPRINT_MIN_OVERLAP = 4
        cls.FINGERPRINT_DEBUG_LOG = False
        log_info('✅ 已重置所有设置为默认值')

    @classmethod
    def enable_debug_mode(cls):
        """启用所有调试选项（用于开发调试）"""
        cls.LAYOUT_DEBUG_PRINT = True
        cls.NODE_LOADING_VERBOSE = True
        cls.UI_TWO_ROW_FIELD_DEBUG_PRINT = True
        cls.PREVIEW_VERBOSE = True
        cls.VALIDATOR_VERBOSE = True
        cls.GRAPH_PARSER_VERBOSE = True
        cls.GRAPH_GENERATOR_VERBOSE = True
        cls.RUNTIME_NODE_GRAPH_VALIDATION_ENABLED = True
        log_info('🔧 已启用调试模式：所有详细日志已打开')

    @classmethod
    def disable_debug_mode(cls):
        """禁用所有调试选项（恢复默认）"""
        cls.LAYOUT_DEBUG_PRINT = False
        cls.NODE_LOADING_VERBOSE = False
        cls.UI_TWO_ROW_FIELD_DEBUG_PRINT = False
        cls.PREVIEW_VERBOSE = False
        cls.VALIDATOR_VERBOSE = False
        cls.GRAPH_PARSER_VERBOSE = False
        cls.GRAPH_GENERATOR_VERBOSE = False
        cls.UI_THEME_MODE = 'auto'
        log_info('✅ 已禁用调试模式：恢复默认设置')
settings = Settings()
