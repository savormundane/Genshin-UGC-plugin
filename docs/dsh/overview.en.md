Look up Miliastra Wonderland nodes and Lua APIs, inspect level files, and create graphs and assets in DeepSeek Harness.

## Try a node lookup

Enable the plugin and send this request in a session that can run local tools.

> Use Miliastra Wonderland to find the server-side Create Entity node. List its inputs and outputs, with the version they apply to.

Look for a `nodes_lookup` call that lists Target GUID as an input and Flow out as an output. You can query the bundled reference data right away. Select and authorize your project directory when a task needs to read or write files.

## Work with your project

- **Inspect a level.** Give the assistant a GIL or GIA file and the object you want to find. Review any edit plan before saving a separate copy.
- **Build gameplay and interfaces.** Check node ports and Lua, create static scenes, or fit an image to primitives and preview the generated script in Beyond.

## Local tools

In a DSH session with slash commands, enter `/miliastra-check` to run the plugin's installation check. It works without a model call and can diagnose an MCP startup failure.

The full toolset targets Windows x64. Setting up dependencies for the first time may require a network connection. [Supported versions and requirements](https://github.com/savormundane/miliastra-wonderland-plugin/blob/main/docs/compatibility.md#运行要求) · [Installation checks](https://github.com/savormundane/miliastra-wonderland-plugin/blob/main/docs/installation.md#安装自检) · [Creator tutorials](https://github.com/savormundane/miliastra-wonderland-plugin/tree/main/samples/creator-demos)
