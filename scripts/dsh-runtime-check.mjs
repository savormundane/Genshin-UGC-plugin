import {execFile} from 'node:child_process';
import {promisify} from 'node:util';

const run = promisify(execFile);

export const name = 'miliastra-wonderland-runtime-check';

export function apply(ctx) {
  ctx.effect(() => ctx.commands.register({
    name: 'miliastra-check',
    description: '检查千星奇域插件的本地运行环境',
    recordInput: false,
    async handler({rawInput, signal}) {
      if (rawInput.trim()) return {kind: 'error', text: '请直接运行 /miliastra-check。'};
      try {
        const {stdout, stderr} = await run('node', [ctx.miliastraWonderlandPaths.launcher, '--check'], {
          encoding: 'utf8',
          signal,
          timeout: 45000,
          windowsHide: true,
        });
        return {kind: 'success', text: [stdout.trim(), stderr.trim()].filter(Boolean).join('\n')};
      } catch (error) {
        if (signal.aborted) return {kind: 'error', text: '已取消安装自检。'};
        const report = [error.stdout?.trim(), error.stderr?.trim()].filter(Boolean).join('\n');
        const next = error.killed ? '安装自检超时。请按安装指南在终端运行自检。'
          : '安装自检失败。请检查 Node.js 和 Python 运行环境。';
        return {kind: 'error', text: [next, report || String(error.code ?? error.message)].join('\n')};
      }
    },
  }));
}
