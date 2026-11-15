"""Extract a source-located catalogue from the bundled client API document."""
import hashlib,re
from pathlib import Path


def catalogue(path):
    raw=Path(path).read_bytes();methods={};fields={};enums={};section=None;unparsed=[];callbacks={}
    for line,text in enumerate(raw.decode('utf-8-sig').splitlines(),1):
        heading=re.match(r'## \d+\.(.+)$',text)
        if heading:section=heading[1]
        if not text.startswith('| `'):continue
        cells=[x.strip().replace('`','')for x in text.strip('|').split('|')]
        signature=cells[0]
        if signature.startswith('Enum.'):
            enums.setdefault(signature,[]).append(cells[1]);continue
        if len(cells)>=4 and cells[2].split('、')[0]in ('只读','读写'):
            for name in signature.split(','):
                fields.setdefault(section,{})[name.strip()]={'type':cells[1],'writable':cells[2].startswith('读写'),'line':line,'tweenable':'Tweenable'in cells[2]+cells[3]}
        elif '('in signature:
            matched=re.fullmatch(r'([\w.:]+)\((.*)\)',signature)
            if not matched:unparsed.append({'line':line,'signature':signature});continue
            name,args=matched.groups();owner=section;indexer=':'
            if ':'in name:owner,name=name.split(':',1)
            elif '.'in name:owner,name=name.split('.',1);indexer='.'
            elif section in ('全局API','Color','脚本生命周期'):owner='_G';indexer='.'
            if owner=='script':owner='Script'
            depth=0;start=0;parameters=[]
            for pos,char in enumerate(args+','):
                if char in '([{':depth+=1
                elif char in ')]}':depth-=1
                elif char==','and depth==0:
                    value=args[start:pos].strip();start=pos+1
                    if value:parameters.append(value)
            if depth:unparsed.append({'line':line,'signature':signature,'reason':'unbalanced parameters'});continue
            if section=='脚本生命周期':
                callbacks[name]={'parameters':parameters,'line':line};continue
            record={'parameters':parameters,'declared_parameters':parameters.copy(),'returns':cells[1],'indexer':indexer,'line':line,'description':cells[2]}
            if owner=='debug'and name=='traceback':record['parameters']=['message: string?','level: integer?'];record['signature_basis']='derived'
            key=owner+'.'+name
            if key in methods and any(methods[key][k]!=record[k]for k in ('parameters','returns','indexer')):
                raise ValueError('Conflicting signature '+key)
            methods.setdefault(key,record)
    # The compact control tables omit annotations. Resolve their parameters from
    # the same document's typed properties, event enums and callback descriptions.
    # Preserve the original spelling and all source lines used by each resolution.
    property_methods={
        'ClientUIBaseControl.SetActive':['active'],
        'ClientUIBaseControl.SetVisible':['visible'],
        'ClientUIBaseControl.GetChild':['name'],
        'ClientUIImageControl.SetSoftEdgeWidth':['softEdgeWidthX','softEdgeWidthY']}
    for stem,props in {'AnchoredPosition':['anchoredPositionX','anchoredPositionY'],
                       'SizeDelta':['sizeDeltaX','sizeDeltaY'],'AnchorMin':['anchorMinX','anchorMinY'],
                       'AnchorMax':['anchorMaxX','anchorMaxY'],'Pivot':['pivotX','pivotY'],
                       'LocalScale':['localScaleX','localScaleY','localScaleZ'],
                       'LocalRotation':['localRotationX','localRotationY','localRotationZ']}.items():
        property_methods['ClientUIBaseControl.Set'+stem]=props
        get=methods['ClientUIBaseControl.Get'+stem]
        get['return_types']=[fields['ClientUIBaseControl'][p]['type']for p in props]
        get['return_basis']='derived'
        get['type_source_lines']=[fields['ClientUIBaseControl'][p]['line']for p in props]
    explicit={
        '_G.typeof':{'value':'any'},'math.isnan':{'n':'number'},'math.isinf':{'n':'number'},
        'ClientUIBaseControl.FindChild':{'path':'string'},
        'ClientUIBaseControl.SetSiblingIndex':{'index':'integer'},
        'ClientUIBaseControl.GetScriptByPath':{'scriptPath':'string'},
        'ClientUIBaseControl.GetScript':{'scriptMappingId':'integer'},
        'ClientUIBaseControl.SetControllerNavigation':{'navigationDir':'ControllerNavigationDir','navigationMode':'ControllerNavigationMode','navigationTarget':'ClientUIBaseControl?'},
        'ClientUIBaseControl.GetControllerNavigation':{'navigationDir':'ControllerNavigationDir'},
        'ClientUIGridScrollerControl.RefreshItems':{'refreshCallback':'fun(control: ClientUIBaseControl, index: integer)'},
        'ClientUIGridScrollerControl.GetItemIndex':{'control':'ClientUIBaseControl'},
        'ClientUIGridScrollerControl.ScrollToItemAt':{'index':'integer','scrollAlignType':'ScrollAlignType'}}
    for owner,event,typ in [('ClientUIBaseControl','Key','KeyEventType'),
                            ('ClientUIBaseControl','Navigation','ControllerNavigationEventType'),
                            ('ClientUIPresetButtonControl','Cursor','CursorEventType'),
                            ('ClientUICursorEventAreaControl','Cursor','CursorEventType')]:
        for verb in ('Add','Remove'):
            explicit[owner+'.'+verb+event+'EventListener']={'eventType':typ,'callback':'fun()'}
        explicit[owner+'.Remove'+event+'EventListeners']={'eventType':typ}
    for key,method in methods.items():
        owner=key.split('.')[0];props={**fields.get('ClientUIBaseControl',{}),**fields.get(owner,{})}if owner.startswith('ClientUI')else fields.get(owner,{})
        typed=[];source_lines=list(method.get('type_source_lines',[]));enforced=[]
        for index,param in enumerate(method['parameters']):
            if ':'in param or param.startswith('...'):typed.append(param);enforced.append(method.get('signature_basis')!='derived');continue
            prop=property_methods.get(key,[])
            field=props.get(prop[index]if prop and index<len(prop)else param)
            typ=field['type']if field else explicit.get(key,{}).get(param)
            typed.append(param+': '+typ if typ else param)
            enforced.append(field is not None)
            if field:source_lines.append(field['line'])
            elif typ:source_lines.append(method['line'])
        method['parameters']=typed
        method['parameter_enforced']=enforced
        method['parameter_basis']=[('declared' if ':' in original or original.startswith('...') else 'derived' if ':' in resolved else 'unknown') for original,resolved in zip(method['declared_parameters'],typed)]
        if method.get('signature_basis')=='derived':method['parameter_basis']=['derived']*len(typed)
        if source_lines:method['type_source_lines']=sorted(set(source_lines))
    methods['ClientUIBaseControl.GetControllerNavigation']['return_types']=['ControllerNavigationMode','ClientUIBaseControl']
    methods['ClientUIBaseControl.GetControllerNavigation']['return_basis']='derived'
    for method in methods.values():method.setdefault('return_basis','declared')
    return {'sha256':hashlib.sha256(raw).hexdigest(),'methods':methods,'fields':fields,'enums':enums,'callbacks':callbacks,'unparsed':unparsed}


