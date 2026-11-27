const fs = require('node:fs');
const path = require('node:path');
const {createHash} = require('node:crypto');
const {spawn, spawnSync} = require('node:child_process');

const plugin = path.resolve(__dirname, '..');
const probe = path.join(__dirname, 'runtime_policy.py');
const pythonProbeFlags = ['-I', '-X', 'utf8', '-B'];
const cli = path.join(__dirname, 'qianxing.py');
const checking = process.argv[2] === '--check';
const settingUp = process.argv[2] === '--setup';
const retryCheck = '在插件目录运行 node .\\scripts\\mcp_launcher.cjs --check，按报告修正后重新打开客户端。';
const prepareRuntime = '在插件目录运行 node .\\scripts\\mcp_launcher.cjs --setup，再重新打开客户端。';
const mirrorRecovery = '若依赖源连接缓慢或镜像与锁文件冲突，按 docs/runtime-environment.md 用镜像预装哈希锁定的依赖并绑定 Python。';

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

function pathExecutables(name) {
  const found = [];
  for (const entry of (process.env.PATH || '').split(path.delimiter)) {
    const directory = entry.trim().replace(/^"(.*)"$/, '$1');
    if (!path.isAbsolute(directory)) continue;
    const executable = path.join(directory, name);
    // WindowsApps can contain a Store stub for python.exe. Use py discovery there.
    if (name === 'python.exe' && /[\\/]Microsoft[\\/]WindowsApps[\\/]/i.test(executable)) continue;
    if (fs.existsSync(executable)) found.push(executable);
  }
  return found;
}

function probePython(executable, args, env, failures, {label = executable, timeout = 5000} = {}) {
  const result = spawnSync(executable, args, {
    cwd: plugin, env, encoding: 'utf8', timeout, windowsHide: true,
  });
  if (result.status !== 0) {
    const detail = result.error?.code === 'ETIMEDOUT'
      ? `Python 环境探测在 ${timeout / 1000} 秒内未完成（ETIMEDOUT）。`
      : probeDetail(result);
    failures.push(label + ' · ' + detail);
    return null;
  }
  try {
    const resolved = JSON.parse(result.stdout);
    if (typeof resolved !== 'string' || !path.isAbsolute(resolved) || !fs.existsSync(resolved)) {
      throw new Error('探测未返回存在的 Python 可执行文件绝对路径。');
    }
    return resolved;
  } catch (error) {
    failures.push(label + ' · ' + error.message);
    return null;
  }
}

function findLauncherPython(env, checkPython, failures) {
  const launchers = new Set(pathExecutables('py.exe'));
  if (!launchers.size) {
    failures.push('PATH 上未找到 py.exe。');
    return null;
  }
  const project = fs.readFileSync(path.join(plugin, 'pyproject.toml'), 'utf8');
  const range = /^requires-python[ \t]*=[ \t]*">=3\.(\d+),<3\.(\d+)"[ \t]*\r?$/m.exec(project);
  if (!range || Number(range[1]) >= Number(range[2])) {
    throw startupError('install.files', '无法识别 pyproject.toml 中的 Python 版本范围。', retryCheck);
  }
  const launcherEnv = {...env};
  for (const name of Object.keys(launcherEnv)) {
    if (['PYLAUNCHER_ALLOW_INSTALL', 'PYLAUNCHER_ALWAYS_INSTALL', 'PYTHON_MANAGER_AUTOMATIC_INSTALL']
      .includes(name.toUpperCase())) delete launcherEnv[name];
  }
  launcherEnv.PYTHON_MANAGER_AUTOMATIC_INSTALL = 'false';
  const min = Number(range[1]);
  const max = Number(range[2]);
  for (const launcher of launchers) {
    for (let minor = max - 1; minor >= min; minor--) {
      const selector = '-3.' + minor;
      const candidate = probePython(launcher, [selector, ...pythonProbeFlags, '-c',
        'import json, sys; print(json.dumps(sys.executable))'], launcherEnv, failures, {label: launcher + ' ' + selector});
      const command = candidate && checkPython(candidate);
      if (command) return command;
    }
  }
  return null;
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
  let uvEnvironment, uvPython, uvReady;
  if (!chosen) {
    const digest = createHash('sha256').update(
      fs.readFileSync(path.join(plugin, 'uv.lock'), 'utf8').replace(/\r\n/g, '\n')).digest('hex').slice(0, 16);
    uvEnvironment = path.join(root, 'env', digest);
    uvPython = path.join(uvEnvironment, 'Scripts', 'python.exe');
    uvReady = path.join(uvEnvironment, '.miliastra-ready');
  }
  const prepared = uvReady && fs.existsSync(uvReady) && fs.existsSync(uvPython) ? uvPython : null;
  const pathPythons = chosen ? [] : pathExecutables('python.exe');
  const configuredPython = chosen || explicit?.python;
  const candidates = chosen ? [chosen] : [explicit?.python, active, ...installed, prepared, ...pathPythons];
  const failures = [];
  const checked = new Set();
  const checkPython = candidate => {
    const key = path.normalize(candidate).toLowerCase();
    if (checked.has(key)) return null;
    checked.add(key);
    return probePython(candidate, [...pythonProbeFlags, probe], env, failures,
      candidate === configuredPython ? {timeout: 15000} : undefined);
  };
  let command;
  for (const candidate of candidates.filter(Boolean)) {
    command = checkPython(candidate);
    if (command) break;
  }
  if (chosen && !command) {
    throw startupError('runtime.python', '指定的 Python 环境未通过启动检查。', pythonRecovery, failures.join('\n'));
  }
  if (!command) {
    if (!pathPythons.length) failures.push('PATH 上未找到可探测的 python.exe。');
    command = findLauncherPython(env, checkPython, failures);
  }
  const runArgs = settingUp ? [...pythonProbeFlags, probe] : ['-X', 'utf8', '-B', cli, 'mcp', 'serve'];
  let args = runArgs;
  let useUv = false;
  if (!command) {
    const check = uv || probeUv(env);
    if (check.status !== 0) {
      throw startupError('runtime.python', '未找到可用的 Python 运行环境，PATH 上也没有可用的 uv。',
        '安装 uv 并确认 uv --version 能运行，或通过 MILIASTRA_WONDERLAND_PYTHON 指定已配置依赖的 Python。重新打开客户端后重试。',
        [...failures, 'uv.exe: ' + probeDetail(check)].join('\n'));
    }
    env.UV_PROJECT_ENVIRONMENT = uvEnvironment;
    command = 'uv.exe';
    args = ['run', '--project', plugin, '--locked', '--no-build', 'python', ...runArgs];
    useUv = true;
  }

  if (checking) {
    if (useUv) {
      console.log(`未找到已有的兼容 Python 环境。详细原因 ${failures.join('\n')}`);
      console.log('下次启动会由 uv 按 uv.lock 准备环境。首次缺少缓存时需要联网。');
      console.log('可提前准备。' + prepareRuntime);
    } else {
      console.log(`Python 环境通过版本、依赖和导入检查（${command}）。`);
    }
    console.log('下一步 重新打开客户端，在新对话中用插件查询服务端「创建实体」节点，确认工具已连通。');
    return;
  }
  if (settingUp && !useUv) {
    console.log(`Python 环境已就绪（${command}）。`);
    return;
  }

  const child = spawn(command, args, {
    cwd: plugin, env, stdio: settingUp ? ['ignore', 'ignore', 'inherit'] : 'inherit', windowsHide: true,
  });
  const step = useUv ? 'runtime.uv' : 'runtime.mcp';
  const message = settingUp ? 'uv 准备 Python 环境失败。'
    : useUv ? 'uv 准备环境或启动 MCP 失败。' : 'MCP 进程启动或运行失败。';
  const next = useUv ? (settingUp ? mirrorRecovery : prepareRuntime + mirrorRecovery) : retryCheck;
  child.on('error', error => fail(startupError(step, message, retryCheck, error.message)));
  child.on('exit', code => {
    if (code) fail(startupError(step, message, next, `退出码 ${code}`), code);
    else if (settingUp && code === 0) {
      try {
        if (!fs.statSync(uvPython, {throwIfNoEntry: false})?.isFile()) {
          throw new Error('未找到 uv 创建的 Python 可执行文件。');
        }
        fs.writeFileSync(uvReady, '');
        console.log(`Python 环境已就绪（${uvPython}）。`);
      } catch (error) {
        fail(startupError(step, message, retryCheck, error.message));
      }
    } else process.exitCode = code ?? 2;
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
