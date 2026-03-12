import os
import glob

directory = r"d:\Skripsi\my"
tex_files = glob.glob(os.path.join(directory, "*.tex"))

for file in tex_files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "huggingface4/" in content:
        new_content = content.replace("huggingface4/", "huggingface/")
        with open(file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Replaced 'huggingface4/' in {os.path.basename(file)}")
