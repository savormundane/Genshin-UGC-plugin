const fs = require('node:fs');
const path = require('node:path');
const {createHash} = require('node:crypto');
const {spawn, spawnSync} = require('node:child_process');

const plugin = path.resolve(__dirname, '..');
const probe = path.join(__dirname, 'runtime_policy.py');
const cli = path.join(__dirname, 'qianxing.py');

function readBinding(filename) {
  const record = JSON.parse(fs.readFileSync(filename, 'utf8').replace(/^\uFEFF/, ''));
  if (record.schema !== 1 || !['python', 'project_root', 'output_root'].every(
      key => typeof record[key] === 'string' && path.isAbsolute(record[key]))) {
    throw new Error('Invalid runtime binding: ' + filename);
  }
  return record;
}

function legacyBindings(root) {
  const bindings = [];
  for (const agent of ['agent-plugins', 'codex', 'claude-code', 'deepseek-harness']) {
    const parent = path.join(root, 'versions', agent);
    if (!fs.existsSync(parent)) continue;
    const versions = fs.readdirSync(parent).filter(name => /^\d+\.\d+\.\d+$/.test(name))
      .sort((a, b) => b.localeCompare(a, 'en', {numeric: true}));
    for (const version of versions) {
      const home = path.join(parent, version);
      const filename = path.join(home, 'runtime.json');
      const python = path.join(home, 'runtime', 'Scripts', 'python.exe');
      if (!fs.existsSync(filename) || !fs.existsSync(python)
          || fs.existsSync(path.join(home, 'installation-pending.json'))) continue;
      try {
        const record = readBinding(filename);
        if (fs.realpathSync.native(record.python) === fs.realpathSync.native(python)) {
          bindings.push({record, agent});
        }
      } catch {
        // An invalid legacy record is not a usable interpreter candidate.
      }
    }
  }
  return bindings;
}

function start() {
  if (process.platform !== 'win32' || process.arch !== 'x64') {
    throw new Error('The complete Miliastra Wonderland runtime requires Windows x64.');
  }
  if (Number(process.versions.node.split('.')[0]) < 22) throw new Error('Node.js 22+ required.');
  const env = {...process.env, PYTHONNOUSERSITE: '1', PYTHONDONTWRITEBYTECODE: '1'};
  delete env.PYTHONPATH;
  delete env.PYTHONHOME;

  const root = env.UGC_PUBLIC_INSTALL_ROOT
    || (env.LOCALAPPDATA && path.join(env.LOCALAPPDATA, 'Genshin-UGC-Public'));
  if (!root || !path.isAbsolute(root)) throw new Error('Set UGC_PUBLIC_INSTALL_ROOT to an absolute path.');
  const clientConfig = env.UGC_PLUGIN_DATA && path.isAbsolute(env.UGC_PLUGIN_DATA)
    ? path.join(env.UGC_PLUGIN_DATA, 'runtime.json') : null;
  const config = env.UGC_RUNTIME_CONFIG || (clientConfig && fs.existsSync(clientConfig) ? clientConfig : null);
  if (config && !path.isAbsolute(config)) throw new Error('UGC_RUNTIME_CONFIG must be an absolute path.');
  const explicit = config ? readBinding(config) : null;
  const legacy = legacyBindings(root);
  // The old agent-plugins preparation was explicitly shared across hosts.
  // Other registrations supply Python only, unless the user selects their config.
  const roots = explicit || legacy.find(({record, agent}) => agent === 'agent-plugins'
    && [record.project_root, record.output_root].every(dir => fs.statSync(dir, {throwIfNoEntry: false})?.isDirectory()))?.record;
  if (roots && !env.UGC_PROJECT_ROOT && !env.UGC_OUTPUT_ROOT) {
    env.UGC_PROJECT_ROOT = roots.project_root;
    env.UGC_OUTPUT_ROOT = roots.output_root;
  }

  const chosen = env.UGC_PYTHON;
  if (chosen && !path.isAbsolute(chosen)) throw new Error('UGC_PYTHON must be an absolute path.');
  const active = env.VIRTUAL_ENV && path.isAbsolute(env.VIRTUAL_ENV)
    ? path.join(env.VIRTUAL_ENV, 'Scripts', 'python.exe') : null;
  const candidates = chosen ? [chosen] : [explicit?.python, active, ...legacy.map(item => item.record.python), 'python.exe'];
  const runArgs = ['-X', 'utf8', '-B', cli, 'mcp', 'serve'];
  let command;
  let args;
  let detail;
  for (const candidate of new Set(candidates.filter(Boolean))) {
    const result = spawnSync(candidate, ['-I', '-B', probe], {
      cwd: plugin, env, encoding: 'utf8', timeout: 5000, windowsHide: true,
    });
    if (result.status === 0) {
      command = JSON.parse(result.stdout);
      args = runArgs;
      break;
    }
    detail = result.stderr?.trim() || detail;
  }
  if (chosen && !command) throw new Error(detail || 'Cannot start the selected Python: ' + chosen);

  if (!command) {
    const check = spawnSync('uv.exe', ['--version'], {cwd: plugin, env, timeout: 2500, windowsHide: true});
    if (check.status !== 0) throw new Error((detail ? detail + '. ' : '') +
      'No compatible Python environment found. Set UGC_PYTHON or make uv available on PATH.');
    const digest = createHash('sha256').update(
      fs.readFileSync(path.join(plugin, 'uv.lock'), 'utf8').replace(/\r\n/g, '\n')).digest('hex').slice(0, 16);
    env.UV_PROJECT_ENVIRONMENT = path.join(root, 'env', digest);
    command = 'uv.exe';
    args = ['run', '--project', plugin, '--locked', '--no-build', 'python', ...runArgs];
  }

  const child = spawn(command, args, {cwd: plugin, env, stdio: 'inherit', windowsHide: true});
  child.on('error', fail);
  child.on('exit', code => { process.exitCode = code ?? 2; });
  for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
}

function fail(error) {
  console.error('Miliastra Wonderland: ' + error.message);
  process.exitCode = 2;
}

try {
  start();
} catch (error) {
  fail(error);
}
