# Artifact storage adapters

`MinioArtifactStore` stores artifacts under `tenant/workflow/name` keys in an S3-compatible bucket and writes a SHA-256 metadata value. `LocalArtifactStore` is the deterministic filesystem test adapter. Both reject unsafe keys. A connected deployment must enforce the same tenant prefix with bucket policies and workload credentials; this application-level key check is not a replacement for storage authorization.

Source: [MinIO Python object API](https://docs.min.io/aistor/developers/sdk/python/api/#put_object).
