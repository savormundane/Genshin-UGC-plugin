"""Exercise the packaged Cordis bundle in an isolated DSH Web Host without model calls."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time


PROBE = """
import assert from 'node:assert/strict';
import {rename, writeFile} from 'node:fs/promises';
import {setTimeout} from 'node:timers/promises';

export const name = 'miliastra-smoke';
export const inject = ['commands', 'tools', 'skills', 'sessionController', 'pluginManager'];

const bundleName = 'dsh-miliastra-wonderland';
const toolPrefix = 'mcp__miliastra_wonderland__';
const command = '/miliastra-check';

async function check(ctx) {
  const {sessionId} = await ctx.sessionController.create({cwd: process.cwd()});
  const {agent, error} = await ctx.sessionController.resolveAgent(sessionId);
  assert.ok(agent, error?.message || 'Could not create a DSH session');
  const signal = AbortSignal.timeout(90000);

  const runCommand = async (input) =>
    (await ctx.commands.execute(agent, input, [], signal))?.result;

  assert.ok(ctx.commands.list(agent).some(({name}) => name === command.slice(1)));
  const invalid = await runCommand(command + ' unexpected');
  assert.equal(invalid?.kind, 'error');
  assert.match(invalid.text, /请直接运行/);
  const check = await runCommand(command);
  if (process.env.MILIASTRA_DSH_SMOKE_BROKEN_PYTHON === '1') {
    assert.equal(check?.kind, 'error');
    assert.match(check.text, /runtime[.]python/);
    assert.equal(ctx.tools.get(toolPrefix + 'nodes_lookup'), undefined);
    return {command: 'reports-startup-failure'};
  }

  assert.equal(check?.kind, 'success', check?.text);
  assert.match(check.text, /Python 环境通过版本、依赖和导入检查/);
  const bundle = (await ctx.pluginManager.listBundles()).find(({name}) => name === bundleName);
  assert.ok(bundle?.installed && bundle.enabled && !bundle.error, 'DSH bundle did not activate');
  assert.equal(bundle.version, process.env.MILIASTRA_DSH_SMOKE_VERSION);
  assert.ok(bundle.rows.some(({rowId, entryId}) => rowId === 'miliastra-wonderland-runtime-check' && entryId));

  const details = {};
  for (const [language, suffix] of [['zh-CN', 'zh'], ['en', 'en']]) {
    const detail = await ctx.pluginManager.readBundleDetail(bundleName, language);
    assert.equal(detail.origin, 'locale');
    assert.equal(detail.path, 'docs/dsh/overview.' + suffix + '.md');
    assert.ok(detail.markdown.includes(command));
    details[language] = detail.path;
  }

  const skills = (await ctx.skills.list()).map(({name}) => name)
    .filter(name => name.startsWith('miliastra-')).sort();
  assert.deepEqual(skills, ['miliastra-assets', 'miliastra-editor', 'miliastra-gil', 'miliastra-graph-code']);

  const nodeLookup = toolPrefix + 'nodes_lookup';
  while (!ctx.tools.get(nodeLookup) && !signal.aborted) await setTimeout(100, undefined, {signal});
  const calls = [
    {type: 'tool-call', id: 'miliastra-smoke-capabilities', name: toolPrefix + 'capabilities', arguments: '{}'},
    {type: 'tool-call', id: 'miliastra-smoke-node', name: nodeLookup,
      arguments: JSON.stringify({query: '创建实体', scope: 'server'})},
  ];
  const {results} = await ctx.tools.execute({calls, signal});
  const [capabilities, lookup] = results.map(({result}) => {
    assert.equal(result.isError, false, JSON.stringify(result.error));
    return result.value.structuredContent.result;
  });
  assert.equal(capabilities.version, bundle.version);
  assert.ok(lookup.nodes.some(node => node.name === '创建实体' && node.scope === 'server'
    && node.inputs.some(([name]) => name === '目标GUID') && node.outputs.some(([name]) => name === '流程出')
    && node.port_evidence?.source_version === '7.1'));
  return {version: bundle.version, command: 'success', skills, details, mcp: 'server-node-lookup'};
}

export function apply(ctx) {
  void check(ctx).then(
    result => ({status: 'passed', ...result}),
    error => ({status: 'failed', error: String(error.stack ?? error)}),
  ).then(async result => {
    const report = process.env.MILIASTRA_DSH_SMOKE_REPORT;
    await writeFile(report + '.tmp', JSON.stringify(result));
    await rename(report + '.tmp', report);
  });
}
"""


def run_host(cli, stage, environment, *, broken_python=False):
    label = 'broken-runtime' if broken_python else 'working-runtime'
    report_path = stage / f'{label}.json'
    log_path = stage / f'{label}.log'
    host_env = {**environment, 'MILIASTRA_DSH_SMOKE_REPORT': str(report_path)}
    if broken_python:
        host_env['MILIASTRA_WONDERLAND_PYTHON'] = str(stage / 'missing-python.exe')
        host_env['MILIASTRA_DSH_SMOKE_BROKEN_PYTHON'] = '1'

    with log_path.open('wb') as log:
        host = subprocess.Popen(
            [*cli, '--profile', 'web', '--patch', str(stage / 'probe.yml'),
             '--host', '127.0.0.1', '--port', '0', '--no-open'],
            cwd=stage, env=host_env, stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 120
            while not report_path.exists() and host.poll() is None and time.monotonic() < deadline:
                time.sleep(0.25)
            if report_path.is_file():
                result = json.loads(report_path.read_text('utf-8'))
                if result['status'] == 'passed':
                    return result
                print(result['error'], file=sys.stderr)
            log_text = log_path.read_text('utf-8', errors='replace')
            print(re.sub(r'(token=)[^&\s]+', r'\1<redacted>', log_text)[-6000:], file=sys.stderr)
            raise SystemExit(f'DSH Web Host smoke failed ({label})')
        finally:
            if host.poll() is None:
                subprocess.run(
                    ['taskkill.exe', '/PID', str(host.pid), '/T', '/F'],
                    capture_output=True, timeout=20,
                )
                if host.poll() is None:
                    host.kill()
            host.wait(timeout=20)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--dsh', type=Path, required=True, help='Installed DSH lib/bin.js entry point')
    parser.add_argument('--node', default='node', help='Node.js executable for this DSH version')
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('The complete Miliastra runtime requires Windows x64')
    node = shutil.which(args.node)
    if not node or not shutil.which('pnpm'):
        parser.error('Node.js and pnpm must be available')
    dsh, archive = args.dsh.resolve(strict=True), args.archive.resolve(strict=True)
    with tarfile.open(archive, 'r:gz') as package:
        with package.extractfile('package/package.json') as stream:
            manifest = json.load(stream)
    if manifest['name'] != 'dsh-miliastra-wonderland':
        parser.error('Expected the dsh-miliastra-wonderland npm archive')

    with tempfile.TemporaryDirectory(prefix='mw-dsh-') as temp:
        stage = Path(temp).resolve()
        home = stage / 'home'
        store = stage / 'store'
        npmrc = stage / 'npmrc'
        npmrc.write_text('', encoding='utf-8')
        environment = {
            key: value for key, value in os.environ.items()
            if not key.upper().startswith(
                ('DSH_', 'MILIASTRA_', 'DEEPSEEK_', 'OPENAI_', 'ANTHROPIC_', 'NPM_CONFIG_')
            )
            and key.upper() not in {'NODE_AUTH_TOKEN', 'NPM_TOKEN', 'NODE_OPTIONS'}
        }
        environment.update({
            'PATH': str(Path(node).parent) + os.pathsep + environment['PATH'],
            'DSH_HOME': str(home),
            'NPM_CONFIG_USERCONFIG': str(npmrc),
            'MILIASTRA_WONDERLAND_INSTALL_ROOT': str(stage / 'runtime'),
            'MILIASTRA_WONDERLAND_PYTHON': sys.executable,
            'MILIASTRA_DSH_SMOKE_VERSION': manifest['version'],
        })
        (stage / 'probe.mjs').write_text(PROBE, encoding='utf-8')
        (stage / 'probe.yml').write_text(
            '- insert:\n    - id: miliastra-smoke\n      name: ./probe.mjs\n', encoding='utf-8',
        )
        cli = [node, str(dsh)]
        subprocess.run(
            [*cli, 'plugin', '--profile', 'web', 'add', str(archive), '--store-dir', str(store)],
            cwd=stage, env=environment, check=True, timeout=120,
        )
        version = subprocess.check_output(
            [*cli, '--version'], cwd=stage, env=environment, encoding='utf-8', timeout=20,
        ).strip()
        results = {
            'dsh': version,
            'working_runtime': run_host(cli, stage, environment),
            'broken_runtime': run_host(cli, stage, environment, broken_python=True),
        }
        print(json.dumps(results, ensure_ascii=False))


if __name__ == '__main__':
    main()
