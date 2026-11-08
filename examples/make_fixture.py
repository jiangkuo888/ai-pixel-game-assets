"""Create a synthetic registration fixture, not an AI-generated art sample."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


def create_fixture(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    image = Image.new('RGBA', (32, 32))
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 5, 19, 10), fill='#514133')
    draw.rectangle((13, 6, 18, 9), fill='#e4c88e')
    draw.rectangle((10, 11, 21, 14), fill='#302f2d')
    draw.rectangle((7, 15, 24, 25), fill='#302f2d')
    draw.rectangle((9, 17, 22, 25), fill='#9d446e')
    draw.rectangle((10, 26, 21, 27), fill='#302f2d')
    image.resize((640, 640), Image.Resampling.NEAREST).save(output/'potion-source.png')
    contract = {
        'version': 1,
        'project': {'tile_pixels': 32, 'world_pixels_per_unit': 32, 'display_scale': 3},
        'families': {'pickup': {
            'canvas': [32, 32], 'alpha': 'binary', 'colors': 'preserve',
            'bbox_size': {'min': [8, 8], 'max': [26, 28]},
            'anchors': {'ground': [16, 28]}, 'anchor_tolerance': 0.5,
        }},
        'assets': [{
            'id': 'potion', 'family': 'pickup', 'source': 'potion-source.png',
            'expected_source_size': [640, 640], 'source_anchors': {'ground': [320, 560]},
        }],
    }
    (output/'pixel-assets.json').write_text(json.dumps(contract, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='New fixture directory')
    create_fixture(parser.parse_args().out)
