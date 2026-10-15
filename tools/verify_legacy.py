"""Validate retained schema-2 data with its immutable producing revision's verifier."""
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

REVISION = 'c91bfef7ccbe50d77cb7bbda59cd4b8281ecccb4'
SOURCE = 'c9ce5eb5bf600d003eb9b734525d3211e268faf66160d767c543b1783396ce56'
ROOT = Path(__file__).resolve().parents[1]


def verify_legacy(directory):
    data = subprocess.check_output(['git', 'archive', REVISION, 'src', 'tools'], cwd=ROOT)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            archive.extractall(root, filter='data')
        subprocess.run([sys.executable, '-c', "import sys;sys.path.insert(0,'tools');from check_project import check;check(sys.argv[1])", str(Path(directory).resolve())],
                       cwd=root, env=dict(os.environ, PYTHONPATH=str(root / 'src')), check=True)
    print('Historical schema-2 data verified using immutable c91bfef source; not measurements of the current pool implementation.')
