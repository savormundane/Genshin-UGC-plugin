"""Reusable offline rectangle compiler; requires Pillow, never changes the source.

Uses alpha hardening, premultiplied BOX resize, foreground palette quantization,
horizontal runs and lossless vertical merges. It does not implement greedy
color-error fusion. Reduce resolution explicitly if the rectangle budget fails.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image


from asset_core import harden, compile_image

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--out', required=True, type=Path, help='New output directory')
    parser.add_argument('--step', type=int, default=1)
    parser.add_argument('--colors', type=int, default=96)
    parser.add_argument('--alpha-min', type=int, default=128)
    parser.add_argument('--max-rects', type=int, help='Fail rather than silently degrade')
    args = parser.parse_args()
    if args.step < 1 or not 1 <= args.colors <= 256 or not 1 <= args.alpha_min <= 255:
        parser.error('step>=1, colors in 1..256, alpha-min in 1..255 required')
    if args.max_rects is not None and args.max_rects < 1:
        parser.error('max-rects must be positive')
    if args.out.exists():
        parser.error('Output directory already exists; choose a new directory')
    if not args.source.is_file():
        parser.error('Source image not found')
    source_bytes = args.source.read_bytes()
    with Image.open(args.source) as im:
        original_size = list(im.size)
        preview, palette, rects = compile_image(im, args.step, args.colors, args.alpha_min)
    if args.max_rects is not None and len(rects) > args.max_rects:
        parser.error(f'{len(rects)} rectangles exceed budget {args.max_rects}; increase --step explicitly')
    rows = lambda values: '{' + ','.join('{' + ','.join(map(str, v)) + '}' for v in values) + '}'
    lua = (f'return {{w={preview.width},h={preview.height},maxRects={len(rects)},'
           f'palette={rows(palette)},rects={rows(rects)}}}\n')
    metadata = dict(source_sha256=hashlib.sha256(source_bytes).hexdigest(),
                    source_size=original_size, grid_size=list(preview.size),
                    step=args.step, alpha_min=args.alpha_min, palette_colors=len(palette),
                    rectangles=len(rects), coordinate_space='top_left_grid_pixels',
                    algorithm='foreground median-cut + exact horizontal/vertical merges',
                    coverage_verified=True, host_runtime_tested=False)
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / 'data.lua').write_text(lua, encoding='utf-8')
    (args.out / 'report.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    preview.save(args.out / 'preview.png')
    print(json.dumps(metadata))


if __name__ == '__main__':
    main()
