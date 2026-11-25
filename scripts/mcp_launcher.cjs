const fs = require('node:fs');
const path = require('node:path');
const {createHash} = require('node:crypto');
const {spawn, spawnSync} = require('node:child_process');

const plugin = path.resolve(__dirname, '..');
const probe = path.join(__dirname, 'runtime_policy.py');
const cli = path.join(__dirname, 'qianxing.py');
const checking = process.argv[2] === '--check';
const retryCheck = '在插件目录运行 node .\\scripts\\mcp_launcher.cjs --check，按报告修正后重新打开客户端。';

function startupError(step, message, next, detail) {
  return new Error(`[${step}] ${message}\n下一步 ${next}` + (detail ? `\n详细原因 ${detail}` : ''));
}

function probeDetail(result) {
  return result.stderr?.trim() || result.error?.message || `退出码 ${result.status}`;
}

function probeUv(env) {
  return spawnSync('uv.exe', ['--version'], {
    cwd: plugin, env, encoding: 'utf8', timeout: 2500, windowsHide: true,
  });
}

function readBinding(filename) {
  const record = JSON.parse(fs.readFileSync(filename, 'utf8').replace(/^\uFEFF/, ''));
  if (record.schema !== 1 || typeof record.python !== 'string' || !path.isAbsolute(record.python)
      || !['project_root', 'output_root'].every(key => record[key] == null
        || (typeof record[key] === 'string' && path.isAbsolute(record[key])))) {
    throw new Error('运行绑定需使用 schema 1，Python 与已填写的工程和输出目录需为绝对路径。文件 ' + filename);
  }
  return record;
}

function installedPythons(root) {
  const interpreters = [];
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
          interpreters.push(record.python);
        }
      } catch {
        // Skip installation records that cannot provide a usable interpreter.
      }
    }
  }
  return interpreters;
}

function runtimeConfig(env) {
  const clientConfig = env.MILIASTRA_WONDERLAND_PLUGIN_DATA && path.isAbsolute(env.MILIASTRA_WONDERLAND_PLUGIN_DATA)
    ? path.join(env.MILIASTRA_WONDERLAND_PLUGIN_DATA, 'runtime.json') : null;
  const config = env.MILIASTRA_WONDERLAND_RUNTIME_CONFIG || (clientConfig && fs.existsSync(clientConfig) ? clientConfig : null);
  if (config && !path.isAbsolute(config)) throw new Error('MILIASTRA_WONDERLAND_RUNTIME_CONFIG 需使用绝对路径。');
  return config;
}

function start() {
  if (checking) console.log(`Miliastra Wonderland 安装自检\n插件目录 ${plugin}`);
  const startupFiles = [
    'plugin.json', 'pyproject.toml', 'uv.lock', 'scripts/runtime_policy.py', 'scripts/qianxing.py',
    'scripts/runtime-env-renames.json',
    'scripts/node_build.py', 'scripts/level_inventory.py', 'scripts/graph_validation.py', 'scripts/authoring_io.py',
    'scripts/miliastra/mcp/service.py', 'scripts/miliastra/mcp/bridge.py', 'scripts/miliastra/mcp/workspace.py', 'scripts/mcp_worker.py',
  ];
  const missing = startupFiles.filter(file => !fs.statSync(path.join(plugin, file), {throwIfNoEntry: false})?.isFile());
  if (missing.length) {
    throw startupError('install.files', '插件缺少启动所需文件。',
      '通过原安装入口重新安装插件，或完整解压原 ZIP 后再运行自检。', missing.join('\n'));
  }
  if (checking) console.log('插件启动文件齐全。');
  const node = `Node.js ${process.version} (${process.execPath})`;
  if (process.platform !== 'win32' || process.arch !== 'x64') {
    throw startupError('runtime.platform', '完整工具需要 Windows x64 和 x64 版 Node.js。',
      '在 Windows x64 上安装 x64 版 Node.js，再运行自检。', `${process.platform}/${process.arch}, ${node}`);
  }
  if (Number(process.versions.node.split('.')[0]) < 22) {
    throw startupError('runtime.node', '当前 Node.js 版本过低。',
      '安装 Node.js 22 或更高版本，再重新打开终端和客户端。DeepSeek Harness 需要 24.9+。',
      `所需版本为 Node.js 22 或更高版本。当前环境 ${node}`);
  }
  if (checking) console.log(`${node} 可用（Windows x64）。`);
  const env = {...process.env, PYTHONNOUSERSITE: '1', PYTHONDONTWRITEBYTECODE: '1'};
  delete env.PYTHONPATH;
  delete env.PYTHONHOME;
  const renames = require('./runtime-env-renames.json');
  for (const name of Object.keys(env)) {
    const current = renames[name.toUpperCase()];
    if (current) {
      console.error(`[runtime.env.deprecated] ${name} 已停用，请使用 ${current}。`);
      delete env[name];
    }
  }

  const uv = checking ? probeUv(env) : null;
  if (checking) console.log(uv.status === 0 ? `PATH 上的 uv 可用（${uv.stdout.trim()}）。`
    : 'PATH 上未找到可用的 uv。');

  const configuredRoot = env.MILIASTRA_WONDERLAND_INSTALL_ROOT;
  const root = configuredRoot || (env.LOCALAPPDATA && path.join(env.LOCALAPPDATA, 'Miliastra Wonderland'));
  const chosen = env.MILIASTRA_WONDERLAND_PYTHON;
  let explicit, workspaceConfig, installed;
  try {
    if (!root || !path.isAbsolute(root)) throw new Error('MILIASTRA_WONDERLAND_INSTALL_ROOT 需使用绝对路径。');
    workspaceConfig = runtimeConfig(env);
    explicit = workspaceConfig ? readBinding(workspaceConfig) : null;
    installed = chosen ? [] : installedPythons(root);
  } catch (error) {
    throw startupError('runtime.binding', '无法读取插件运行配置。',
      '检查安装根目录和 MILIASTRA_WONDERLAND_RUNTIME_CONFIG 指向的 runtime.json。修正路径或绑定后重试。', error.message);
  }
  if (workspaceConfig) env.MILIASTRA_WONDERLAND_RUNTIME_CONFIG = workspaceConfig;
  if (checking && workspaceConfig) console.log(`运行绑定 ${workspaceConfig}`);

  const pythonRecovery = '将 MILIASTRA_WONDERLAND_PYTHON 设为已配置好插件依赖的 Python 绝对路径，或清除它后让启动器查找环境。重新打开客户端后重试。';
  if (chosen && !path.isAbsolute(chosen)) {
    throw startupError('runtime.python', '指定的 Python 路径无效。', pythonRecovery, 'MILIASTRA_WONDERLAND_PYTHON 需使用绝对路径。');
  }
  const active = env.VIRTUAL_ENV && path.isAbsolute(env.VIRTUAL_ENV)
    ? path.join(env.VIRTUAL_ENV, 'Scripts', 'python.exe') : null;
  const candidates = chosen ? [chosen] : [explicit?.python, active, ...installed, 'python.exe'];
  const runArgs = ['-X', 'utf8', '-B', cli, 'mcp', 'serve'];
  let command;
  let args;
  const failures = [];
  for (const candidate of new Set(candidates.filter(Boolean))) {
    const result = spawnSync(candidate, ['-I', '-X', 'utf8', '-B', probe], {
      cwd: plugin, env, encoding: 'utf8', timeout: 5000, windowsHide: true,
    });
    if (result.status === 0) {
      try {
        command = JSON.parse(result.stdout);
      } catch (error) {
        failures.push(`${candidate}: ${error.message}`);
        continue;
      }
      args = runArgs;
      break;
    }
    failures.push(`${candidate}: ${probeDetail(result)}`);
  }
  if (chosen && !command) {
    throw startupError('runtime.python', '指定的 Python 环境不可用或缺少所需依赖。', pythonRecovery, failures.join('\n'));
  }
  let useUv = false;
  if (!command) {
    const check = uv || probeUv(env);
    if (check.status !== 0) {
      throw startupError('runtime.python', '未找到可用的 Python 运行环境，PATH 上也没有可用的 uv。',
        '安装 uv 并确认 uv --version 能运行，或通过 MILIASTRA_WONDERLAND_PYTHON 指定已配置依赖的 Python。重新打开客户端后重试。',
        [...failures, 'uv.exe: ' + probeDetail(check)].join('\n'));
    }
    const digest = createHash('sha256').update(
      fs.readFileSync(path.join(plugin, 'uv.lock'), 'utf8').replace(/\r\n/g, '\n')).digest('hex').slice(0, 16);
    env.UV_PROJECT_ENVIRONMENT = path.join(root, 'env', digest);
    command = 'uv.exe';
    args = ['run', '--project', plugin, '--locked', '--no-build', 'python', ...runArgs];
    useUv = true;
  }

  if (checking) {
    if (useUv) {
      console.log(`未找到已有的兼容 Python 环境。详细原因 ${failures.join('\n')}`);
      console.log('下次启动会由 uv 按 uv.lock 准备环境。首次缺少缓存时需要联网。');
    } else {
      console.log(`Python 环境通过版本、依赖和导入检查（${command}）。`);
    }
    console.log('下一步 重新打开客户端，在新对话中用插件查询服务端「创建实体」节点，确认工具已连通。');
    return;
  }

  const child = spawn(command, args, {cwd: plugin, env, stdio: 'inherit', windowsHide: true});
  const step = useUv ? 'runtime.uv' : 'runtime.mcp';
  const message = useUv ? 'uv 准备环境或启动 MCP 失败。' : 'MCP 进程启动或运行失败。';
  const next = useUv ? '查看上方 uv 日志。若下载失败，确认网络可访问依赖源后重试。' : retryCheck;
  child.on('error', error => fail(startupError(step, message, retryCheck, error.message)));
  child.on('exit', code => {
    if (code) fail(startupError(step, message, next, `退出码 ${code}`), code);
    else process.exitCode = code ?? 2;
  });
  for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
}

function fail(error, code = 2) {
  console.error('Miliastra Wonderland: ' + error.message);
  process.exitCode = code;
}

try {
  start();
} catch (error) {
  fail(error);
}
