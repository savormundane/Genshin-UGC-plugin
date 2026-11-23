"""Plugin-owned image preparation and rectangle/rich-text compilation; Pillow only."""
from contextlib import contextmanager

ASSET_GENERATOR = 'miliastra-wonderland-assets'
ASSET_GENERATORS = (ASSET_GENERATOR, 'genshin-ugc-assets')


@contextmanager
def open_single_image(source, max_pixels):
    from PIL import Image
    try:
        image = Image.open(source)
    except Image.DecompressionBombError as error:
        raise ValueError(f'{source.name}: {error} This tool allows {max_pixels} source pixels; preprocess explicitly') from error
    with image:
        width, height = image.size
        if width * height > max_pixels:
            raise ValueError(f'{source.name}: {width}x{height} exceeds {max_pixels} pixels; preprocess explicitly')
        if getattr(image, 'n_frames', 1) != 1:
            raise ValueError('Extract animation frames explicitly')
        yield image


def harden(image, threshold):
    from PIL import Image
    mask = image.getchannel('A').point([0] * threshold + [255] * (256 - threshold))
    result = Image.new('RGBA', image.size)
    result.paste(image, mask=mask)
    result.putalpha(mask)
    return result


def compile_image(image, step, colors, threshold):
    from PIL import Image
    image = harden(image.convert('RGBA'), threshold)
    size = (max(1, (image.width + step - 1) // step),
            max(1, (image.height + step - 1) // step))
    image = harden(image.convert('RGBa').resize(size, Image.Resampling.BOX)
                   .convert('RGBA'), threshold)
    preview, palette, grid = quantized_grid(image, colors)
    return preview, palette, rectangles(image.size, palette, grid) if palette else []


def quantized_grid(image, colors):
    from PIL import Image
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
    preview = Image.new('RGBA', image.size)
    preview.putdata([tuple(palette[i - 1]) if i else (0, 0, 0, 0) for i in grid])
    return preview, palette, grid


def rectangles(size, palette, grid):
    width, height = size
    rects, previous = [], {}
    for y in range(height):
        current, x = {}, 0
        while x < width:
            key = grid[y * width + x]
            if not key:
                x += 1
                continue
            end = x + 1
            while end < width and grid[y * width + end] == key:
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
        assert x >= 0 and y >= 0 and x + w <= width and y + h <= height
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                i = yy * width + xx
                assert not seen[i] and grid[i] == color
                seen[i] = color
    assert seen == grid, 'Rectangles must exactly cover quantized foreground'
    return rects



def compile_tiles(image, *, width, height, alpha_min=128, columns=64, max_bytes=4096, cell=16, fit='auto'):
    from PIL import Image
    if any(type(v)!=int or v<1 for v in (width,height,columns,max_bytes,cell)):
        raise ValueError('Dimensions, columns, byte budget and cell must be positive integers')
    if width*height>1048576:raise ValueError('Grid exceeds 1048576 pixels; reduce dimensions explicitly')
    if type(alpha_min)!=int or not 1<=alpha_min<=255:raise ValueError('alpha_min must be 1..255')
    if fit not in ('auto','fixed'):raise ValueError('fit must be auto or fixed')
    grid=image.convert('RGBA').convert('RGBa').resize((width,height),Image.Resampling.BOX).convert('RGBA')
    preview=harden(grid,alpha_min)
    return preview,text_tiles(preview,columns,max_bytes,cell,fit)


def text_tiles(image, columns, max_bytes, cell, fit):
    width,height=image.size
    pixels=image.load()
    tag_bytes=len('<color=#000000></color>')
    pixel_bytes=len('■'.encode('utf-8'))
    tiles=[]
    for y in range(height):
        x=0
        while x<width:
            if not pixels[x,y][3]:x+=1;continue
            start=x;runs=[];used_bytes=0
            while x<width and pixels[x,y][3] and x-start<columns:
                color=pixels[x,y][:3]
                new_run=not runs or runs[-1][0]!=color
                increment=pixel_bytes + (tag_bytes if new_run else 0)
                if used_bytes+increment>max_bytes:
                    if not runs:raise ValueError('Byte budget cannot hold one colored pixel')
                    break
                if new_run:runs.append([color,1])
                else:runs[-1][1]+=1
                used_bytes+=increment
                x+=1
            text=''.join('<color=#%02X%02X%02X>'%color+'■'*count+'</color>' for color,count in runs)
            count=x-start
            tiles.append({'x':start*cell,'y':y*cell,'width':(columns if fit=='fixed' else count)*cell,
                          'height':cell,'columns':count,'text':text,'font_size':cell})
    return tiles


def compile_prepared(image, target, colors, columns, max_bytes, cell, fit):
    # Both outputs consume the same hardened, quantized reference grid.
    preview,palette,grid=quantized_grid(image,colors)
    if target=='rectangles':
        rects=rectangles(image.size,palette,grid) if palette else []
        return preview,{'palette':palette,'rects':rects},len(rects)
    tiles=text_tiles(preview,columns,max_bytes,cell,fit)
    return preview,{'tiles':tiles},len(tiles)
