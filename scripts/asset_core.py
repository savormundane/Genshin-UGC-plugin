"""Plugin-owned image preparation and rectangle/rich-text compilation; Pillow only."""
def harden(image, threshold):
    result = image.copy()
    result.putdata([(r, g, b, 255) if a >= threshold else (0, 0, 0, 0)
                    for r, g, b, a in image.getdata()])
    return result


def compile_image(image, step, colors, threshold):
    from PIL import Image
    image = harden(image.convert('RGBA'), threshold)
    size = (max(1, (image.width + step - 1) // step),
            max(1, (image.height + step - 1) // step))
    image = harden(image.convert('RGBa').resize(size, Image.Resampling.BOX)
                   .convert('RGBA'), threshold)
    pixels = list(image.getdata())
    foreground = [p[:3] for p in pixels if p[3]]
    if not foreground:
        return image, [], []
    swatch = Image.new('RGB', (len(foreground), 1))
    swatch.putdata(foreground)
    quantized = swatch.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    color_values = quantized.getpalette()
    ids = iter(quantized.getdata())
    palette, mapping, grid = [], {}, []
    for p in pixels:
        if not p[3]:
            grid.append(0)
            continue
        old = next(ids)
        if old not in mapping:
            mapping[old] = len(palette) + 1
            palette.append(color_values[old * 3:old * 3 + 3] + [255])
        grid.append(mapping[old])
    rects, previous = [], {}
    for y in range(image.height):
        current, x = {}, 0
        while x < image.width:
            key = grid[y * image.width + x]
            if not key:
                x += 1
                continue
            end = x + 1
            while end < image.width and grid[y * image.width + end] == key:
                end += 1
            run = (x, end - x, key)
            if run in previous:
                index = previous[run]
                rects[index][3] += 1
            else:
                index = len(rects)
                rects.append([x, y, end - x, 1, key])
            current[run] = index
            x = end
        previous = current
    seen = [0] * len(grid)
    for x, y, w, h, color in rects:
        assert 1 <= color <= len(palette)
        assert x >= 0 and y >= 0 and x + w <= image.width and y + h <= image.height
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                i = yy * image.width + xx
                assert not seen[i] and grid[i] == color
                seen[i] = color
    assert seen == grid, 'Rectangles must exactly cover quantized foreground'
    preview = Image.new('RGBA', image.size)
    preview.putdata([tuple(palette[i - 1]) if i else (0, 0, 0, 0) for i in grid])
    return preview, palette, rects



def compile_tiles(image, *, width, height, alpha_min=128, columns=64, max_bytes=4096, cell=16, fit='auto'):
    from PIL import Image
    if any(type(v)!=int or v<1 for v in (width,height,columns,max_bytes,cell)):
        raise ValueError('Dimensions, columns, byte budget and cell must be positive integers')
    if width*height>1048576:raise ValueError('Grid exceeds 1048576 pixels; reduce dimensions explicitly')
    if type(alpha_min)!=int or not 1<=alpha_min<=255:raise ValueError('alpha_min must be 1..255')
    if fit not in ('auto','fixed'):raise ValueError('fit must be auto or fixed')
    grid=image.convert('RGBA').convert('RGBa').resize((width,height),Image.Resampling.BOX).convert('RGBA')
    pixels=[(r,g,b,255) if a>=alpha_min else (0,0,0,0) for r,g,b,a in grid.getdata()]
    preview=Image.new('RGBA',(width,height));preview.putdata(pixels)
    def markup(colors):
        runs=[]
        for color in colors:
            if runs and runs[-1][0]==color:runs[-1][1]+=1
            else:runs.append([color,1])
        return ''.join('<color=#%02X%02X%02X>'%color+'■'*count+'</color>' for color,count in runs)
    tiles=[]
    for y in range(height):
        x=0
        while x<width:
            if not pixels[y*width+x][3]:x+=1;continue
            start=x; colors=[]
            while x<width and pixels[y*width+x][3] and len(colors)<columns:
                candidate=colors+[pixels[y*width+x][:3]]
                if len(markup(candidate).encode('utf-8'))>max_bytes:
                    if not colors:raise ValueError('Byte budget cannot hold one colored pixel')
                    break
                colors=candidate;x+=1
            text=markup(colors)
            tiles.append({'x':start*cell,'y':y*cell,'width':(columns if fit=='fixed' else len(colors))*cell,
                          'height':cell,'columns':len(colors),'text':text,'font_size':cell})
    return preview,tiles


def compile_prepared(image, target, colors, columns, max_bytes, cell, fit):
    # Both outputs consume the same hardened, quantized reference grid.
    preview,palette,rects=compile_image(image,1,colors,128)
    if target=='rectangles':
        return preview,{'palette':palette,'rects':rects},len(rects)
    preview,tiles=compile_tiles(preview,width=preview.width,height=preview.height,columns=columns,max_bytes=max_bytes,cell=cell,fit=fit)
    return preview,{'tiles':tiles},len(tiles)
