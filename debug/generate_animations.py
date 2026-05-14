import os
import re
from PIL import Image

def generate_gifs(src_root, dest_folder):
    """
    Finds sequences of images like 'name_YEAR.png' and creates GIFs.
    """
    if not os.path.exists(src_root):
        return
    
    # We walk through root, scenario1, scenario2
    for root, dirs, files in os.walk(src_root):
        # Group files by base name (removing the year part)
        # Pattern: anything_YEAR.png or anything_YEARxYEAR.png
        groups = {}
        for f in files:
            if not f.endswith('.png'): continue
            
            # Match name_YEAR.png
            match = re.search(r'^(.*?)(?:_|\s)(\d{4})\.png$', f)
            if match:
                base = match.group(1)
                year = int(match.group(2))
                if base not in groups: groups[base] = []
                groups[base].append({'year': year, 'file': os.path.join(root, f)})
            else:
                # Match name_YEARxYEAR.png (for transition maps)
                match_trans = re.search(r'^(.*?)(?:_|\s)(\d{4})x(\d{4})\.png$', f)
                if match_trans:
                    base = match_trans.group(1)
                    year = int(match_trans.group(2)) # use the first year for sorting
                    if base not in groups: groups[base] = []
                    groups[base].append({'year': year, 'file': os.path.join(root, f)})

        # For each group with > 1 image, create a GIF
        for base, items in groups.items():
            if len(items) <= 1: continue
            
            # Sort by year
            items.sort(key=lambda x: x['year'])
            
            images = []
            for item in items:
                img = Image.open(item['file'])
                images.append(img.convert('RGB')) # PIL GIF works best with RGB/P
            
            if not images: continue
            
            # Output name: base_animation.gif in the same directory
            gif_name = f"{base}_animation.gif"
            gif_path = os.path.join(root, gif_name)
            
            # Save GIF
            images[0].save(
                gif_path,
                save_all=True,
                append_images=images[1:],
                duration=800, # 800ms per frame
                loop=0
            )
            print(f"  [GIF] Created: {gif_path} ({len(images)} frames)")

if __name__ == "__main__":
    roots = [
        r"d:\Skripsi\my\output_real",
        r"d:\Skripsi\my\output_sample"
    ]
    
    print("=== Generating Animations (GIF) ===")
    for r in roots:
        print(f"Processing {r}...")
        generate_gifs(r, r)
    print("=== Done ===")
