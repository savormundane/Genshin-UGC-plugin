// Machine-specific interpreter binding lives outside the immutable plugin version.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {spawn}=require('node:child_process');
const config=process.env.UGC_RUNTIME_CONFIG||path.join(process.env.LOCALAPPDATA||path.join(os.homedir(),'.local','share'),'Genshin-UGC','runtime.json');
if(!fs.existsSync(config)){console.error('Genshin-UGC runtime is not configured. Run '+path.join(__dirname,'configure_runtime.py')+' with an explicit Python interpreter and project/output roots; see docs/runtime-environment.md.');process.exit(2)}
const r=JSON.parse(fs.readFileSync(config,'utf8').replace(/^\uFEFF/,''));
if(r.schema!==1||!fs.existsSync(r.python)||!path.isAbsolute(r.project_root)||!path.isAbsolute(r.output_root)){console.error('Invalid Genshin-UGC runtime binding');process.exit(2)}
const env={...process.env,UGC_PROJECT_ROOT:r.project_root,UGC_OUTPUT_ROOT:r.output_root,PYTHONNOUSERSITE:'1',PYTHONDONTWRITEBYTECODE:'1'};
delete env.PYTHONPATH;delete env.PYTHONHOME;
const child=spawn(r.python,['-X','utf8','-B',path.join(__dirname,'qianxing.py'),'mcp','serve'],{stdio:'inherit',env,windowsHide:true});
child.on('error',e=>{console.error(e.message);process.exitCode=2});
child.on('exit',code=>{process.exitCode=code??2});
for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>child.kill(signal));
