# Security scope

This is a local experiment for trusted code and synthetic data. It opens no network service. Multiprocessing control messages are Python objects on private parent/child Pipes; this is not an untrusted-input serialization interface. Shared-memory names/permissions are not tenant isolation or a security boundary against local peers.

The controller owns normal and worker-failure cleanup, but arbitrary controller termination or machine failure is outside its guarantee. Do not use this MVP as a production shared-memory allocator or a crash-proof persistence mechanism.

Reports collect CPU/OS/runtime provenance, synthetic checksums and measurements, plus a whitelist of allocator/thread runtime options; they do not collect hostname, user names, arbitrary environment variables or credentials. Keep local inputs, environments, personal instructions and runtime logs out of Git. The tracked-file scanner is heuristic, not a comprehensive secret detector. CI tokens are read-only; pinned official Actions do not receive project secrets.
