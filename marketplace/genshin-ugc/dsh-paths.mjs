import {fileURLToPath} from 'node:url';

export const name = 'genshin-ugc-marketplace-paths';

export function apply(ctx) {
  ctx.provide('genshinUgcPaths', {
    skills: fileURLToPath(new URL('./skills', import.meta.url)),
    launcher: fileURLToPath(new URL('./launch.cjs', import.meta.url)),
  });
}
