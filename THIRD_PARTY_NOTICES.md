# Third-party materials and license status

The workload uses procedurally generated synthetic numeric tensors; no external model weights, dataset or sibling project's source files are included.

NumPy and psutil are installed dependencies, not vendored source. They retain their upstream licenses: [NumPy license](https://github.com/numpy/numpy/blob/v1.26.4/LICENSE.txt) and [psutil license](https://github.com/giampaolo/psutil/blob/release-7.0.0/LICENSE). Python's standard-library multiprocessing facilities retain Python's license. Links in methodology are API/design references and do not transfer their projects' licenses to this implementation.

No license has been selected for original project contributions, including source, documentation, tests and measurement artifacts. Private GitHub visibility does not itself select an open-source license.

Local validation downloads upstream Colima/Lima tools and a Python container image; binaries and images are not committed or redistributed by this repository. Upstream licenses remain applicable: [Colima](https://github.com/abiosoft/colima/blob/v0.10.3/LICENSE), [Lima](https://github.com/lima-vm/lima/blob/v2.2.1/LICENSE), and [Python image](https://hub.docker.com/_/python). The installer reuses the separately installed Docker CLI. This does not change the original project license status above.
