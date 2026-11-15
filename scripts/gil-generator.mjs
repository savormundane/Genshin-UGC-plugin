import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {container,inspect,replaceLua,writeNew} from './gil-toolkit.mjs';
// Explicit existing-file operation only; no shipped game registry or implicit seed.
export async function generateFromSeed(input,output,modifications={}) {
 if(modifications.rename || modifications.customFields) throw Error('不再使用模糊改名或未验证字段修改；新建使用qianxing.py level create的明确配置');
 let data=await fs.readFile(input);
 for(const [name,code] of Object.entries(modifications.replaceScripts||{})) data=replaceLua(data,name,Buffer.from(code,'utf8'));
 await writeNew(input,output,data);
 return {inputPath:input,outputPath:output,...inspect(data),operation:'explicit_existing_archive_copy'};
}
export async function listScripts(input) {return inspect(await fs.readFile(input)).scripts;}
export async function inspectStructure(input) {const bytes=await fs.readFile(input),c=container(bytes);return {header:c.header,topLevelFields:c.fields.map(f=>({field:f.n,wire:f.w,bytes:f.raw.length})),fieldCount:c.fields.length};}
async function main(args){
 const [op,input,output]=args;
 if(op==='clone-existing'&&input&&output) return generateFromSeed(input,output);
 if(op==='list-scripts'&&input) return listScripts(input);
 if(op==='inspect-structure'&&input) return inspectStructure(input);
 throw Error('新建：python scripts/qianxing.py level create SPEC.json --out NEW.gil。已有文件：clone-existing INPUT OUTPUT | list-scripts INPUT | inspect-structure INPUT。不再提供--name。');
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href) main(process.argv.slice(2)).then(v=>console.log(JSON.stringify(v,null,2))).catch(e=>{console.error(e.message);process.exitCode=2;});
