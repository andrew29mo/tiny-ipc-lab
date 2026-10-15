# Third-party materials and licenses

Original Tiny IPC Lab contributions (source, documentation, tests and synthetic
measurement artifacts) are licensed under the [MIT License](LICENSE),
Copyright (c) 2026 Andrew Yuan. This grant does not replace third-party licenses.

The workload uses procedurally generated synthetic numeric tensors. No external
model weights, dataset or sibling project's implementation is included.

| Component | Purpose | Upstream license / notice |
|---|---|---|
| NumPy 1.26.4 | Installed runtime dependency | [BSD-3-Clause](https://github.com/numpy/numpy/blob/v1.26.4/LICENSE.txt) |
| psutil 7.0.0 | Installed runtime dependency | [BSD-3-Clause](https://github.com/giampaolo/psutil/blob/release-7.0.0/LICENSE) |
| setuptools 83.0.0 | Isolated build dependency | [MIT](https://github.com/pypa/setuptools/blob/v83.0.0/LICENSE) |
| Colima 0.10.3 | Downloaded local validation tool | [MIT](https://github.com/abiosoft/colima/blob/v0.10.3/LICENSE) |
| Lima 2.2.1 | Downloaded local validation tool | [Apache-2.0](https://github.com/lima-vm/lima/blob/v2.2.1/LICENSE) |

These components are installed/downloaded, not vendored source or binaries in
this repository. Their upstream copyright notices, conditions and disclaimers
remain applicable. NumPy wheels may bundle separately licensed libraries; their
bundled notices remain applicable as well. No dependency wheel or built container
image is redistributed by this repository.

Python and its standard-library multiprocessing facilities retain
[Python's license](https://docs.python.org/3.12/license.html). Local validation uses
the [official Python image](https://hub.docker.com/_/python) and its operating-system
packages under their respective upstream terms. The installer reuses the
separately installed Docker CLI; this project does not relicense Docker Desktop.
Links in methodology are API/design references, not grants to relicense those
projects. No original-project MIT statement applies to third-party components.

Historical review receipts identify immutable audited revisions. Their
`not-selected` license fields describe the state before the owner's later MIT
adoption; they are preserved as historical evidence, not current license metadata.
