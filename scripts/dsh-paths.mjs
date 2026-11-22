import {fileURLToPath} from 'node:url';

export const name = 'genshin-ugc-paths';

export function apply(ctx) {
  ctx.provide('genshinUgcPaths', {
    skills: fileURLToPath(new URL('../skills', import.meta.url)),
    launcher: fileURLToPath(new URL('./mcp_launcher.cjs', import.meta.url)),
  });
}
