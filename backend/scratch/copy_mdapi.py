import os
import shutil

dest_dir = r"app/services/mosdac_client"
os.makedirs(dest_dir, exist_ok=True)
src_file = r"scratch/mdapi_official/mdapi.py"
dest_file = os.path.join(dest_dir, "mdapi.py")
shutil.copyfile(src_file, dest_file)

with open(os.path.join(dest_dir, "__init__.py"), "w", encoding="utf-8") as f:
    f.write('"""Official MOSDAC Data Download API client package."""\n')

print("Copied to:", dest_file, "size:", os.path.getsize(dest_file))
