const fs = require('fs');
const parser = require('../vendor/luaparse/luaparse.js');
const source = fs.readFileSync(0);
const tree = parser.parse(source.toString('latin1'), {
  luaVersion: '5.3', encodingMode: 'pseudo-latin1',
  scope: true, locations: true, ranges: true, comments: false
});
// Grouping suppresses Lua's multiple returns. Recover it from tokens because
// luaparse omits grouping nodes; comments and literal contents are not tokens.
parser.parse(source.toString('latin1'), {wait: true, locations: true, ranges: true});
const tokens = []; let token;
while ((token = parser.lex()).type !== 1) tokens.push(token);
const starts = new Map(tokens.map((t, i) => [t.range[0], i]));
const ends = new Map(tokens.map((t, i) => [t.range[1], i]));
const callParens = new Set(); const nodes = [];
function visit(node) {
  if (!node || typeof node !== 'object') return;
  if (Array.isArray(node)) { node.forEach(visit); return; }
  if (node.type) {
    nodes.push(node);
    if (node.type === 'CallExpression') {
      const next = ends.get(node.base.range[1]) + 1;
      if (tokens[next]?.value === '(') callParens.add(next);
    }
  }
  for (const [key, value] of Object.entries(node))
    if (!['loc', 'range', 'globals'].includes(key)) visit(value);
}
visit(tree);
for (const node of nodes) {
  const before = starts.get(node.range[0]) - 1, after = ends.get(node.range[1]) + 1;
  if (tokens[before]?.value === '(' && tokens[after]?.value === ')' && !callParens.has(before))
    node.parenthesized = true;
}
process.stdout.write(JSON.stringify(tree, function(key, value) {
  if (key === 'value' && this.type === 'StringLiteral') {
    return {bytes: Buffer.from(value, 'latin1').toString('base64')};
  }
  return value;
}));
