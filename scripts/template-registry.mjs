export const CONTROL_KINDS = ['container', 'text', 'image', 'area'];
export function listAllTemplates() { throw Error('完整游戏模板注册表已停用。使用 python scripts/qianxing.py level create SPEC.json --out NEW.gil；控件类型：' + CONTROL_KINDS.join(', ')); }
if (process.argv[1]?.endsWith('template-registry.mjs')) { console.error('已改为结构化生成：python scripts/qianxing.py level create SPEC.json --out NEW.gil'); process.exitCode=2; }
