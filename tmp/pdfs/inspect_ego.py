import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'ego-tools'))
import hashlib
import json
import fitz
from pypdf import PdfReader
from PIL import Image, ImageDraw, ImageFont

root = Path('D:/my-website/static/产品使用手册/使用手册/视觉套件/VINS-ROS-EGO')
output = Path('D:/my-website/tmp/pdfs/ego-inspection')
output.mkdir(parents=True, exist_ok=True)
pdf_path = next(root.glob('*.pdf'))
reader = PdfReader(pdf_path)
texts = []
for number, page in enumerate(reader.pages, 1):
    texts.append(f'\n===== PAGE {number} =====\n' + (page.extract_text() or ''))
    for annot in page.get('/Annots', []):
        a = annot.get_object()
        if a.get('/A', {}).get('/URI'):
            texts.append('LINK: ' + str(a['/A']['/URI']))
(output / 'source.txt').write_text('\n'.join(texts), encoding='utf-8')
doc = fitz.open(pdf_path)
for number, page in enumerate(doc, 1):
    pix = page.get_pixmap(matrix=fitz.Matrix(1.25, 1.25))
    pix.save(str(output / f'page-{number:02}.png'))
files = sorted(root.glob('*.png'), key=lambda p: int(p.stem.split('(')[1].rstrip(')')) + 1 if '(' in p.stem else 0)
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 20)
records = []
for idx, path in enumerate(files):
    with Image.open(path) as im:
        rgb = im.convert('RGB')
        rec = {'file': path.name, 'size': list(im.size), 'pixels_sha256': hashlib.sha256(rgb.tobytes()).hexdigest()}
        small = rgb.resize((32, 32)).convert('L')
        rec['tiny'] = list(small.getdata())
        records.append(rec)
for start in range(0, len(files), 12):
    sheet = Image.new('RGB', (1200, 1120), 'white')
    draw = ImageDraw.Draw(sheet)
    for offset, path in enumerate(files[start:start+12]):
        x, y = (offset % 3) * 400, (offset // 3) * 280
        with Image.open(path) as im:
            im.thumbnail((390, 245))
            sheet.paste(im, (x, y + 30))
        draw.text((x + 5, y + 3), f'Image {start+offset}: {records[start+offset]["size"]}', fill='black', font=font)
    sheet.save(output / f'assets-{start//12+1}.jpg')
pairs = []
for i, a in enumerate(records):
    for b in records[i+1:]:
        diff = sum(abs(x-y) for x,y in zip(a['tiny'], b['tiny'])) / 1024
        if diff < 12:
            pairs.append({'a': a['file'], 'b': b['file'], 'diff': diff, 'identical_pixels': a['size'] == b['size'] and a['pixels_sha256'] == b['pixels_sha256']})
for r in records:
    del r['tiny']
(output / 'assets.json').write_text(json.dumps({'images': records, 'similar_pairs': pairs}, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'pages': len(doc), 'images': len(files), 'similar_pairs': pairs}, ensure_ascii=False, indent=2))
