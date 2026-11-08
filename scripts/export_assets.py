"""Export already registered AI art to a shared logical pixel contract (Pillow)."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

from PIL import Image


def require(condition, message):
    if not condition:
        raise ValueError(message)


def positive_int(value):
    return type(value) is int and value > 0


def pair(value, label):
    require(isinstance(value, list) and len(value) == 2 and
            all(positive_int(v) for v in value), f'{label}: expected two positive integers')
    return tuple(value)


def point(value, label):
    require(isinstance(value, list) and len(value) == 2 and
            all(type(v) in (int, float) and math.isfinite(v) for v in value),
            f'{label}: expected two finite coordinates')
    return value


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pixels(image):
    # Pillow 12+ renamed this API; retain compatibility with older installs.
    if hasattr(image, 'get_flattened_data'):
        return image.get_flattened_data()
    return image.getdata()


def rgb_colors(image):
    return {p[:3] for p in pixels(image) if p[3] > 0}


def prepare(spec_path):
    spec = json.loads(spec_path.read_text(encoding='utf-8-sig'))
    require(spec.get('version') == 1, 'Expected contract version 1')
    zoom = spec.get('preview_scale', 8)
    require(positive_int(zoom) and zoom <= 32, 'preview_scale must be 1..32')
    require(isinstance(spec.get('families'), dict), 'families must be an object')
    require(isinstance(spec.get('assets'), list) and spec['assets'], 'assets must be nonempty')
    ids, groups, prepared = set(), {}, []
    for asset in spec['assets']:
        name = asset['id']
        require(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9_-]+', name), 'Invalid asset id')
        require(name not in ids, f'Duplicate id: {name}')
        ids.add(name)
        family_name = asset['family']
        require(family_name in spec['families'], f'{name}: unknown family')
        family = spec['families'][family_name]
        size = pair(family['canvas'], f'{name}.canvas')
        path = (spec_path.parent / asset['source']).resolve()
        with Image.open(path) as opened:
            require(opened.format == 'PNG', f'{name}: source must be PNG')
            original = opened.convert('RGBA')
        if 'expected_source_size' in asset:
            require(original.size == pair(asset['expected_source_size'], 'expected_source_size'),
                    f'{name}: source dimensions changed')
        rect = asset.get('source_rect', [0, 0, *original.size])
        require(isinstance(rect, list) and len(rect) == 4 and
                all(type(v) is int for v in rect), f'{name}: invalid source_rect')
        left, top, right, bottom = rect
        require(0 <= left < right <= original.width and 0 <= top < bottom <= original.height,
                f'{name}: source_rect outside source')
        width, height = right-left, bottom-top
        require(width*size[1] == height*size[0], f'{name}: aspect ratio mismatch; register source first')
        require(width >= size[0] and height >= size[1],
                f'{name}: source smaller than logical canvas; do not disguise upscaling as sampling')
        if 'group' in asset:
            group = asset['group']
            require(isinstance(group, str) and group, f'{name}: group must be a nonempty string')
            signature = (family_name, width, height, size)
            require(group not in groups or groups[group] == signature,
                    f'{name}: group transform mismatch')
            groups[group] = signature
        crop = original.crop(rect)
        sampled = crop.resize(size, Image.Resampling.NEAREST)
        input_rgb = rgb_colors(crop)
        require(rgb_colors(sampled) <= input_rgb, f'{name}: sampling introduced RGB colors')
        alpha_mode = family.get('alpha', 'binary')
        require(alpha_mode in ('binary', 'preserve'), f'{name}: unknown alpha mode')
        threshold = family.get('alpha_threshold')
        if threshold is not None:
            require(alpha_mode == 'binary' and positive_int(threshold) and threshold <= 255,
                    f'{name}: threshold requires binary alpha and value 1..255')
            sampled.putalpha(sampled.getchannel('A').point(lambda a: 255 if a >= threshold else 0))
        alpha_values = set(pixels(sampled.getchannel('A')))
        if alpha_mode == 'binary':
            require(alpha_values <= {0, 255}, f'{name}: semi-transparent sampled pixels; repair mask or specify threshold')
        color_mode = family.get('colors', 'preserve')
        require(color_mode in ('preserve', 'palette'), f'{name}: unknown color policy')
        before_palette = len(rgb_colors(sampled))
        if color_mode == 'palette':
            palette = family.get('palette')
            require(isinstance(palette, list) and palette and
                    all(isinstance(c, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', c) for c in palette),
                    f'{name}: palette must contain #RRGGBB colors')
            palette = [tuple(bytes.fromhex(c[1:])) for c in palette]
            remap = {c: min(palette, key=lambda p: sum((a-b)**2 for a, b in zip(c, p)))
                     for c in rgb_colors(sampled)}
            sampled.putdata([(*remap[p[:3]], p[3]) if p[3] else p for p in pixels(sampled)])
            require(rgb_colors(sampled) <= set(palette), f'{name}: palette violation')
        else:
            require(rgb_colors(sampled) <= input_rgb, f'{name}: preserve RGB violation')
        colors = len(rgb_colors(sampled))
        if 'max_colors' in family:
            limit = family['max_colors']
            require(positive_int(limit) and colors <= limit, f'{name}: color budget exceeded or invalid')
        bbox = sampled.getchannel('A').getbbox()
        allow_empty = family.get('allow_empty', False)
        require(type(allow_empty) is bool, f'{name}: allow_empty must be boolean')
        require(bbox or allow_empty, f'{name}: empty sprite')
        bbox_size = [bbox[2]-bbox[0], bbox[3]-bbox[1]] if bbox else [0, 0]
        if bbox and 'bbox_size' in family:
            bounds = family['bbox_size']
            lower = pair(bounds.get('min', [1, 1]), 'bbox min')
            upper = pair(bounds.get('max', list(size)), 'bbox max')
            require(all(a <= v <= b for a, v, b in zip(lower, bbox_size, upper)),
                    f'{name}: subject bbox size outside contract')
        tolerance = family.get('anchor_tolerance', 0.5)
        require(type(tolerance) in (int, float) and math.isfinite(tolerance) and tolerance >= 0,
                f'{name}: invalid anchor_tolerance')
        mapped = {}
        for key, destination in family.get('anchors', {}).items():
            destination = point(destination, f'{name}.{key}.target')
            require(key in asset.get('source_anchors', {}), f'{name}: missing source anchor {key}')
            source_point = point(asset['source_anchors'][key], f'{name}.{key}.source')
            mapped[key] = [(source_point[0]-left)*size[0]/width,
                           (source_point[1]-top)*size[1]/height]
            require(all(abs(a-b) <= tolerance for a, b in zip(mapped[key], destination)),
                    f'{name}: anchor mismatch: {key}')
        record = {
            'id': name, 'family': family_name, 'group': asset.get('group'),
            'source': str(path), 'source_sha256': digest(path), 'source_size': list(original.size),
            'source_rect': rect, 'canvas': list(size), 'source_pixels_per_logical_pixel': width/size[0],
            'transform': {'scale': size[0]/width, 'translation': [-left*size[0]/width, -top*size[1]/height]},
            'sampling': 'nearest', 'colors_policy': color_mode, 'colors_before_palette': before_palette,
            'colors': colors, 'alpha_policy': alpha_mode, 'alpha_threshold': threshold,
            'alpha_values': sorted(alpha_values), 'bbox': bbox, 'bbox_size': bbox_size, 'anchors': mapped,
            'review': {'automatic_contract': 'passed', 'visual': 'not_run', 'in_game': 'not_run'},
        }
        prepared.append((sampled, record))
    return spec, zoom, prepared


def export(spec_path, output):
    spec_path, output = Path(spec_path).resolve(), Path(output).resolve()
    require(not output.exists(), f'Output already exists: {output}')
    spec, zoom, prepared = prepare(spec_path)
    output.mkdir(parents=True, exist_ok=False)
    (output/'previews').mkdir()
    records = []
    for image, record in prepared:
        name = record['id']
        target = output/f'{name}.png'
        image.save(target)
        preview = f'previews/{name}@{zoom}x.png'
        image.resize((image.width*zoom, image.height*zoom), Image.Resampling.NEAREST).save(output/preview)
        record.update(file=target.name, sha256=digest(target), preview=preview)
        records.append(record)
    manifest = {'contract': spec, 'contract_sha256': digest(spec_path), 'assets': records,
                'limitations': 'Automated checks do not verify visual pixel density, layers, animation, tile seams or runtime rendering.'}
    (output/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True, help='Contract JSON; source paths relative to it')
    parser.add_argument('--out', type=Path, required=True, help='New output directory, must not exist')
    args = parser.parse_args()
    try:
        manifest = export(args.spec, args.out)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, f'Export failed: {error}\n')
    print(f'Exported {len(manifest["assets"])} assets. Visual and in-game review pending.')


if __name__ == '__main__':
    main()
