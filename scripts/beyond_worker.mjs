import {readFileSync,writeFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import {dirname,join} from 'node:path';
const job=JSON.parse(readFileSync(process.argv[2],'utf8'));
const {createStudio}=await import(pathToFileURL(job.entry).href);
const directory=dirname(process.argv[3]);
if(job.gil){
 const {importGia}=await import(new URL('./gia/codec.js',pathToFileURL(job.entry)));
 const imported=importGia(Buffer.from(job.gil.envelope,'base64'));
 if(imported.warnings.length!==1) throw Error('Unexpected conversion warnings: '+imported.warnings.join('; '));
 job.project=imported.project;
 job.project.canvasId=job.gil.canvas;
 job.project.meta.assetType='server-control-template';
 job.project.meta.sourceFormat='gil-subtree';
 const byGuid=new Map();
 function visit(node){if(node.guid)byGuid.set(node.guid,node);for(const child of node.children||[])visit(child)}
 visit(job.project.root);
 if(job.gil.guids.length!==byGuid.size || job.gil.guids.some(g=>!byGuid.has(g)))throw Error('Converted GUID inventory differs');
 for(const script of job.scripts){script.controlId=byGuid.get(script.control_guid).id;script.controlAsset='server-control-template';delete script.control_guid}
 writeFileSync(join(directory,'converted-project.json'),JSON.stringify(job.project,null,2));
}
const studio=createStudio(job.project);
try {
 for(const script of job.scripts) studio.patch({op:'addScript',...script});
 const result=studio.playRunCase(job.case);
 if(job.render){
  const {renderPaintPng}=await import(new URL('./host-png.js',pathToFileURL(job.entry)));
  const snap=studio.playGet({inspect:true,paint:true});
  for(const check of job.render_checks){
   const matches=snap.paint.filter(p=>p.name===check.name);
   if(matches.length!==1)throw Error('Render target missing or ambiguous: '+check.name);
   for(const [key,value]of Object.entries(check))if(key!=='name' && matches[0][key]!==value)throw Error('Render assertion failed: '+check.name+'.'+key);
  }
  const rendered=renderPaintPng(snap.paint,snap.canvasWidth,snap.canvasHeight,{background:'transparent'});
  writeFileSync(join(directory,'preview.png'),rendered.data);
  writeFileSync(join(directory,'render.json'),JSON.stringify({layer:'software_preview',checks:job.render_checks,status:job.render_checks.length?'passed':'not_checked',width:rendered.width,height:rendered.height,paint:snap.paint,tree:snap.tree},null,2));
 }
 writeFileSync(process.argv[3],JSON.stringify(result),{flag:'wx'});
} finally {studio.playStop();}
