-- Call with the actual binding report, e.g. Diagnostics.run({name=templateGUID}).
local D={}
function D.run(templates)
 local report={templates={},roots={}}
 local ok,w,h=pcall(game.GetUICanvasSize)
 report.canvas=ok and {width=w,height=h} or {error=tostring(w)}
 print('[千星自检] canvas',w,h)
 for _,root in ipairs(game.GetClientUIRoots()) do
  local r={name=root.name,id=root.id,prefabIndex=root.prefabIndex,alive=root.alive,scripts={}}
  for _,s in ipairs(root:GetScripts()) do
   r.scripts[#r.scripts+1]={id=s.scriptMappingId,path=s.path,enabled=s.enabled,alive=s.alive}
   print('[千星自检] script',s.scriptMappingId,s.path,s.enabled,s.alive)
  end
  report.roots[#report.roots+1]=r
 end
 for name,index in pairs(templates or {}) do
  -- API cannot enumerate the whole editor template library. Only probe supplied indices.
  local result={name=name,index=index}
  local parent=game.GetClientUIRoots()[1]
  if parent then
   local valid,c=pcall(game.InstantiateClientUIControl,index,parent)
   result.instantiated=valid and c~=nil
   if result.instantiated then
    local clean,err=pcall(game.DestroyClientUIControl,c);result.cleaned=clean;result.cleanupError=not clean and tostring(err) or nil
   else result.error=tostring(c) end
  else result.error='没有运行时UI根控件' end
  report.templates[#report.templates+1]=result
  print('[千星自检] template',name,index,result.instantiated,result.error)
 end
 game.PrintClientUITree()
 return report
end
return D
