"""Deterministic entity-local timer clock for the restricted native model."""
import math

class TimerClock:
    def __init__(self,index_base=1):
        if type(index_base) is not int or index_base not in (0,1):
            raise ValueError('Timer index base must be 0 or 1')
        self.time=0.;self.serial=0;self.entries={};self.index_base=index_base

    def deadline(self):
        return min((entry['due']for entry in self.entries.values()if entry['paused']is None),default=None)

    def command(self,action,entity,name,loop=None,sequence=None):
        if type(entity)!=int or entity<0 or not isinstance(name,str)or not name:raise ValueError('Invalid timer identity')
        key=(entity,name)
        if action=='start':
            if type(loop)!=bool or not isinstance(sequence,list)or not 1<=len(sequence)<=100:raise ValueError('Invalid timer sequence')
            if any(type(v)not in(int,float)or not math.isfinite(v)or v<0 for v in sequence)or sequence[-1]<=0:raise ValueError('Invalid timer time')
            if any(b-a<.03-1e-12 for a,b in zip(sequence,sequence[1:])):raise ValueError('Timer sequence must increase by at least 0.03')
            if key not in self.entries and sum(k[0]==entity for k in self.entries)>=100:raise ValueError('Timer entity capacity exceeded')
            self.serial+=1
            self.entries[key]={'order':self.serial,'sequence':list(sequence),'loop':loop,'cycle':0,'index':0,'due':self.time+sequence[0],'paused':None}
        elif action not in('pause','resume','stop'):raise ValueError('Unknown timer action')
        elif key in self.entries:
            entry=self.entries[key]
            if action=='stop':del self.entries[key]
            elif action=='pause'and entry['paused']is None:entry['paused']=entry['due']-self.time
            elif action=='resume'and entry['paused']is not None:entry['due']=self.time+entry['paused'];entry['paused']=None

    def tick(self,dt,emit):
        if type(dt)not in(int,float)or not math.isfinite(dt)or not 0<=dt<=3600:raise ValueError('Invalid timer tick')
        end=self.time+dt;count=0
        while True:
            ready=[(v['due'],v['order'],k)for k,v in self.entries.items()if v['paused']is None and v['due']<=end]
            if not ready:break
            count+=1
            if count>10000:raise ValueError('Timer event budget exceeded')
            due,_,key=min(ready);self.time=due;entry=self.entries[key]
            index=entry['index'];cycle=entry['cycle'];seq=entry['sequence']
            # Schedule before dispatch so callbacks can stop, pause or replace it.
            if index+1<len(seq):entry['index']+=1;entry['due']+=seq[index+1]-seq[index]
            elif entry['loop']:entry['index']=0;entry['cycle']+=1;entry['due']+=seq[0]
            else:del self.entries[key]
            emit(key[0],key[1],index+self.index_base,cycle)
        self.time=end
