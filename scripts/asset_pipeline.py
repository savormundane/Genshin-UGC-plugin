"""Python and direct script entry for existing asset tools."""
from miliastra.assets.pipeline import (
    compile_grid,
    generate,
    lua,
    lua_payload,
    main,
    positive,
    prepare_source,
    preview,
    procedural,
)

__all__ = [
    'compile_grid', 'generate', 'lua', 'lua_payload', 'main', 'positive',
    'prepare_source', 'preview', 'procedural',
]

if __name__ == '__main__':
    raise SystemExit(main())
