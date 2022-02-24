import shutil
import os
try:
    shutil.rmtree('dist')
except Exception:
    pass
os.system("python3 -m build")
os.system("twine upload -u influxes -p JakeDaBoss00!? dist/*")