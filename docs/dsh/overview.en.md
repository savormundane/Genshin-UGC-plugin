Look up Miliastra Wonderland nodes and Lua APIs, inspect level files, and create graphs and assets in DeepSeek Harness.

## Try a node lookup

Enable the plugin and send this request in a session that can run local tools.

> Use Miliastra Wonderland to find the server-side Create Entity node. List its inputs and outputs, with the version they apply to.

Look for a `nodes_lookup` call that lists Target GUID as an input and Flow out as an output. You can query the bundled reference data right away. Select and authorize your project directory when a task needs to read or write files.

## Work with your project

- **Inspect a level.** Give the assistant a GIL or GIA file and the object you want to find. Review any edit plan before saving a separate copy.
- **Build gameplay and interfaces.** Check node ports and Lua, create static scenes, or fit an image to primitives and preview the generated script in Beyond.

Native writes use samples calibrated for the target version. Test the exported files in the game to confirm their behavior.

## Local requirements

The full toolset targets Windows x64. Use DeepSeek Harness 0.2.2-rc.5, Node.js 24.9 or later, and CPython 3.11–3.14 with the required packages or uv on PATH. Preparing Python dependencies on first use may require a network connection. [Installation checks](https://github.com/savormundane/miliastra-wonderland-plugin/blob/main/docs/installation.md#安装自检) · [Creator tutorials](https://github.com/savormundane/miliastra-wonderland-plugin/tree/main/samples/creator-demos)
