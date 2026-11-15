"""Versioned storage graph guards. Native logic is compiled, never simulated by a stub."""
from authoring_io import PLUGIN


def graph_methods(s,wire):
    annotations={'integer':'整数','boolean':'布尔值','integer_list':'整数列表'}
    fs=s['fields'];signals=[];methods=[];limit=9223372036854775807
    defaults={f['name']:('qx_empty_'+f['name']if f['type']=='integer_list'and not f['default']else repr(f['default']))for f in wire}
    placeholders=', '.join(f['name']+'='+('[0,0]'if f['type']=='integer_list'else repr(f['default']))for f in wire)
    for slot in range(1,s['slots']+1):
        variable=s['name']+'_slot_'+str(slot)
        for action in ('read','open','write'):
            name=s['name']+'_v3_'+action+'_'+str(slot);reply=name+'_reply'
            params=[('request','整数')]
            if action!='read':params += [('session','整数'),('revision','整数')]
            if action=='write':params += [(f['name'],annotations[f['type']])for f in fs]
            reply_params=[('request','整数'),('ok','布尔值'),('session','整数'),('revision','整数')]+[(f['name'],annotations[f['type']])for f in fs]
            for signal,parameters in ((name,params),(reply,reply_params)):
                signals.append((signal,[{'name':n,'parameter_type':t}for n,t in parameters]))
            signature=', '.join(n+': '+repr(t)for n,t in [('事件源实体','实体'),('事件源GUID','GUID'),('信号来源实体','实体'),*params])
            lines=['    def on_'+name+'(self, '+signature+'):']
            for f in fs:
                if f['type']=='integer_list'and not f['default']:
                    lines+=['        qx_seed_'+f['name']+': "整数列表" = 拼装列表(self.game, 0)',
                            '        qx_empty_ref_'+f['name']+', qx_empty_'+f['name']+' = 获取局部变量(self.game, 初始值=qx_seed_'+f['name']+')',
                            '        清除列表(self.game, 列表=qx_empty_'+f['name']+')']
            def respond(indent,ok,values):
                return [indent+'发送信号(self.game, 信号名='+repr(reply)+', request=request, ok='+ok+', session='+values['qx_session']+', revision='+values['qx_revision']+', '+', '.join(f['name']+'='+values[f['name']]for f in fs)+')']
            def split(indent,record,tag):
                values={f['name']:f['name']+'字段_'+tag for f in wire}
                rows=[indent+values[f['name']]+': '+repr(annotations[f['type']])+' = '+repr(f['default'])for f in wire if f['type']!='integer_list']+[indent+', '.join(values[f['name']]for f in wire)+' = 拆分结构体(self.game, 结构体='+record+', 结构体名='+repr(s['name'])+', '+placeholders+')']
                # Annotate after unpacking: the backend otherwise infers a
                # scalar split output from downstream generic list consumers.
                for f in wire:
                    if f['type']=='integer_list':
                        alias='qx_list_'+tag+'_'+f['name']
                        rows.append(indent+alias+': "整数列表" = '+values[f['name']]);values[f['name']]=alias
                return rows,values
            def commit(indent,values):
                rows=[indent+'qx_updated: "结构体" = 拼装结构体(self.game, 结构体名='+repr(s['name'])+', '+', '.join(f['name']+'='+values[f['name']]for f in wire)+')',
                      indent+'qx_new_records: "结构体列表" = 拼装列表(self.game, qx_updated)',
                      indent+'设置自定义变量(self.game, 目标实体=信号来源实体, 变量名='+repr(variable)+', 变量值=qx_new_records, 是否触发事件=False)',
                      indent+'qx_back: "结构体列表" = 获取自定义变量(self.game, 目标实体=信号来源实体, 变量名='+repr(variable)+')',
                      indent+'if 获取列表长度(self.game, 列表=qx_back) == 1:',
                      indent+'    qx_back_record: "结构体" = 获取列表对应值(self.game, 列表=qx_back, 序号=0)']
                parts,back=split(indent+'    ','qx_back_record','saved');rows+=parts
                expected={'qx_protocol':'3','qx_record_version':str(s.get('record_version',1)),'qx_session':'session','qx_request':'0'if action=='open'else'request'}
                check=' and '.join(back[key]+' == '+value for key,value in expected.items())
                check+=' and '+back['qx_revision']+' == revision + 1'
                rows+=respond(indent+'    ',check,back)+[indent+'else:']+respond(indent+'    ','False',defaults)
                return rows
            def process(indent,state,empty=False):
                if action=='read':return respond(indent,'True',state)
                rows=[]
                if action=='open':
                    rows += [indent+'if session == '+state['qx_session']+' + 1 and revision == '+state['qx_revision']+' and session > 0 and session < '+str(limit)+' and revision < '+str(limit)+':']
                    updated={**state,'qx_session':'session','qx_revision':'revision + 1','qx_request':'0'}
                    rows+=commit(indent+'    ',updated)
                    rows += [indent+'elif session == '+state['qx_session']+' and '+state['qx_revision']+' == revision + 1 and '+state['qx_request']+' == 0 and session > 0:']
                    rows+=respond(indent+'    ','True',state)+[indent+'else:']+respond(indent+'    ','False',state)
                    return rows
                if empty:return respond(indent,'False',state)
                rows += [indent+'if session == '+state['qx_session']+' and session > 0 and request > '+state['qx_request']+' and revision == '+state['qx_revision']+' and revision < '+str(limit)+':']
                updated={**state,**{f['name']:f['name']for f in fs},'qx_session':'session','qx_revision':'revision + 1','qx_request':'request'}
                rows+=commit(indent+'    ',updated)
                rows += [indent+'elif session == '+state['qx_session']+' and session > 0 and request == '+state['qx_request']+' and '+state['qx_revision']+' == revision + 1:']
                rows += [indent+'    qx_same_ref, qx_same = 获取局部变量(self.game, 初始值=True)']
                for f in fs:
                    a=f['name'];b=state[a]
                    if f['type']=='integer_list':
                        rows += [indent+'    qx_length_'+a+': "整数" = 获取列表长度(self.game, 列表='+a+')',
                                 indent+'    if qx_length_'+a+' == 获取列表长度(self.game, 列表='+b+'):',
                                 # The bundled DSL maps range bounds directly to
                                 # native inclusive Finite_Loop bounds.
                                 indent+'        qx_last_'+a+': "整数" = qx_length_'+a+' - 1',
                                 indent+'        for qx_index_'+a+' in range(0, qx_last_'+a+'):',
                                 indent+'            qx_left_'+a+': "整数" = 获取列表对应值(self.game, 列表='+a+', 序号=qx_index_'+a+')',
                                 indent+'            qx_right_'+a+': "整数" = 获取列表对应值(self.game, 列表='+b+', 序号=qx_index_'+a+')',
                                 indent+'            if qx_left_'+a+' == qx_right_'+a+':',
                                 indent+'                pass',indent+'            else:',
                                 indent+'                设置局部变量(self.game, 局部变量=qx_same_ref, 值=False)',indent+'    else:',indent+'        设置局部变量(self.game, 局部变量=qx_same_ref, 值=False)']
                    else:rows += [indent+'    if '+a+' == '+b+':',indent+'        pass',indent+'    else:',indent+'        设置局部变量(self.game, 局部变量=qx_same_ref, 值=False)']
                rows+=respond(indent+'    ','qx_same',state)+[indent+'else:']+respond(indent+'    ','False',state)
                return rows
            body=['        records: "结构体列表" = 获取自定义变量(self.game, 目标实体=信号来源实体, 变量名='+repr(variable)+')',
                  '        count: "整数" = 获取列表长度(self.game, 列表=records)','        if count == 1:',
                  '            record: "结构体" = 获取列表对应值(self.game, 列表=records, 序号=0)']
            parts,current=split('            ','record','current');body+=parts
            compatible=[current['qx_protocol']+' == 3',current['qx_record_version']+' == '+str(s.get('record_version',1))]
            compatible += [current[key]+' >= 0'for key in ('qx_session','qx_revision','qx_request')]
            stored_size=str(40+sum(8 if f['type']=='integer'else 1 if f['type']=='boolean'else 0 for f in fs))+''.join(' + 获取列表长度(self.game, 列表='+current[f['name']]+') * 8'for f in fs if f['type']=='integer_list')
            compatible += ['('+stored_size+') <= '+str(s['capacity_bytes'])]+['获取列表长度(self.game, 列表='+current[f['name']]+') <= '+str(f.get('max_items',s['capacity_bytes']//8))for f in fs if f['type']=='integer_list']
            body+=['            if '+' and '.join(compatible)+':']
            body+=process('                ',current)
            body+=['            else:']+respond('                ','False',defaults)+['        elif count == 0:']+process('            ',defaults,True)+['        else:']+respond('            ','False',defaults)
            checks=['request > 0']
            if action=='write':
                size=str(40+sum(8 if f['type']=='integer'else 1 if f['type']=='boolean'else 0 for f in fs))+''.join(' + 获取列表长度(self.game, 列表='+f['name']+') * 8'for f in fs if f['type']=='integer_list')
                checks += ['('+size+') <= '+str(s['capacity_bytes'])]+['获取列表长度(self.game, 列表='+f['name']+') <= '+str(f.get('max_items',s['capacity_bytes']//8))for f in fs if f['type']=='integer_list']
            lines+=['        if '+' and '.join(checks)+':',*['    '+line for line in body],'        else:',*respond('            ','False',defaults)]
            methods.append('\n'.join(lines))
    return signals,methods


def client_adapter(spec,legacy):
    # The shared adapter supplies typed field/codec checks, achievements and
    # cleanup. Only the explicitly versioned transport and transaction differ.
    runtime=(PLUGIN/'scripts/runtime_storage_v3.lua').read_text(encoding='utf-8')
    legacy=legacy.replace('local tx=Runtime.transaction(contract.fields,function(kind,request,values)',
        'local V3=(function()\n'+runtime+'\nend)()\n local tx=V3(Runtime,contract.fields,function(kind,request,values,session,revision)')
    legacy=legacy.replace("contract.name..'_'..kind..'_'..slot","contract.name..'_v3_'..kind..'_'..slot")
    legacy=legacy.replace("s:AddInt(request)\n  if kind=='write'", "s:AddInt(request)\n  if kind~='read'then s:AddInt(session);s:AddInt(revision)end\n  if kind=='write'")
    legacy=legacy.replace("ipairs({'read','write'})","ipairs({'read','open','write'})")
    legacy=legacy.replace('local bytes=8','local bytes=40')
    legacy=legacy.replace('p[i+2]end tx:receive(p[1],kind,values,p[2])','p[i+4]end tx:receive_v3(p[1],kind,values,p[2],p[3],p[4])')
    migration=(PLUGIN/'scripts/runtime_storage_migration.lua').read_text(encoding='utf-8')
    legacy=legacy.replace(' return tx\nend',' local installMigration=(function()\n'+migration+'\nend)()\n installMigration(tx,codec,contract,slot)\n return tx\nend')
    return legacy
