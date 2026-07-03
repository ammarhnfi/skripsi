import sys, re
sys.stdout.reconfigure(encoding='utf-8')

path = r'd:\Skripsi\my\Presentation\sidang_skripsi.html'
with open(path, encoding='utf-8') as f:
    content = f.read()

original = content

# 1. Topbar: fix to px so not affected by 200% base
content = content.replace(
    '.tb-title{font-size:.85rem;font-weight:700;opacity:.95;}',
    '.tb-title{font-size:16px;font-weight:700;opacity:.95;}'
)
content = content.replace(
    '.tb-sub{font-size:.75rem;opacity:.65;margin-top:1px;}',
    '.tb-sub{font-size:12px;opacity:.65;margin-top:1px;}'
)

# 2. For slides 11, 27, 32: scale inline em values by 0.65
# Extract slide boundaries
def slide_range(html, idx):
    start = html.find(f'data-idx="{idx}"')
    end = html.find('data-idx="', start + 10)
    return start, end

def scale_em(match):
    val = float(match.group(1))
    new_val = round(val * 0.65, 2)
    return f'font-size:{new_val}em'

for idx in [11, 27, 32]:
    s, e = slide_range(content, idx)
    if s == -1:
        print(f'WARN: slide {idx} not found')
        continue
    segment = content[s:e]
    new_seg = re.sub(r'font-size:(0?\.\d+)em', scale_em, segment)
    changed = sum(1 for a,b in zip(segment.splitlines(), new_seg.splitlines()) if a!=b)
    content = content[:s] + new_seg + content[e:]
    print(f'  Slide {idx}: {changed} line(s) changed')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print(f'Done.')
