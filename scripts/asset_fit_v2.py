"""Budget-constrained deterministic search; schema 1 stays in asset_fit."""
import bisect
import random
from PIL import Image, ImageDraw, ImageChops, ImageStat, __version__ as PILLOW_VERSION
from authoring_io import sha, canonical
from asset_fit import paint, render, error, rectangle_data

ALGORITHM = 'residual-budget-2'


def fit(image, cfg, binding, state=None, steps=None, initial=None):
    size = image.size
    if size[0]*size[1] > 262144:
        raise ValueError('Fit input exceeds 262144 pixels')
    if steps is not None and (type(steps) != int or steps <= 0):
        raise ValueError('steps must be positive')
    regions = cfg['regions'] or [[0, 0, *size]]
    if any(not (0 <= l < r <= size[0] and 0 <= t < b <= size[1]) for l,t,r,b in regions):
        raise ValueError('Region outside image')
    region = Image.new('L', size)
    draw = ImageDraw.Draw(region)
    for l,t,r,b in regions:
        draw.rectangle((l,t,r-1,b-1), fill=255)
    allowed = ImageChops.multiply(region, image.getchannel('A').point(lambda a: 255 if a >= cfg['alpha_min'] else 0))
    points = [(i % size[0], i // size[0]) for i,a in enumerate(allowed.getdata()) if a]
    rng = random.Random(cfg['seed'])
    algorithm = state.get('identity',{}).get('algorithm') if state else ALGORITHM
    if algorithm not in ('residual-budget-1', ALGORITHM): raise ValueError('Resume algorithm identity mismatch')
    identity = {'algorithm': algorithm, 'pillow': PILLOW_VERSION, 'config_sha256': sha(canonical(cfg).encode())}
    shapes = list(initial or [])
    done = cursor = 0
    stats = dict(renders=0, cost_evaluations=0, budget_rejections=0, local_attempts=0)
    if state is not None:
        if state.get('schema') != 2 or state.get('binding') != binding or state.get('identity') != identity:
            raise ValueError('Resume input/configuration/algorithm identity mismatch')
        if state.get('sha256') != sha(canonical({k:v for k,v in state.items() if k != 'sha256'}).encode()):
            raise ValueError('Resume state checksum mismatch')
        shapes = state['shapes']; done = state['work_done']; cursor = state['cursor']; stats = state['stats'].copy()
        if type(done) != int or not 0 <= done <= cfg['work'] or type(cursor) != int or cursor < 0:
            raise ValueError('Invalid resume work/cursor')
        rng.setstate((state['rng'][0], tuple(state['rng'][1]), state['rng'][2]))
    if len(shapes) > cfg['budget']:
        raise ValueError('Initial primitives exceed budget')
    canvas = render(size, shapes)
    current = error(canvas, image)
    controls = len(rectangle_data(canvas)['rects'])
    if controls > cfg['max_controls']:
        raise ValueError('Initial rectangles exceed control budget')
    history = state['history'][:] if state else [[current, controls]]
    if not history or history[-1] != [current, controls] or any(not (b[0] < a[0] or b[0] == a[0] and b[1] < a[1]) for a,b in zip(history,history[1:])):
        raise ValueError('Invalid resume error/cost history')
    cumulative = None
    target = image.convert('RGBa')
    limit = cfg['work'] if steps is None else min(cfg['work'], done+steps)
    while done < limit and current > cfg['target_error'] and points:
        if cumulative is None:
            residual = ImageChops.difference(canvas.convert('RGBa'), target)
            cumulative = []; total = 0
            for xy in points:
                total += sum(c*c for c in residual.getpixel(xy)); cumulative.append(total)
        if rng.random() < .75 and cumulative[-1]:
            x,y = points[bisect.bisect_right(cumulative, rng.random()*cumulative[-1])]
        else:
            x,y = rng.choice(points)
        local = bool(shapes) and (done % 3 == 2 or len(shapes) >= cfg['budget'])
        kind = rng.choice(cfg['shapes'])
        scale = max(1, round(max(size)*(1-done/cfg['work'])/2))
        w = rng.randint(1,min(scale,size[0])); h = rng.randint(1,min(scale,size[1]))
        if kind == 'circle': w = h = min(w,h)
        if kind == 'line':
            if rng.randrange(2): w = 1
            else: h = 1
        l = max(0,min(size[0]-w,x-w//2)); t = max(0,min(size[1]-h,y-h//2))
        box = [l,t,l+w,t+h]; color = list(image.getpixel((x,y)))
        # Spend one existing proposal, not extra work: a coherent source region avoids
        # building flat translucent areas from many overlapping alpha composites.
        if algorithm == ALGORITHM and not local and done % 4 == 0 and 'rect' in cfg['shapes']:
            kind = 'rect'
            pixels = image.load(); mask = allowed.load(); reference = pixels[x,y]
            def coherent(xx,yy):
                c = pixels[xx,yy]
                return mask[xx,yy] and c[3] == reference[3] and max(abs(c[k]-reference[k]) for k in range(3)) <= 32
            left=right=x; top=bottom=y
            while left>0 and coherent(left-1,y): left-=1
            while right+1<size[0] and coherent(right+1,y): right+=1
            while top>0 and all(coherent(xx,top-1) for xx in range(left,right+1)): top-=1
            while bottom+1<size[1] and all(coherent(xx,bottom+1) for xx in range(left,right+1)): bottom+=1
            box=[left,top,right+1,bottom+1]
            color=[round(v) for v in ImageStat.Stat(image.crop(tuple(box))).mean]
        index = len(shapes)
        if local:
            stats['local_attempts'] += 1
            index = cursor % len(shapes); cursor += 1
            old = shapes[index]; kind = old['kind']; box = old['box'][:]; color = old['color'][:]
            move = rng.choice((-1,1)); axis = rng.randrange(2); action = rng.randrange(3)
            if action == 0:
                box[axis] += move; box[axis+2] += move
            elif action == 1:
                if kind == 'circle': box[2] += move; box[3] += move
                elif kind == 'line': box[2 if box[2]-box[0]>1 else 3] += move
                else: box[axis+2*rng.randrange(2)] += move
            else:
                color = list(image.getpixel(((box[0]+box[2]-1)//2,(box[1]+box[3]-1)//2)))
        done += 1
        if not (0 <= box[0] < box[2] <= size[0] and 0 <= box[1] < box[3] <= size[1]): continue
        if local and ImageChops.subtract(paint(size,shapes[index]).getchannel('A'),region).getbbox(): continue
        proposal = {'kind':kind,'box':box,'color':color}
        layer = paint(size,proposal)
        if ImageChops.subtract(layer.getchannel('A').point(lambda a:255 if a else 0),allowed).getbbox(): continue
        trial = shapes[:]; trial[index:index+1] = [proposal]
        candidate = render(size,trial) if local else Image.alpha_composite(canvas,layer)
        stats['renders'] += 1
        score = error(candidate,image)
        if score > current: continue
        cost = len(rectangle_data(candidate)['rects']); stats['cost_evaluations'] += 1
        if cost > cfg['max_controls']:
            stats['budget_rejections'] += 1; continue
        if score < current or score == current and cost < controls:
            shapes = trial; canvas = candidate; current = score; controls = cost
            history.append([score,cost]); cumulative = None
    reason = 'target_reached' if current <= cfg['target_error'] else 'no_allowed_pixels' if not points else 'work_exhausted' if done == cfg['work'] else 'step_limit'
    result = dict(schema=2, identity=identity, binding=binding, shapes=shapes, work_done=done,
                  cursor=cursor, stats=stats, history=history, errors=[r[0] for r in history],
                  rng=rng.getstate(), stop_reason=reason, target_reached=current<=cfg['target_error'])
    result['sha256'] = sha(canonical(result).encode())
    return result,canvas
