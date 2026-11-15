"""Lexical Lua binding and source-located host API checks."""
from pathlib import Path
import base64,json,re,subprocess,shutil
from client_api_catalogue import catalogue
from authoring_io import PLUGIN,sha,schema

API_PATH=PLUGIN/'skills/client-controls-lua/references/client-controls-api.md'
PARSER=PLUGIN/'vendor/luaparse'
PARSER_FILES={'luaparse.js':'1c70940a6e46be63c84c285036925715f110bf06cbf058922372fb5c9d060b27',
              'LICENSE':'bedf97319fd3fb51c22dc5a44daf603ca4b2515ae75cae8ac677fb6bd40ec34e'}


def analyze(code,bindings=()):
    """Analyze UTF-8 Lua without running it; unknown facts remain unverified."""
    raw=code.encode('utf-8');api=catalogue(API_PATH)
    from knowledge import sources
    source=sources()['client_api']
    if source['integrity']!='passed':raise ValueError('Client API source changed; review the knowledge source registry')
    if api['unparsed']:raise ValueError('Unparsed client API signatures: '+str(api['unparsed']))
    provenance=json.loads((PARSER/'SOURCE.json').read_text('utf-8'))
    if provenance['version']!='0.3.1':raise ValueError('Unexpected Lua parser version')
    for name,digest in PARSER_FILES.items():
        if sha((PARSER/name).read_bytes())!=digest or provenance['files'][name]['sha256']!=digest:
            raise ValueError('Lua parser dependency differs: '+name)
    allowed=set(api['fields'])|{k.split('.')[0]for k in api['methods']}|{k[5:]for k in api['enums']}|{'string','integer','number','boolean','table','lua_function','ClientUIContainerControl'}
    if not isinstance(bindings,(list,tuple)):raise ValueError('API bindings must be a list')
    for binding in bindings:
        schema(binding,('range','type','value'),('range','type'))
        span=binding['range'];typ=binding['type']
        if not isinstance(span,list)or len(span)!=2 or any(type(n)is not int for n in span)or not 0<=span[0]<span[1]<=len(raw):
            raise ValueError('Binding range must address UTF-8 bytes')
        if not isinstance(typ,str)or typ.removesuffix('[]')not in allowed:raise ValueError('Unknown API binding type')
        if 'value'in binding:
            value=binding['value']
            if not(typ=='string'and isinstance(value,str)or typ=='integer'and type(value)is int and -(2**63)<=value<2**63):raise ValueError('Literal bindings require string or Lua 5.3 integer values')
    node=shutil.which('node')
    if node is None:raise ValueError('Node is required for client API checks')
    process=subprocess.run([node,'--preserve-symlinks','--preserve-symlinks-main',str(PLUGIN/'scripts/client_ast.cjs')],input=raw,capture_output=True)
    if process.returncode:raise ValueError('Lua AST parsing failed: '+process.stderr.decode('utf-8',errors='replace')[-1800:])
    analysis=Analysis(json.loads(process.stdout),api,bindings)
    return {'status':'failed'if analysis.errors else'not_checked'if analysis.unresolved else'passed',
            'scope':'lexical_host_members_permissions_calls_and_declared_types','source_sha256':sha(raw),
            'api_sha256':api['sha256'],'knowledge_source':source,'parser':{'version':'0.3.1','files':PARSER_FILES},
            'calls':analysis.calls,'errors':analysis.errors,'unresolved':analysis.unresolved,
            'bindings':list(bindings),'references':'not_checked','runtime':'not_checked'}


class Analysis:
    def __init__(self,tree,api,bindings=()):
        self.api=api;self.symbols=[];self.refs={};self.globals={};self.nodes=[];self.errors=[];self.unresolved=[];self.calls=[];self.cache={};self.resolving=set();self.env_refs=set();self.declarations=[];self.annotations={}
        self.bind_block(tree['body'],[{}])
        # Infer only lexical tables whose every use is a direct field read.
        # Aliasing, passing/returning the table, any field write, or reassignment
        # makes it unknown before analysis; never depend on traversal order.
        writes={id(v)for n in self.nodes if n['type']=='AssignmentStatement'for v in n['variables']}
        writes.update(id(n['identifier'])for n in self.nodes if n['type']=='FunctionDeclaration'and n.get('identifier'))
        reads={id(n['base'])for n in self.nodes if n['type']in('MemberExpression','IndexExpression')and id(n)not in writes and n.get('indexer')!=':'}
        self.readonly_tables=set()
        for sid,symbol in enumerate(self.symbols):
            if len(symbol['values'])!=1:continue
            value=symbol['values'][0]
            if 'result_of'in value:
                if value['position']!=0:continue
                value=value['result_of']
            if value.get('type')!='TableConstructorExpression':continue
            uses=[n for n in self.nodes if n['type']=='Identifier'and self.refs.get(id(n))==sid]
            if uses and all(id(n)in reads for n in uses):self.readonly_tables.add(id(value))
        self.contexts={}
        def contexts(node,scope='chunk',conditional=False):
            if isinstance(node,list):
                for child in node:contexts(child,scope,conditional)
            elif isinstance(node,dict):
                kind=node.get('type')
                if kind=='FunctionDeclaration':scope=str(node['range']);conditional=False
                if kind in ('IfStatement','WhileStatement','RepeatStatement','ForNumericStatement','ForGenericStatement','LogicalExpression'):conditional=True
                if kind in ('CallExpression','StringCallExpression','TableCallExpression'):self.contexts[tuple(node['range'])]={'scope':scope,'conditional':conditional}
                for key,value in node.items():
                    if key not in ('loc','range'):contexts(value,scope,conditional)
        contexts(tree)
        if any(n['type']=='GotoStatement'for n in self.nodes):
            for context in self.contexts.values():context['conditional']=True
        for binding in bindings:
            nodes=[n for n in self.declarations if n['range']==binding['range']]
            if len(nodes)!=1:raise ValueError('Binding requires one declaration range')
            sid=self.refs[id(nodes[0])]
            if sid in self.annotations:raise ValueError('Duplicate declaration binding')
            self.annotations[sid]=binding
        for sid in self.annotations:self.value(sid)
        for node in self.nodes:
            kind=node['type']
            if kind in ('CallExpression','StringCallExpression','TableCallExpression'):self.expression(node)
            elif kind in ('MemberExpression','IndexExpression'):self.expression(node)
            elif kind=='AssignmentStatement':
                for target in node['variables']:
                    if target['type']in ('MemberExpression','IndexExpression'):
                        expected=self.member(target,True);pos=node['variables'].index(target)
                        value=self.expression(node['init'][pos])if pos<len(node['init'])else None
                        if expected:self.check_type(value,expected['type'],target,'field_value')

    def symbol(self,name,initial=None):
        index=len(self.symbols);self.symbols.append({'name':name,'values':[]if initial is None else[initial]});return index

    def lookup(self,name,scopes):
        for scope in reversed(scopes):
            if name in scope:return scope[name]
        if name not in self.globals:self.globals[name]=self.symbol(name,{'host_global':name})
        return self.globals[name]

    def bind_block(self,body,scopes):
        for node in body:self.bind(node,scopes)

    def bind(self,node,scopes):
        if not isinstance(node,dict)or 'type'not in node:return
        self.nodes.append(node);kind=node['type']
        if kind=='Identifier':
            self.refs[id(node)]=self.lookup(node['name'],scopes)
            if self.refs[id(node)]==self.globals.get(node['name'])and any('_ENV'in scope for scope in scopes):self.env_refs.add(id(node))
            return
        if kind=='LocalStatement':
            for value in node['init']:self.bind(value,scopes)
            for i,var in enumerate(node['variables']):
                sid=self.symbol(var['name'],{'result_of':node['init'][-1],'position':i-len(node['init'])+1}if node['init']and i>=len(node['init'])-1 else node['init'][i]if i<len(node['init'])else{'unknown':'uninitialized'})
                scopes[-1][var['name']]=sid;self.refs[id(var)]=sid;self.declarations.append(var)
            return
        if kind=='AssignmentStatement':
            for value in node['init']:self.bind(value,scopes)
            for i,var in enumerate(node['variables']):
                self.bind(var,scopes)
                if var['type']=='Identifier':self.symbols[self.refs[id(var)]]['values'].append(node['init'][i]if i<len(node['init'])else{'unknown':'assignment'})
            return
        if kind=='FunctionDeclaration':
            ident=node.get('identifier')
            if ident:
                if node['isLocal']:
                    sid=self.symbol(ident['name'],{'type':'FunctionDeclaration'});scopes[-1][ident['name']]=sid;self.refs[id(ident)]=sid
                else:
                    self.bind(ident,scopes)
                    if ident['type']=='Identifier':self.symbols[self.refs[id(ident)]]['values'].append({'type':'FunctionDeclaration'})
            local={}
            for param in node['parameters']:
                if param['type']=='Identifier':
                    sid=self.symbol(param['name'],{'unknown':'parameter'});local[param['name']]=sid;self.refs[id(param)]=sid;self.declarations.append(param)
            if ident and ident['type']=='MemberExpression'and ident['indexer']==':':local['self']=self.symbol('self',{'unknown':'method_self'})
            self.bind_block(node['body'],scopes+[local]);return
        if kind=='IfStatement':
            for clause in node['clauses']:
                self.bind(clause.get('condition'),scopes);self.bind_block(clause['body'],scopes+[{}])
            return
        if kind in ('WhileStatement','DoStatement','RepeatStatement'):
            if kind=='WhileStatement':self.bind(node['condition'],scopes)
            local=scopes+[{}];self.bind_block(node['body'],local)
            if kind=='RepeatStatement':self.bind(node['condition'],local)
            return
        if kind in ('ForNumericStatement','ForGenericStatement'):
            if kind=='ForNumericStatement':
                for key in ('start','end','step'):self.bind(node.get(key),scopes)
                variables=[node['variable']]
            else:
                for value in node['iterators']:self.bind(value,scopes)
                variables=node['variables']
            local={}
            for i,var in enumerate(variables):
                initial={'iterator':node['iterators'][0],'position':i}if kind=='ForGenericStatement'and len(node['iterators'])==1 else{'unknown':'loop_variable'}
                sid=self.symbol(var['name'],initial);local[var['name']]=sid;self.refs[id(var)]=sid;self.declarations.append(var)
            self.bind_block(node['body'],scopes+[local]);return
        if kind=='MemberExpression':self.bind(node['base'],scopes);return
        if kind=='TableKeyString':self.bind(node['value'],scopes);return
        for key,value in node.items():
            if key in ('loc','range'):continue
            if isinstance(value,dict):self.bind(value,scopes)
            elif isinstance(value,list):
                for child in value:self.bind(child,scopes)

    def diagnostic(self,target,node,reason,**details):
        item={'line':node['loc']['start']['line'],'range':node['range'],'reason':reason,**details}
        if item not in target:target.append(item)

    def value(self,sid):
        if sid in self.cache:return self.cache[sid]
        if sid in self.resolving:return None
        self.resolving.add(sid);values=[]
        for expr in self.symbols[sid]['values']:
            if 'host_global'in expr:
                name=expr['host_global'];v={'type':{'script':'Script','game':'game','Color':'Color','Enum':'Enum','_G':'Globals','_ENV':'Globals','io':'forbidden','coroutine':'forbidden','os':'os','debug':'debug','string':'string_library','math':'math'}.get(name)}
                if v['type']is None:v={'type':'function','owner':'_G','name':name}if '_G.'+name in self.api['methods']else {'type':'builtin','name':name}if name in ('pcall','ipairs','pairs')else None
            elif 'result_of'in expr:
                returns=self.results(expr['result_of']);v=returns[expr['position']]if returns is not None and expr['position']<len(returns)else None
            elif 'iterator'in expr:
                iterator=expr['iterator'];v=None
                if iterator['type']=='CallExpression':
                    target=self.expression(iterator['base'])
                    source=self.expression(iterator['arguments'][0])if iterator['arguments']else None
                    if target and target['type']=='builtin'and target['name']=='ipairs'and source and source['type'].endswith('[]'):
                        v={'type':'integer'}if expr['position']==0 else{'type':source['type'][:-2]}if expr['position']==1 else None
            else:v=self.expression(expr)
            values.append(v)
        result=values[0]if values and all(v==values[0]for v in values)else None
        if result is None and values and all(v and v['type']==values[0]['type']for v in values):
            typ=values[0]['type']
            if typ in ('integer','number','boolean','string'):result={'type':typ}
        if result is None and any(v and v['type']in ('game','Script','Color','Enum','Globals','uncertain_host')for v in values):result={'type':'uncertain_host'}
        if sid in self.annotations:
            annotation=self.annotations[sid]
            refinement=result is not None and result['type']=='ClientUIBaseControl'and annotation['type'].startswith('ClientUI')and annotation['type']in self.api['fields']
            if result is not None and not refinement and not self.compatible(result,annotation['type']):raise ValueError('Binding conflicts with inferred type')
            if 'value'in annotation and result is not None and result.get('value')is not None and result['value']!=annotation['value']:raise ValueError('Binding conflicts with inferred value')
            result={'type':annotation['type'],**({'value':annotation['value']}if 'value'in annotation else{})}
        self.resolving.remove(sid);self.cache[sid]=result;return result

    def member(self,node,write=False):
        base=self.expression(node['base'])
        if base is None:
            self.diagnostic(self.unresolved,node,'unknown_receiver_type')
            return None
        owner=base['type']
        if owner=='uncertain_host':
            self.diagnostic(self.unresolved,node,'mutable_host_alias');return None
        if node['type']=='MemberExpression':name=node['identifier']['name']
        else:
            key=self.expression(node['index']);name=key.get('value')if key and key['type']=='string'else None
        if owner.endswith('[]'):
            key=self.expression(node['index'])if node['type']=='IndexExpression'else None
            return {'type':owner[:-2]}if key and key['type']in ('number','integer')else None
        if owner=='table':return base.get('fields',{}).get(name)if not write else None
        if owner in ('string','number','integer','boolean','lua_function'):return None
        if owner=='nil':
            self.diagnostic(self.errors,node,'nil_receiver');return None
        if name is None:
            self.diagnostic(self.unresolved,node,'dynamic_host_member',owner=owner);return None
        if owner=='Globals':
            if write:
                self.diagnostic(self.unresolved,node,'global_environment_write',name=name);return None
            return self.value(self.lookup(name,[{}]))
        if owner=='forbidden'or owner=='os'and name not in ('time','date','clock','difftime')or owner=='debug'and name!='traceback'or owner=='string_library'and name=='dump':
            self.diagnostic(self.errors,node,'unsupported_host_library',owner=owner,name=name);return None
        if owner=='Enum':
            if 'Enum.'+name in self.api['enums']:return {'type':'Enum.'+name}
            self.diagnostic(self.errors,node,'unknown_enum_type',name=name);return None
        if owner.startswith('Enum.'):
            if name in self.api['enums'][owner]:return {'type':'EnumItem','enum':owner,'value':name}
            self.diagnostic(self.errors,node,'unknown_enum_value',owner=owner,name=name);return None
        if owner in ('game','Color','math','os','debug','string_library')and write:
            self.diagnostic(self.unresolved,node,'host_namespace_write',owner=owner,name=name);return None
        owners=[owner]
        if 'Enum.'+owner in self.api['enums']:owners.append('EnumItem')
        if owner.startswith('ClientUI')and owner!='ClientUIBaseControl':owners.append('ClientUIBaseControl')
        for candidate in owners:
            field=self.api['fields'].get(candidate,{}).get(name)
            if field:
                if write and not field['writable']:self.diagnostic(self.errors,node,'readonly_field',owner=candidate,name=name,source_line=field['line'])
                return None if field['type']=='any'else{'type':field['type']}
            signature=self.api['methods'].get(candidate+'.'+name)
            if signature:
                if write:self.diagnostic(self.unresolved,node,'host_method_assignment',owner=candidate,name=name)
                return {'type':'function','owner':candidate,'name':name}
        if owner in ('os','debug','string_library','math'):return None
        if owner in self.api['fields']or any(k.startswith(owner+'.')for k in self.api['methods']):
            self.diagnostic(self.errors,node,'unknown_host_member',owner=owner,name=name)
        return None

    def results(self,node):
        if node.get('parenthesized')or node.get('type')not in ('CallExpression','StringCallExpression','TableCallExpression'):return [self.expression(node)]
        target=self.expression(node['base'])
        if target and target['type']=='builtin'and target['name']=='pcall'and node['arguments']:
            inner={**node,'base':node['arguments'][0],'arguments':node['arguments'][1:]}
            returns=self.results(inner)
            return None if returns is None else[{'type':'boolean'}]+returns
        first=self.expression(node)
        if target and target['type']=='Color':return [first]
        if not target or target['type']!='function':return None
        signature=self.api['methods'][target['owner']+'.'+target['name']]
        if 'return_types'in signature:return [{'type':t}for t in signature['return_types']]
        result=signature['returns']
        if result=='—':return []
        if ':'in result:
            names,typ=result.split(':',1);return [{'type':typ.strip()}for name in names.split(',')]
        if ','in result:return [None for name in result.split(',')]
        return [first]

    def expression(self,node):
        kind=node.get('type')
        if kind=='Identifier':
            if id(node)in self.env_refs:
                self.diagnostic(self.unresolved,node,'local_environment',name=node['name']);return None
            return self.value(self.refs[id(node)])
        if kind=='StringLiteral':
            raw=base64.b64decode(node['value']['bytes'])
            try:value=raw.decode('utf-8')
            except UnicodeDecodeError:value=None
            return {'type':'string','value':value,'bytes':node['value']['bytes']}
        if kind=='NumericLiteral':
            raw=node['raw'];integer=bool(re.fullmatch(r'0[xX][0-9a-fA-F]+',raw))or bool(re.fullmatch(r'[0-9]+',raw))and int(raw)<=9223372036854775807
            result={'type':'integer'if integer else'number','raw':raw}
            if integer:
                number=int(raw,16 if raw.lower().startswith('0x')else 10)
                result['value']=(number+2**63)%2**64-2**63
            return result
        if kind=='NilLiteral':return {'type':'nil'}
        if kind=='FunctionDeclaration':return {'type':'lua_function'}
        if kind=='BooleanLiteral':return {'type':'boolean','value':node['value']}
        if kind=='TableConstructorExpression':
            if id(node)not in self.readonly_tables:return {'type':'table'}
            values={}
            for field in node['fields']:
                if field['type']=='TableKeyString':key=field['key']['name']
                elif field['type']=='TableKey':
                    literal=self.expression(field['key']);key=literal.get('value')if literal and literal['type']=='string'else None
                else:return {'type':'table'}
                value=self.expression(field['value'])
                if key is None or not value or value['type']not in('string','integer','number','boolean')or 'value'not in value:return {'type':'table'}
                values[key]=value
            return {'type':'table','fields':values}
        if kind=='UnaryExpression':
            if node['operator']=='not':return {'type':'boolean'}
            if node['operator']=='#':return {'type':'integer'}
            value=self.expression(node['argument'])
            if not value or value['type']not in ('integer','number'):return None
            result={'type':value['type']}
            if value['type']=='integer'and type(value.get('value'))is int and node['operator']in('-','~'):
                number=-value['value']if node['operator']=='-'else~value['value']
                result['value']=(number+2**63)%2**64-2**63
            return result
        if kind in ('BinaryExpression','LogicalExpression'):
            left=self.expression(node['left']);right=self.expression(node['right']);op=node['operator']
            if op in ('==','~=','<','>','<=','>='):return {'type':'boolean'}
            if op in ('and','or'):return left if left==right else None
            if op=='..'and left and right and left['type']==right['type']=='string':
                return {'type':'string','value':left['value']+right['value']}if left.get('value')is not None and right.get('value')is not None else{'type':'string'}
            if left and right and left['type']in ('integer','number')and right['type']in ('integer','number'):
                return {'type':'integer'if left['type']==right['type']=='integer'and op not in ('/','^')else'number'}
            return None
        if kind in ('MemberExpression','IndexExpression'):return self.member(node)
        if kind in ('CallExpression','StringCallExpression','TableCallExpression'):
            target=self.expression(node['base'])
            if target and target['type']=='builtin'and target['name']=='pcall':
                if node.get('arguments'):self.expression({**node,'base':node['arguments'][0],'arguments':node['arguments'][1:]})
                return {'type':'boolean'}
            if target and target['type']=='Color':target={'type':'function','owner':'_G','name':'Color'}
            if not target or target['type']!='function':
                for argument in node.get('arguments',[])if isinstance(node.get('arguments',[]),list)else[]:
                    value=self.expression(argument)
                    if value and value['type']=='ServerSignal':self.diagnostic(self.unresolved,node,'signal_escapes_known_calls')
                if target and target['type']not in ('lua_function','table','builtin','uncertain_host'):
                    self.diagnostic(self.errors,node,'non_callable_value',actual=target['type'])
                elif target is None:self.diagnostic(self.unresolved,node,'unresolved_call_target')
                return None
            owner=target['owner'];name=target['name'];signature=self.api['methods'][owner+'.'+name]
            callstyle=node['base'].get('indexer','.')
            args=node.get('arguments',[node['argument']]if 'argument'in node else[])
            if not isinstance(args,list):args=[args]
            receiver=self.expression(node['base']['base'])if callstyle==':'else self.expression(args[0])if signature['indexer']==':'and args else None
            if signature['indexer']=='.'and callstyle==':':self.diagnostic(self.errors,node,'namespace_requires_dot',owner=owner,name=name)
            elif signature['indexer']==':'and callstyle!=':':
                receiver=self.expression(args[0])if args else None
                if receiver is None:self.diagnostic(self.unresolved,node,'unknown_explicit_receiver',owner=owner,name=name)
                elif not self.compatible(receiver,owner):self.diagnostic(self.errors,node,'instance_receiver_missing',owner=owner,name=name)
                args=args[1:]
            required=sum('?'not in p and not p.startswith('...')for p in signature['parameters'])
            variable=any(p.startswith('...')for p in signature['parameters'])
            values=[self.expression(a)for a in args[:-1]]
            tail=self.results(args[-1])if args and args[-1]['type']!='VarargLiteral'else None if args else[]
            if tail is None:
                self.diagnostic(self.unresolved,node,'call_result_argument_count',owner=owner,name=name)
            else:
                values+=tail
                if len(values)<required or not variable and len(values)>len(signature['parameters']):
                    self.diagnostic(self.errors,node,'argument_count',owner=owner,name=name,actual=len(values),required=required)
            for index,parameter in enumerate(signature['parameters']):
                if parameter.startswith('...'):break
                if index>=len(values):break
                if ':'not in parameter:
                    self.diagnostic(self.unresolved,node,'undocumented_parameter_type',owner=owner,name=name,parameter=parameter)
                else:self.check_type(values[index],parameter.split(':',1)[1].strip(),node,'argument',index=index+1,knowledge_basis=signature['parameter_basis'][index],enforced=signature['parameter_enforced'][index],source_line=signature['line'],type_source_lines=signature.get('type_source_lines',[]))
            record={'line':node['loc']['start']['line'],'range':node['range'],'owner':owner,'name':name,'source_line':signature['line'],
                    'type_source_lines':signature.get('type_source_lines',[]),'parameter_basis':signature['parameter_basis'],'return_basis':signature['return_basis'],'arguments':values,
                    **self.contexts.get(tuple(node['range']),{'scope':'unknown','conditional':True})}
            if receiver and receiver['type']=='ServerSignal':record['signal_origin']=receiver.get('origin')
            if record not in self.calls:self.calls.append(record)
            result=signature['return_types'][0]if 'return_types'in signature else signature['returns']
            if owner=='game'and name=='ServerSignal':return {'type':'ServerSignal','origin':node['range']}
            if result=='—':return {'type':'nil'}
            if ':'in result:result=result.split(':',1)[1].strip()
            return {'type':result}if re.fullmatch(r'[A-Za-z]\w*(?:\[\])?',result)and result!='any'else None
        return None

    def compatible(self,value,expected):
        actual=value['type'];optional=expected.endswith('?');expected=expected.removesuffix('?')
        if expected=='any'or optional and actual=='nil':return True
        if actual==expected:return True
        if expected=='number'and actual=='integer':return True
        if expected.startswith('fun(')and actual in ('lua_function','function'):return True
        if expected=='ClientUIBaseControl'and actual.startswith('ClientUI')and actual in self.api['fields']:return True
        if actual=='EnumItem'and value.get('enum')=='Enum.'+expected:return True
        return False

    def check_type(self,value,expected,node,context,**details):
        if expected=='any':return
        if value is None:
            self.diagnostic(self.unresolved,node,'unknown_value_type',expected=expected,context=context,**details)
        elif expected.endswith('[]')and value['type']=='table':
            self.diagnostic(self.unresolved,node,'unverified_list_elements',expected=expected,context=context,**details)
        elif not self.compatible(value,expected):
            self.diagnostic(self.errors if details.get('enforced',True) else self.unresolved,node,'value_type',expected=expected,actual=value['type'],context=context,**details)

