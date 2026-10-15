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


POOL_REVISION = "d0ba9c0053467d00dd55449c00a4e87c1632e601"
POOL_SOURCE = "a789b12567f25948a2f64e340ec29de7ee79980dda70ab995d4ba7807898997d"


def verify_legacy(directory, revision=REVISION):
    data = subprocess.check_output(['git', 'archive', revision, 'src', 'tools'], cwd=ROOT)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            archive.extractall(root, filter='data')
        subprocess.run([sys.executable, '-c', "import sys;sys.path.insert(0,'tools');from check_project import check;check(sys.argv[1])", str(Path(directory).resolve())],
                       cwd=root, env=dict(os.environ, PYTHONPATH=str(root / 'src')), check=True)
    print(f'Historical data verified using immutable {revision[:7]} source; not measurements of the current timing implementation.')
