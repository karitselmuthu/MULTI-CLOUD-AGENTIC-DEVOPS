# Optional context cache

`RedisContextCache` namespaces keys by tenant and always sets a bounded TTL. It holds disposable context only; approvals and workflow state remain in PostgreSQL/Temporal. The current test uses an injected fake client. A connected Redis deployment still needs authenticated transport, eviction settings and tenant-aware access controls.

Source: [redis-py client guide](https://redis.io/docs/latest/develop/clients/redis-py/).
