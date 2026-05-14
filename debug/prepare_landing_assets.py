import os
import json
import shutil

folders = [
    {"src": r"d:\Skripsi\my\output_real", "dest": r"d:\Skripsi\my\landing-page\public\output_real", "manifest": r"d:\Skripsi\my\landing-page\public\output_real_manifest.json"},
    {"src": r"d:\Skripsi\my\output_sample", "dest": r"d:\Skripsi\my\landing-page\public\output_sample", "manifest": r"d:\Skripsi\my\landing-page\public\output_sample_manifest.json"}
]

# Grouping logic
def get_group(fname):
    if fname.startswith('compare_'): return 'Perbandingan Bersandingan'
    if fname.startswith('biplot_tahun'): return 'Snapshot Biplot'
    if fname.startswith('boxplot'): return 'Distribusi Variabel'
    if fname.startswith('cluster_biplot') or fname.startswith('cluster_scatter'): return 'Biplot Klaster'
    if fname.startswith('cluster_map'): return 'Peta Klaster'
    if fname.startswith('dendrogram'): return 'Dendrogram'
    if fname.startswith('elbow_plot'): return 'Elbow Plot'
    if fname.startswith('output_table'): return 'Tabel Hasil (.tex)'
    if fname in ['compromise_map.png', 'loading_plot.png', 'rv_heatmap.png', 'scree_plot.png', 'statis_trajectories.png', 'variable_contribution.png', 'variable_cos2.png', 'permutation_histogram.png']:
        return 'Hasil Utama STATIS'
    return 'Lain-lain'

total_copied = 0
for folder in folders:
    dest_root = folder['dest']
    if not os.path.exists(dest_root):
        os.makedirs(dest_root)
        
    src_root = folder['src']
    if not os.path.exists(src_root):
        continue
        
    manifest = []
    
    for root, dirs, files in os.walk(src_root):
        # Calculate relative path to src_root
        rel_path = os.path.relpath(root, src_root)
        
        # Determine scenario
        scenario = 'Shared'
        if 'scenario1' in root.lower():
            scenario = 'Scenario 1'
        elif 'scenario2' in root.lower():
            scenario = 'Scenario 2'
            
        for f in files:
            if f == 'OUTPUT_APP.md': continue
            src_f = os.path.join(root, f)
            
            # Create subfolder in dest if needed
            dest_f_dir = os.path.join(dest_root, rel_path) if rel_path != '.' else dest_root
            if not os.path.exists(dest_f_dir):
                os.makedirs(dest_f_dir)
            
            dest_f = os.path.join(dest_f_dir, f)
            
            ftype = 'image' if f.endswith('.png') else 'text' if f.endswith('.tex') else 'other'
            folder_name = os.path.basename(dest_root)
            
            # URL path for the frontend
            url_path = f'/{folder_name}/{f}'
            if rel_path != '.':
                url_path = f'/{folder_name}/{rel_path.replace("\\", "/")}/{f}'
            
            manifest.append({
                'name': f,
                'caption': f.replace('_', ' ').replace('.png', '').replace('.tex', '').title(),
                'type': ftype,
                'src': url_path,
                'group': get_group(f),
                'scenario': scenario
            })
            shutil.copy2(src_f, dest_f)
            total_copied += 1
            
    manifest.sort(key=lambda x: (x['scenario'], x['group'], x['caption']))
    with open(folder['manifest'], "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2)

from datetime import datetime
import locale

# Set locale for Indonesian day names if possible (safe fallback provided)
try:
    locale.setlocale(locale.LC_TIME, 'id_ID.utf8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'Indonesian_Indonesia.1252')
    except:
        pass

# Generate Last Update timestamp
now = datetime.now()
timestamp_str = now.strftime("%A, %d %B %Y %H:%M:%S") + " WIB"
update_info_path = r"d:\Skripsi\my\landing-page\public\last_update.json"

with open(update_info_path, "w", encoding="utf-8") as f:
    json.dump({"lastUpdate": timestamp_str}, f, indent=2)

print(f"Copied {total_copied} files and generated multiple manifests + last_update.json.")
