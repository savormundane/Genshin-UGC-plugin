import {fileURLToPath} from 'node:url';

export const name = 'miliastra-wonderland-paths';

export function apply(ctx) {
  ctx.provide('miliastraWonderlandPaths', {
    skills: fileURLToPath(new URL('../skills', import.meta.url)),
    launcher: fileURLToPath(new URL('./mcp_launcher.cjs', import.meta.url)),
  });
}
