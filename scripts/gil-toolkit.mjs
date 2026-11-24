import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';

export const sha256 = b => crypto.createHash('sha256').update(b).digest('hex');
function varint(b, start) {
  let v = 0n, i = start;
  for (let shift = 0n; shift < 70n; shift += 7n) {
    if (i >= b.length) throw Error('Truncated varint');
    const c = b[i++];
    if (shift === 63n && c > 1) throw Error('Varint exceeds uint64');
    v |= BigInt(c & 127) << shift;
    if (c < 128) return [v, i];
  }
  throw Error('Invalid varint');
}
function vi(v) {
  v = BigInt(v); const out = [];
  do { const c = Number(v & 127n); v >>= 7n; out.push(c | (v ? 128 : 0)); } while (v);
  return Buffer.from(out);
}
export function parse(b) {
  const fields = []; let i = 0;
  while (i < b.length) {
    const start = i; let tag; [tag, i] = varint(b, i);
    const n = Number(tag >> 3n), w = Number(tag & 7n);
    if (!n || n > 536870911) throw Error('Invalid field number');
    let value;
    if (w === 0) [value, i] = varint(b, i);
    else if (w === 2) {
      let len; [len, i] = varint(b, i);
      if (len > BigInt(b.length - i)) throw Error('Truncated payload');
      value = b.subarray(i, i + Number(len)); i += Number(len);
    } else if (w === 1 || w === 5) {
      const len = w === 1 ? 8 : 4;
      if (i + len > b.length) throw Error('Truncated fixed value');
      value = b.subarray(i, i + len); i += len;
    } else throw Error('Unsupported wire type: ' + w);
    fields.push({ n, w, value, raw: b.subarray(start, i) });
  }
  return fields;
}
export function encode(fields) {
  return Buffer.concat(fields.map(f => f.raw || Buffer.concat([
    vi(BigInt(f.n) * 8n + BigInt(f.w)),
    f.w === 0 ? vi(f.value) : f.w === 2
      ? Buffer.concat([vi(f.value.length), f.value]) : f.value
  ])));
}
function one(fields, n, w) {
  const found = fields.filter(f => f.n === n && f.w === w);
  if (found.length !== 1) throw Error(`Expected exactly one field ${n}/${w}, found ${found.length}`);
  return found[0];
}
function replace(fields, target, value) {
  return fields.map(f => f === target ? { n: f.n, w: f.w, value } : f);
}
export function container(b) {
  if (b.length < 24) throw Error('Container too short');
  const header = Array.from({ length: 5 }, (_, i) => b.readUInt32BE(i * 4));
  if (header[0] !== b.length - 4 || header[4] !== b.length - 24 || b.readUInt32BE(b.length - 4) !== 0x679)
    throw Error('Unsupported GIL framing');
  const fields = parse(b.subarray(20, -4));
  return { header, fields, trailer: b.subarray(-4) };
}
export function inspect(b) {
  const { header, fields } = container(b); const scripts = [];
  for (const group of fields.filter(f => f.n === 50 && f.w === 2)) {
    for (const entry of parse(group.value).filter(f => f.n === 1 && f.w === 2)) {
      const ef = parse(entry.value);
      const names = ef.filter(f => f.n === 3 && f.w === 2);
      const code = ef.filter(f => f.n === 5 && f.w === 2);
      if (names.length === 1 && code.length === 1)
        scripts.push({ name: names[0].value.toString('utf8'), bytes: code[0].value.length, sha256: sha256(code[0].value) });
    }
  }
  return { bytes: b.length, sha256: sha256(b), header, roundtripByteIdentical: encode(fields).equals(b.subarray(20, -4)),
    fields: fields.map(f => ({ field: f.n, wire: f.w, bytes: f.raw.length, sha256: sha256(f.raw) })), scripts,
    editorImportTested: false, hostRuntimeTested: false };
}
export function replaceLua(b, scriptName, code) {
  if (!Buffer.isBuffer(code) || !code.length) throw Error('Lua content must be a nonempty Buffer');
  const c = container(b);
  if (c.header[1] !== 1 || c.header[2] !== 806 || c.header[3] !== 2)
    throw Error('写入需要已校准的 GIL 容器头。实际=' + c.header.slice(1, 4).join(','));
  const group = one(c.fields, 50, 2); const entries = parse(group.value);
  const matches = entries.filter(e => e.n === 1 && e.w === 2 && parse(e.value).some(f => f.n === 3 && f.w === 2 && f.value.toString('utf8') === scriptName));
  if (matches.length !== 1) {
    const names = entries.filter(e => e.n === 1 && e.w === 2).flatMap(e => parse(e.value).filter(f => f.n === 3 && f.w === 2).map(f => f.value.toString('utf8')));
    throw Error('脚本映射缺失或不唯一；需要完整文件名（精确相等，含.lua）。请求=' + JSON.stringify(scriptName) + '，现有映射=' + JSON.stringify(names));
  }
  const entry = matches[0], ef = parse(entry.value), target = one(ef, 5, 2);
  one(ef, 3, 2);
  const newEntry = encode(replace(ef, target, code));
  const newGroup = encode(replace(entries, entry, newEntry));
  const payload = encode(replace(c.fields, group, newGroup));
  if (payload.length > 0xffffffff - 20) throw Error('Container too large');
  const head = Buffer.from(b.subarray(0, 20)); head.writeUInt32BE(payload.length + 20, 0); head.writeUInt32BE(payload.length, 16);
  const out = Buffer.concat([head, payload, c.trailer]);
  const result = container(out);
  if (c.fields.length !== result.fields.length || c.fields.some((f, i) => f !== group && !f.raw.equals(result.fields[i].raw)))
    throw Error('Unexpected change outside scripts');
  return out;
}
export async function writeNew(input, output, bytes) {
  const a = path.resolve(input), b = path.resolve(output);
  if (a.toLowerCase() === b.toLowerCase()) throw Error('Refusing to overwrite input');
  const original = await fs.realpath(a);
  const parent = await fs.realpath(path.dirname(b));
  if (original.toLowerCase() === path.join(parent, path.basename(b)).toLowerCase()) throw Error('Input and output alias');
  await fs.writeFile(b, bytes, { flag: 'wx' });
}
async function main(args) {
  const [cmd, input, name, lua, output] = args;
  if (cmd === 'inspect' && input) console.log(JSON.stringify(inspect(await fs.readFile(input)), null, 2));
  else if (cmd === 'replace-lua' && input && name && lua && output) {
    const b = replaceLua(await fs.readFile(input), name, await fs.readFile(lua));
    await writeNew(input, output, b); console.log(JSON.stringify(inspect(b), null, 2));
  } else throw Error('Usage: node gil-toolkit.mjs inspect INPUT | replace-lua INPUT SCRIPT_NAME LUA NEW_OUTPUT');
}
if (typeof process !== 'undefined' && process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href)
  main(process.argv.slice(2)).catch(e => { console.error(e.message); process.exitCode = 1; });
