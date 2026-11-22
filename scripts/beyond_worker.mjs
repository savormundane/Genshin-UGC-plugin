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
 const diagnostics=[];
 let result;
 try {
  result=studio.playRunCase(job.case);
 } catch(error) {
  result={passed:false,results:[]};
  diagnostics.push({code:'beyond_execution_failed',message:error.message});
 }
 const failedIndex=result.results.findIndex(row=>!row.ok);
 if(failedIndex>=0){
  const first=result.results[failedIndex];
  diagnostics.push({code:'beyond_assertion_failed',message:first.message||'Beyond case assertion failed',
   assertion_index:failedIndex+1,kind:first.kind,time:result.failedAt,frame:result.frame,
   expected:first.expected,actual:first.actual});
 }
 const assertions={status:failedIndex>=0?'failed':result.results.length?'passed':'not_checked',
  executed:result.results.length};
 let rendering='not_checked';
 let previewGenerated=false;
 if(job.render){
  try {
   const {renderPaintPng}=await import(new URL('./host-png.js',pathToFileURL(job.entry)));
   const snap=studio.playGet({inspect:true,paint:true});
   const rendered=renderPaintPng(snap.paint,snap.canvasWidth,snap.canvasHeight,{background:'transparent'});
   writeFileSync(join(directory,'preview.png'),rendered.data);
   previewGenerated=true;
   if(result.passed && job.render_checks.length){
    rendering='passed';
    for(const check of job.render_checks){
     const matches=snap.paint.filter(p=>p.name===check.name);
     if(matches.length!==1){
      diagnostics.push({code:'beyond_render_target',message:'Render target missing or ambiguous: '+check.name,
       target:check.name,expected:1,actual:matches.length});
      rendering='failed';
      break;
     }
     const mismatch=Object.entries(check).find(([key,value])=>key!=='name' && matches[0][key]!==value);
     if(mismatch){
      const [field,expected]=mismatch;
      diagnostics.push({code:'beyond_render_assertion_failed',
       message:'Render assertion failed: '+check.name+'.'+field,target:check.name,field,
       expected,actual:matches[0][field]??null,frame:snap.frame,time:snap.time});
      rendering='failed';
      break;
     }
    }
   }
   writeFileSync(join(directory,'render.json'),JSON.stringify({
    layer:'software_preview',checks:job.render_checks,status:rendering,
    width:rendered.width,height:rendered.height,paint:snap.paint,tree:snap.tree
   },null,2));
   result.logs=snap.logs||result.snapshot?.logs||[];
  } catch(error) {
   rendering='failed';
   diagnostics.push({code:'beyond_render_failed',message:error.message});
  }
 }
 result.passed=result.passed && diagnostics.length===0;
 result.diagnostics=diagnostics;
 result.checks={assertions,render_assertions:{status:rendering},preview:{generated:previewGenerated}};
 result.logs??=result.snapshot?.logs||[];
 writeFileSync(process.argv[3],JSON.stringify(result),{flag:'wx'});
} finally {studio.playStop();}
