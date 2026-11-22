const fs = require('node:fs');
const path = require('node:path');
const {spawn} = require('node:child_process');
const {version} = require('./plugin.json');
const realpath = fs.realpathSync.native;

function readJson(filename) {
  return JSON.parse(fs.readFileSync(filename, 'utf8').replace(/^\uFEFF/, ''));
}

function start() {
  if (process.platform !== 'win32' || process.arch !== 'x64') {
    throw new Error('The complete Genshin-UGC runtime requires Windows x64.');
  }
  const root = process.env.UGC_PUBLIC_INSTALL_ROOT
    || (process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA, 'Genshin-UGC-Public'));
  if (!root || !path.isAbsolute(root)) {
    throw new Error('Set UGC_PUBLIC_INSTALL_ROOT to the absolute installation root.');
  }

  const home = path.join(root, 'versions', 'agent-plugins', version);
  const bundle = path.join(home, 'Genshin-UGC');
  const config = path.join(home, 'runtime.json');
  const prepared = readJson(path.join(home, 'preparation.json'));
  if (prepared.agent !== 'agent-plugins' || prepared.prepared !== version
      || prepared.runtime_smoke !== 'passed'
      || !path.isAbsolute(prepared.plugin_directory || '') || !path.isAbsolute(prepared.config || '')
      || realpath(prepared.plugin_directory) !== realpath(bundle)
      || realpath(prepared.config) !== realpath(config)) {
    throw new Error('The preparation record does not match this plugin and installation root.');
  }
  const manifest = readJson(path.join(bundle, 'plugin.json'));
  if (manifest.name !== 'genshin-ugc-public' || manifest.version !== version) {
    throw new Error(`Expected the public Genshin-UGC ${version} runtime.`);
  }
  const binding = readJson(config);
  const python = path.join(home, 'runtime', 'Scripts', 'python.exe');
  if (binding.schema !== 1 || !path.isAbsolute(binding.python || '')
      || realpath(binding.python) !== realpath(python)) {
    throw new Error('The runtime configuration does not point to the prepared Python environment.');
  }

  const launcher = path.join(bundle, 'scripts', 'mcp_launcher.cjs');
  if (!fs.statSync(launcher).isFile()) throw new Error('The runtime MCP launcher is missing.');
  const child = spawn(process.execPath, [launcher], {
    cwd: bundle,
    env: {...process.env, UGC_RUNTIME_CONFIG: config},
    stdio: 'inherit',
    windowsHide: true,
  });
  child.on('error', fail);
  child.on('exit', code => { process.exitCode = code ?? 2; });
  for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
}

function fail(error) {
  console.error(`Genshin-UGC marketplace: ${error.message}`);
  console.error(`Prepare the ${version} Windows runtime with install.ps1 -Agent agent-plugins -Version ${version}.`);
  console.error(`https://github.com/savormundane/Genshin-UGC-plugin/blob/main/docs/installation.md#marketplace`);
  process.exitCode = 2;
}

try {
  start();
} catch (error) {
  fail(error);
}
