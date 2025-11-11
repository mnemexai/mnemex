# CortexGraph SaaS Scaling Strategy

## Executive Summary

CortexGraph is currently architected as a **single-user, local-first MCP server** with file-based storage. To transform it into a **production SaaS platform**, significant architectural changes are required across infrastructure, data persistence, authentication, multi-tenancy, and API design.

This document provides a comprehensive roadmap for scaling CortexGraph from a local tool to a cloud-hosted, multi-tenant SaaS offering.

---

## Current Architecture Analysis

### Strengths
- ✅ **Sophisticated memory algorithm**: Temporal decay with power-law, exponential, and two-component models
- ✅ **Clean code architecture**: Well-separated layers (tools, core, storage)
- ✅ **Strong test coverage potential**: 98%+ coverage from mnemex heritage
- ✅ **MCP protocol**: Modern standard for AI tool integration
- ✅ **Git-friendly storage**: JSONL format is human-readable and versionable
- ✅ **Security conscious**: File permissions, input validation, path traversal prevention

### Limitations for SaaS

| Component | Current State | SaaS Requirement | Gap |
|-----------|--------------|------------------|-----|
| **Storage** | JSONL files | Scalable database | **Critical** |
| **Authentication** | File permissions | JWT/OAuth2 | **Critical** |
| **Authorization** | Single user | RBAC/ABAC | **Critical** |
| **Multi-tenancy** | None | Tenant isolation | **Critical** |
| **API** | MCP only | REST/GraphQL + MCP | **High** |
| **Deployment** | Local CLI | Cloud containers | **High** |
| **Monitoring** | Basic logging | APM, metrics | **High** |
| **Scalability** | Single process | Horizontal scaling | **High** |
| **Data backup** | Git commits | Cloud backups | **Medium** |
| **Billing** | None | Usage-based metering | **Medium** |

---

## Phase 1: Foundation (0-3 months)

### 1.1 Database Migration

**Current**: JSONL files with in-memory indexes
**Target**: PostgreSQL with proper indexing

#### Implementation Strategy

```python
# New database schema
CREATE TABLE tenants (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    plan VARCHAR(50) NOT NULL,  -- free, pro, enterprise
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    settings JSONB,  -- tenant-specific config
    status VARCHAR(20) NOT NULL DEFAULT 'active'
);

CREATE TABLE users (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',  -- admin, user, readonly
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
);

CREATE TABLE memories (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    tags TEXT[] NOT NULL DEFAULT '{}',
    entities TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_used TIMESTAMP NOT NULL DEFAULT NOW(),
    use_count INTEGER NOT NULL DEFAULT 0,
    strength FLOAT NOT NULL DEFAULT 1.0,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    promoted_at TIMESTAMP,
    promoted_to VARCHAR(255),
    embedding vector(384),  -- pgvector extension for semantic search
    review_priority FLOAT NOT NULL DEFAULT 0.0,
    last_review_at TIMESTAMP,
    review_count INTEGER NOT NULL DEFAULT 0,
    cross_domain_count INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT valid_strength CHECK (strength >= 0 AND strength <= 2.0),
    CONSTRAINT valid_priority CHECK (review_priority >= 0 AND review_priority <= 1.0)
);

CREATE TABLE relations (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    relation_type VARCHAR(50) NOT NULL,
    strength FLOAT NOT NULL DEFAULT 1.0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Critical indexes for performance
CREATE INDEX idx_memories_tenant_status ON memories(tenant_id, status);
CREATE INDEX idx_memories_tenant_user ON memories(tenant_id, user_id);
CREATE INDEX idx_memories_tags ON memories USING GIN(tags);
CREATE INDEX idx_memories_entities ON memories USING GIN(entities);
CREATE INDEX idx_memories_last_used ON memories(tenant_id, last_used DESC);
CREATE INDEX idx_memories_embedding ON memories USING ivfflat(embedding vector_cosine_ops);
CREATE INDEX idx_relations_source ON relations(source_id);
CREATE INDEX idx_relations_target ON relations(target_id);
```

#### Migration Path

1. **Create database abstraction layer**:
   ```python
   # src/cortexgraph/storage/database.py
   from abc import ABC, abstractmethod

   class StorageBackend(ABC):
       @abstractmethod
       async def save_memory(self, memory: Memory) -> str:
           pass

       @abstractmethod
       async def get_memory(self, memory_id: str) -> Memory | None:
           pass

       @abstractmethod
       async def search_memories(self, filters: dict) -> list[Memory]:
           pass

   class JSONLStorage(StorageBackend):
       # Current implementation
       pass

   class PostgreSQLStorage(StorageBackend):
       # New implementation using asyncpg or SQLAlchemy
       pass
   ```

2. **Implement dual-write mode** for safe migration:
   - Write to both JSONL and PostgreSQL
   - Read from PostgreSQL, fallback to JSONL
   - Validate consistency between stores
   - Monitor for 1-2 weeks before cutover

3. **Migration CLI tool**:
   ```bash
   cortexgraph-migrate-db --from jsonl --to postgresql --validate
   ```

#### Technology Choices

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **PostgreSQL** | ACID, JSON support, pgvector, proven | Heavier weight | ✅ **Recommended** |
| **MongoDB** | Flexible schema, good for JSONL-like | No joins, consistency | ⚠️ Consider for docs |
| **Supabase** | PostgreSQL + Auth + APIs | Vendor lock-in | ✅ **Good for MVP** |

**Recommendation**: **PostgreSQL with pgvector extension**
- Native vector support for embeddings
- ACID guarantees for memory consistency
- JSON/JSONB for flexible metadata
- Mature ecosystem and tooling

### 1.2 Authentication & Authorization

**Current**: None (file permissions only)
**Target**: JWT-based auth with RBAC

#### Implementation

```python
# src/cortexgraph/auth/jwt.py
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

class AuthService:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def create_access_token(
        self,
        user_id: str,
        tenant_id: str,
        expires_delta: timedelta = timedelta(hours=24)
    ) -> str:
        payload = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "exp": datetime.utcnow() + expires_delta,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            raise AuthenticationError("Invalid token")

    def hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return self.pwd_context.verify(plain, hashed)

# Middleware for FastAPI
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> dict:
    try:
        payload = auth_service.verify_token(credentials.credentials)
        return {
            "user_id": payload["sub"],
            "tenant_id": payload["tenant_id"],
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
```

#### RBAC Model

```python
# src/cortexgraph/auth/permissions.py
from enum import Enum

class Permission(str, Enum):
    MEMORY_CREATE = "memory:create"
    MEMORY_READ = "memory:read"
    MEMORY_UPDATE = "memory:update"
    MEMORY_DELETE = "memory:delete"
    MEMORY_PROMOTE = "memory:promote"
    ADMIN_USERS = "admin:users"
    ADMIN_SETTINGS = "admin:settings"

class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"

ROLE_PERMISSIONS = {
    Role.ADMIN: [p for p in Permission],
    Role.USER: [
        Permission.MEMORY_CREATE,
        Permission.MEMORY_READ,
        Permission.MEMORY_UPDATE,
        Permission.MEMORY_DELETE,
        Permission.MEMORY_PROMOTE,
    ],
    Role.READONLY: [
        Permission.MEMORY_READ,
    ],
}

def check_permission(user_role: Role, required_permission: Permission) -> bool:
    return required_permission in ROLE_PERMISSIONS.get(user_role, [])
```

### 1.3 Multi-Tenancy Architecture

**Pattern**: **Row-level tenant isolation** (single database, tenant_id in every table)

#### Implementation Strategy

```python
# src/cortexgraph/middleware/tenant.py
from contextvars import ContextVar
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

# Thread-safe context for current tenant
current_tenant: ContextVar[str] = ContextVar("current_tenant", default=None)
current_user: ContextVar[str] = ContextVar("current_user", default=None)

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract tenant from JWT claims
        user_data = request.state.user  # Set by auth middleware
        tenant_id = user_data.get("tenant_id")
        user_id = user_data.get("user_id")

        if not tenant_id:
            raise HTTPException(status_code=403, detail="No tenant context")

        # Set context variables
        current_tenant.set(tenant_id)
        current_user.set(user_id)

        try:
            response = await call_next(request)
            return response
        finally:
            current_tenant.set(None)
            current_user.set(None)

# Storage layer automatically filters by tenant
class PostgreSQLStorage(StorageBackend):
    async def search_memories(self, filters: dict) -> list[Memory]:
        tenant_id = current_tenant.get()
        if not tenant_id:
            raise SecurityError("No tenant context")

        query = """
            SELECT * FROM memories
            WHERE tenant_id = $1
            AND status = $2
            ORDER BY last_used DESC
            LIMIT $3
        """
        # Always filter by tenant_id
        rows = await self.pool.fetch(query, tenant_id, filters.get("status"), filters.get("limit", 50))
        return [Memory.from_db_row(row) for row in rows]
```

#### Data Isolation Strategies

| Strategy | Isolation | Complexity | Cost | Recommendation |
|----------|-----------|------------|------|----------------|
| **Shared DB, Shared Schema** | Row-level | Low | Low | ✅ **Phase 1** |
| **Shared DB, Schema per Tenant** | Schema-level | Medium | Low | ⚠️ Phase 2+ |
| **Database per Tenant** | Complete | High | High | ❌ Overkill |

**Recommendation**: Start with **row-level isolation** with strict query-level tenant filtering.

---

## Phase 2: API & Service Layer (3-6 months)

### 2.1 REST API with FastAPI

**Current**: MCP server only
**Target**: REST API + MCP server (dual interface)

#### API Structure

```python
# src/cortexgraph/api/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="CortexGraph API",
    version="2.0.0",
    description="Temporal memory management for AI assistants"
)

# CORS for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.cortexgraph.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}

# Memory endpoints
@app.post("/api/v1/memories", response_model=MemoryResponse)
async def create_memory(
    data: CreateMemoryRequest,
    user: dict = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage)
):
    """Save a new memory."""
    memory = Memory(
        id=str(uuid.uuid4()),
        content=data.content,
        meta=MemoryMetadata(tags=data.tags),
        tenant_id=user["tenant_id"],
        user_id=user["user_id"],
    )
    await storage.save_memory(memory)
    return MemoryResponse.from_memory(memory)

@app.get("/api/v1/memories", response_model=list[MemoryResponse])
async def search_memories(
    query: str | None = None,
    tags: list[str] | None = Query(None),
    limit: int = Query(50, le=100),
    user: dict = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage)
):
    """Search memories with filters."""
    filters = {
        "query": query,
        "tags": tags,
        "limit": limit,
        "status": "active",
    }
    memories = await storage.search_memories(filters)
    return [MemoryResponse.from_memory(m) for m in memories]

@app.get("/api/v1/memories/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: str,
    user: dict = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage)
):
    """Get a specific memory by ID."""
    memory = await storage.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    # Verify tenant ownership
    if memory.tenant_id != user["tenant_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return MemoryResponse.from_memory(memory)

@app.post("/api/v1/memories/{memory_id}/touch")
async def touch_memory(
    memory_id: str,
    user: dict = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage)
):
    """Reinforce a memory (update last_used, increment use_count)."""
    # Implementation
    pass

@app.post("/api/v1/memories/gc")
async def garbage_collect(
    dry_run: bool = Query(False),
    user: dict = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage)
):
    """Run garbage collection on low-scoring memories."""
    # Implementation
    pass
```

#### API Versioning Strategy

- **URL versioning**: `/api/v1/`, `/api/v2/`
- **Deprecation policy**: 6 months notice before removal
- **Header-based version selection** (optional): `X-API-Version: 2.0`

### 2.2 WebSocket Support for Real-Time Updates

```python
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, tenant_id: str, websocket: WebSocket):
        await websocket.accept()
        if tenant_id not in self.active_connections:
            self.active_connections[tenant_id] = []
        self.active_connections[tenant_id].append(websocket)

    async def disconnect(self, tenant_id: str, websocket: WebSocket):
        self.active_connections[tenant_id].remove(websocket)

    async def broadcast_to_tenant(self, tenant_id: str, message: dict):
        for connection in self.active_connections.get(tenant_id, []):
            await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/memories")
async def websocket_endpoint(websocket: WebSocket, token: str):
    # Authenticate
    user = await authenticate_websocket(token)
    tenant_id = user["tenant_id"]

    await manager.connect(tenant_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages
    except WebSocketDisconnect:
        manager.disconnect(tenant_id, websocket)
```

### 2.3 GraphQL API (Optional, for complex queries)

```python
# src/cortexgraph/api/graphql.py
import strawberry
from strawberry.fastapi import GraphQLRouter

@strawberry.type
class Memory:
    id: str
    content: str
    tags: list[str]
    created_at: int
    last_used: int
    use_count: int
    strength: float

@strawberry.type
class Query:
    @strawberry.field
    async def memory(self, id: str, info: strawberry.Info) -> Memory | None:
        user = info.context["user"]
        # Implementation
        pass

    @strawberry.field
    async def search_memories(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
        info: strawberry.Info = None
    ) -> list[Memory]:
        user = info.context["user"]
        # Implementation
        pass

schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")
```

---

## Phase 3: Infrastructure & DevOps (6-9 months)

### 3.1 Container Architecture

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY pyproject.toml .

# Install application
RUN pip install -e .

# Non-root user
RUN useradd -m -u 1000 cortex
USER cortex

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "cortexgraph.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_USER: cortexgraph
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: cortexgraph_prod
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build: .
    environment:
      DATABASE_URL: postgresql://cortexgraph:${DB_PASSWORD}@postgres:5432/cortexgraph_prod
      REDIS_URL: redis://redis:6379
      JWT_SECRET: ${JWT_SECRET}
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 512M

  worker:
    build: .
    command: celery -A cortexgraph.tasks worker --loglevel=info
    environment:
      DATABASE_URL: postgresql://cortexgraph:${DB_PASSWORD}@postgres:5432/cortexgraph_prod
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
```

### 3.2 Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cortexgraph-api
  namespace: production
spec:
  replicas: 5
  selector:
    matchLabels:
      app: cortexgraph-api
  template:
    metadata:
      labels:
        app: cortexgraph-api
    spec:
      containers:
      - name: api
        image: cortexgraph/api:2.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: cortexgraph-secrets
              key: database-url
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: cortexgraph-secrets
              key: jwt-secret
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: cortexgraph-api
  namespace: production
spec:
  selector:
    app: cortexgraph-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: cortexgraph-api-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cortexgraph-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 3.3 Monitoring & Observability

```python
# src/cortexgraph/observability/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
memory_operations = Counter(
    'cortexgraph_memory_operations_total',
    'Total memory operations',
    ['operation', 'status', 'tenant_id']
)

memory_search_duration = Histogram(
    'cortexgraph_memory_search_duration_seconds',
    'Memory search duration',
    ['tenant_id'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

active_memories = Gauge(
    'cortexgraph_active_memories',
    'Number of active memories',
    ['tenant_id']
)

# Usage
async def search_memories_with_metrics(filters: dict):
    tenant_id = current_tenant.get()
    start = time.time()

    try:
        memories = await storage.search_memories(filters)
        memory_operations.labels(
            operation='search',
            status='success',
            tenant_id=tenant_id
        ).inc()
        return memories
    except Exception as e:
        memory_operations.labels(
            operation='search',
            status='error',
            tenant_id=tenant_id
        ).inc()
        raise
    finally:
        duration = time.time() - start
        memory_search_duration.labels(tenant_id=tenant_id).observe(duration)
```

```python
# src/cortexgraph/observability/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Setup OpenTelemetry
trace.set_tracer_provider(TracerProvider())
otlp_exporter = OTLPSpanExporter(endpoint="http://jaeger:4317")
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))

tracer = trace.get_tracer(__name__)

# Usage
async def search_memories(filters: dict):
    with tracer.start_as_current_span("search_memories") as span:
        span.set_attribute("tenant_id", current_tenant.get())
        span.set_attribute("filter.tags", str(filters.get("tags")))

        memories = await storage.search_memories(filters)
        span.set_attribute("result.count", len(memories))

        return memories
```

### 3.4 Caching Strategy

```python
# src/cortexgraph/cache/redis.py
import redis.asyncio as redis
import json
from typing import Any

class CacheService:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    async def get(self, key: str) -> Any | None:
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value: Any, ttl: int = 300):
        await self.redis.setex(key, ttl, json.dumps(value))

    async def invalidate_tenant(self, tenant_id: str):
        """Invalidate all cache keys for a tenant."""
        pattern = f"tenant:{tenant_id}:*"
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern)
            if keys:
                await self.redis.delete(*keys)
            if cursor == 0:
                break

# Usage in API
@app.get("/api/v1/memories")
async def search_memories(
    query: str | None = None,
    user: dict = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage),
    cache: CacheService = Depends(get_cache)
):
    tenant_id = user["tenant_id"]
    cache_key = f"tenant:{tenant_id}:search:{query}:{hash(str(filters))}"

    # Try cache first
    cached = await cache.get(cache_key)
    if cached:
        return cached

    # Query database
    memories = await storage.search_memories(filters)
    result = [MemoryResponse.from_memory(m) for m in memories]

    # Cache for 5 minutes
    await cache.set(cache_key, result, ttl=300)

    return result
```

---

## Phase 4: Advanced Features (9-12 months)

### 4.1 Background Job Processing

```python
# src/cortexgraph/tasks/celery.py
from celery import Celery

celery_app = Celery(
    'cortexgraph',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/1'
)

@celery_app.task
def garbage_collect_tenant(tenant_id: str):
    """Run GC for a specific tenant."""
    # Implementation
    pass

@celery_app.task
def promote_memories_batch(tenant_id: str):
    """Auto-promote memories that meet criteria."""
    # Implementation
    pass

@celery_app.task
def calculate_review_priorities(tenant_id: str):
    """Recalculate review priorities for all memories."""
    # Implementation
    pass

@celery_app.task
def generate_embeddings_batch(memory_ids: list[str]):
    """Generate embeddings for new memories."""
    # Implementation
    pass

# Schedule periodic tasks
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'gc-all-tenants': {
        'task': 'cortexgraph.tasks.gc_all_tenants',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    'promote-memories': {
        'task': 'cortexgraph.tasks.promote_all_tenants',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
    },
}
```

### 4.2 Webhook System

```python
# src/cortexgraph/webhooks/manager.py
import httpx
from typing import Literal

class WebhookManager:
    def __init__(self, storage: StorageBackend):
        self.storage = storage

    async def trigger_webhook(
        self,
        tenant_id: str,
        event: Literal["memory.created", "memory.promoted", "memory.deleted"],
        payload: dict
    ):
        """Send webhook to tenant's configured endpoints."""
        webhooks = await self.storage.get_tenant_webhooks(tenant_id, event)

        async with httpx.AsyncClient() as client:
            for webhook in webhooks:
                try:
                    response = await client.post(
                        webhook.url,
                        json={
                            "event": event,
                            "timestamp": int(time.time()),
                            "data": payload,
                        },
                        headers={
                            "X-CortexGraph-Signature": self._sign_payload(payload, webhook.secret),
                        },
                        timeout=10.0
                    )
                    response.raise_for_status()
                except Exception as e:
                    logger.error(f"Webhook failed for {webhook.url}: {e}")
                    # Store failed webhook for retry
                    await self.storage.save_failed_webhook(webhook.id, str(e))
```

### 4.3 Usage Metering & Billing

```python
# src/cortexgraph/billing/metering.py
from enum import Enum

class MetricType(str, Enum):
    MEMORY_CREATED = "memory_created"
    MEMORY_SEARCH = "memory_search"
    MEMORY_PROMOTED = "memory_promoted"
    STORAGE_GB = "storage_gb"
    API_REQUESTS = "api_requests"

class UsageTracker:
    def __init__(self, storage: StorageBackend):
        self.storage = storage

    async def track_usage(
        self,
        tenant_id: str,
        metric: MetricType,
        quantity: float = 1.0
    ):
        """Track usage metrics for billing."""
        await self.storage.increment_usage(
            tenant_id=tenant_id,
            metric=metric.value,
            quantity=quantity,
            timestamp=int(time.time())
        )

    async def get_current_usage(self, tenant_id: str, period: str = "month") -> dict:
        """Get usage for current billing period."""
        return await self.storage.get_usage_summary(tenant_id, period)

    async def check_quota(self, tenant_id: str, metric: MetricType) -> bool:
        """Check if tenant has exceeded quota."""
        plan = await self.storage.get_tenant_plan(tenant_id)
        current = await self.get_current_usage(tenant_id)

        quota = plan.limits.get(metric.value)
        if quota is None:
            return True  # Unlimited

        return current.get(metric.value, 0) < quota

# Middleware for API requests
async def track_api_usage(request: Request, call_next):
    response = await call_next(request)

    if hasattr(request.state, "user"):
        tenant_id = request.state.user["tenant_id"]
        await usage_tracker.track_usage(tenant_id, MetricType.API_REQUESTS)

    return response
```

### 4.4 Rate Limiting

```python
# src/cortexgraph/middleware/rate_limit.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://redis:6379"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Per-tenant rate limiting
def get_tenant_id(request: Request):
    return request.state.user.get("tenant_id")

@app.post("/api/v1/memories")
@limiter.limit("100/minute", key_func=get_tenant_id)
async def create_memory(request: Request, ...):
    # Implementation
    pass

@app.get("/api/v1/memories")
@limiter.limit("1000/minute", key_func=get_tenant_id)
async def search_memories(request: Request, ...):
    # Implementation
    pass
```

---

## Phase 5: Enterprise Features (12+ months)

### 5.1 Advanced Security

```python
# src/cortexgraph/security/encryption.py
from cryptography.fernet import Fernet

class EncryptionService:
    """Field-level encryption for sensitive data."""

    def __init__(self, key: bytes):
        self.fernet = Fernet(key)

    def encrypt(self, data: str) -> str:
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        return self.fernet.decrypt(encrypted.encode()).decode()

# Usage: Encrypt memory content at rest
class EncryptedMemory(Memory):
    @property
    def content(self) -> str:
        return encryption_service.decrypt(self._encrypted_content)

    @content.setter
    def content(self, value: str):
        self._encrypted_content = encryption_service.encrypt(value)
```

### 5.2 Audit Logging

```python
# src/cortexgraph/audit/logger.py
from enum import Enum

class AuditAction(str, Enum):
    MEMORY_CREATE = "memory.create"
    MEMORY_READ = "memory.read"
    MEMORY_UPDATE = "memory.update"
    MEMORY_DELETE = "memory.delete"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"

class AuditLogger:
    async def log(
        self,
        action: AuditAction,
        tenant_id: str,
        user_id: str,
        resource_id: str | None = None,
        metadata: dict | None = None,
        ip_address: str | None = None
    ):
        """Log audit event."""
        await self.storage.save_audit_log({
            "action": action.value,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "resource_id": resource_id,
            "metadata": metadata or {},
            "ip_address": ip_address,
            "timestamp": int(time.time()),
        })

# Decorator for automatic audit logging
def audit_log(action: AuditAction):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # Extract context
            user = kwargs.get("user") or args[0]
            resource_id = result.get("id") if isinstance(result, dict) else None

            await audit_logger.log(
                action=action,
                tenant_id=user["tenant_id"],
                user_id=user["user_id"],
                resource_id=resource_id
            )

            return result
        return wrapper
    return decorator
```

### 5.3 SSO Integration

```python
# src/cortexgraph/auth/saml.py
from onelogin.saml2.auth import OneLogin_Saml2_Auth

class SAMLProvider:
    def __init__(self, settings: dict):
        self.settings = settings

    def init_auth(self, request):
        return OneLogin_Saml2_Auth(request, self.settings)

    async def login(self, request):
        auth = self.init_auth(request)
        return auth.login()

    async def process_response(self, request):
        auth = self.init_auth(request)
        auth.process_response()

        if not auth.is_authenticated():
            raise AuthenticationError("SAML authentication failed")

        # Extract user attributes
        attributes = auth.get_attributes()
        return {
            "email": attributes.get("email")[0],
            "name": attributes.get("name")[0],
            "groups": attributes.get("groups", []),
        }

# OAuth2 (Google, GitHub, etc.)
from authlib.integrations.starlette_client import OAuth

oauth = OAuth()
oauth.register(
    name='google',
    client_id='...',
    client_secret='...',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@app.get('/auth/google/login')
async def google_login(request: Request):
    redirect_uri = request.url_for('google_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get('/auth/google/callback')
async def google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = await oauth.google.parse_id_token(request, token)
    # Create or update user in database
    return user
```

### 5.4 Team Collaboration Features

```python
# src/cortexgraph/collaboration/sharing.py
class SharingService:
    async def share_memory(
        self,
        memory_id: str,
        from_user: str,
        to_users: list[str],
        permission: Literal["read", "write"] = "read"
    ):
        """Share a memory with other users in the same tenant."""
        memory = await self.storage.get_memory(memory_id)

        # Verify ownership
        if memory.user_id != from_user:
            raise PermissionError("Only owner can share")

        # Create sharing records
        for user_id in to_users:
            await self.storage.create_memory_share(
                memory_id=memory_id,
                user_id=user_id,
                permission=permission,
                shared_by=from_user,
            )

    async def get_shared_memories(self, user_id: str) -> list[Memory]:
        """Get all memories shared with this user."""
        return await self.storage.get_shared_memories(user_id)
```

---

## Technology Stack Recommendations

### Core Infrastructure

| Component | Technology | Alternatives | Justification |
|-----------|-----------|--------------|---------------|
| **Web Framework** | FastAPI | Django, Flask | Async support, automatic OpenAPI, type hints |
| **Database** | PostgreSQL + pgvector | Supabase, Neon | ACID, vector search, mature ecosystem |
| **Cache** | Redis | Memcached, KeyDB | Pub/sub, sorted sets, persistence |
| **Message Queue** | Celery + Redis | RabbitMQ, AWS SQS | Proven, Python-native, good monitoring |
| **Container Orchestration** | Kubernetes | ECS, Cloud Run | Portable, mature, ecosystem |
| **Monitoring** | Prometheus + Grafana | DataDog, New Relic | Open source, flexible, cost-effective |
| **Tracing** | OpenTelemetry + Jaeger | Zipkin, DataDog APM | Vendor-neutral, comprehensive |
| **Logging** | ELK Stack | Loki, CloudWatch | Powerful search, visualization |
| **CI/CD** | GitHub Actions | GitLab CI, CircleCI | Native integration, generous free tier |

### Cloud Providers

| Provider | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **AWS** | Most features, global reach | Complex pricing | ✅ **Best for enterprise** |
| **GCP** | K8s native, ML/AI tools | Smaller footprint | ✅ **Good for AI-heavy** |
| **Azure** | Enterprise integration | Complex setup | ⚠️ Consider for MS shops |
| **DigitalOcean** | Simple, affordable | Limited services | ✅ **Good for MVP** |
| **Render** | Automatic deploys, managed DB | Limited control | ✅ **Great for early stage** |

**Recommendation for MVP**: **Render.com** or **Railway.app**
- Managed PostgreSQL with pgvector
- Automatic deployments from GitHub
- Simple pricing (~$20-50/month to start)
- Easy migration to AWS/GCP later

### Development Tools

```bash
# pyproject.toml additions for SaaS
[project.dependencies]
fastapi = ">=0.104.0"
uvicorn = {extras = ["standard"], version = ">=0.24.0"}
pydantic = {extras = ["email"], version = ">=2.0.0"}
asyncpg = ">=0.29.0"
sqlalchemy = {extras = ["asyncio"], version = ">=2.0.0"}
alembic = ">=1.12.0"
redis = {extras = ["hiredis"], version = ">=5.0.0"}
celery = {extras = ["redis"], version = ">=5.3.0"}
python-jose = {extras = ["cryptography"], version = ">=3.3.0"}
passlib = {extras = ["bcrypt"], version = ">=1.7.4"}
slowapi = ">=0.1.9"
prometheus-client = ">=0.19.0"
opentelemetry-api = ">=1.21.0"
opentelemetry-sdk = ">=1.21.0"
opentelemetry-instrumentation-fastapi = ">=0.42b0"
sentry-sdk = {extras = ["fastapi"], version = ">=1.38.0"}
```

---

## Cost Estimation

### Monthly Costs (by scale)

#### MVP (< 100 users)
- **Hosting**: Render.com - $25
- **Database**: Render PostgreSQL - $25
- **Redis**: Render Redis - $10
- **Monitoring**: Free tier (Sentry, Prometheus Cloud)
- **Domain & SSL**: $15
- **Total**: ~$75/month

#### Growth (1,000 users)
- **Hosting**: 3 containers on Render - $75
- **Database**: Render PostgreSQL (4GB) - $75
- **Redis**: Render Redis (1GB) - $25
- **Monitoring**: Sentry Developer - $26
- **CDN**: CloudFlare Pro - $20
- **Total**: ~$221/month

#### Scale (10,000 users)
- **K8s Cluster**: GKE/EKS - $150
- **Database**: Cloud SQL (16GB) - $200
- **Redis**: ElastiCache - $100
- **Object Storage**: S3/GCS - $50
- **Monitoring**: DataDog - $150
- **Load Balancer**: $20
- **Total**: ~$670/month

#### Enterprise (100,000+ users)
- **K8s Cluster**: Multi-zone - $500
- **Database**: Cloud SQL (64GB, replicas) - $1,200
- **Redis Cluster**: $400
- **Object Storage**: $200
- **CDN**: CloudFlare Enterprise - $200
- **Monitoring & APM**: $500
- **Total**: ~$3,000/month

---

## Migration Path & Timeline

### Summary Timeline

| Phase | Duration | Key Deliverables | Team Size |
|-------|----------|-----------------|-----------|
| **Phase 1** | 0-3 months | PostgreSQL, Auth, Multi-tenancy | 2-3 engineers |
| **Phase 2** | 3-6 months | REST API, WebSockets, GraphQL | 3-4 engineers |
| **Phase 3** | 6-9 months | K8s, Monitoring, Caching | 4-5 engineers |
| **Phase 4** | 9-12 months | Background jobs, Webhooks, Billing | 5-6 engineers |
| **Phase 5** | 12+ months | Enterprise features, SSO | 6-8 engineers |

### Recommended Approach

1. **Dual-mode operation** (months 1-6):
   - Keep existing JSONL storage working
   - Add PostgreSQL in parallel
   - Gradual migration path for existing users

2. **Feature flags** for gradual rollout:
   ```python
   from launchdarkly import Client

   if feature_flags.is_enabled("postgres_storage", user):
       storage = PostgreSQLStorage()
   else:
       storage = JSONLStorage()
   ```

3. **Backwards compatibility** guarantee:
   - MCP protocol remains unchanged
   - Existing CLI tools continue working
   - Data export tools for migration

---

## Risk Assessment

### High-Risk Areas

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Data migration failures** | Critical | Dual-write mode, extensive testing, rollback plan |
| **Performance degradation** | High | Load testing, caching strategy, database optimization |
| **Security vulnerabilities** | Critical | Security audit, penetration testing, bug bounty |
| **Multi-tenancy bugs** | Critical | Comprehensive integration tests, row-level security |
| **Cost overruns** | Medium | Usage monitoring, auto-scaling limits, quotas |

### Testing Strategy

```python
# tests/integration/test_multi_tenancy.py
async def test_tenant_isolation():
    """Ensure tenant A cannot access tenant B's data."""
    # Create memories for two tenants
    tenant_a_memory = await create_memory(tenant_id="tenant-a", content="Secret A")
    tenant_b_memory = await create_memory(tenant_id="tenant-b", content="Secret B")

    # Try to access tenant B's memory with tenant A's credentials
    with pytest.raises(PermissionError):
        await get_memory(
            memory_id=tenant_b_memory.id,
            user={"tenant_id": "tenant-a"}
        )

    # Verify tenant A can only see their own memories
    results = await search_memories(user={"tenant_id": "tenant-a"})
    assert all(m.tenant_id == "tenant-a" for m in results)
    assert tenant_b_memory.id not in [m.id for m in results]
```

---

## Success Metrics

### Technical KPIs

- **API Response Time**: p95 < 200ms, p99 < 500ms
- **Database Query Time**: p95 < 50ms
- **Uptime**: 99.9% (8.76 hours downtime/year)
- **Error Rate**: < 0.1% of requests
- **Cache Hit Rate**: > 80%

### Business KPIs

- **User Acquisition**: Track signups, conversion rate
- **Activation**: % of users who create first memory within 24h
- **Retention**: 7-day, 30-day, 90-day retention rates
- **Engagement**: Avg memories/user, searches/user
- **Revenue**: MRR, ARR, churn rate, ARPU

---

## Conclusion

Scaling CortexGraph to SaaS requires significant architectural evolution:

1. **Database migration** from JSONL to PostgreSQL (critical)
2. **Authentication & authorization** with JWT and RBAC (critical)
3. **Multi-tenancy** with row-level isolation (critical)
4. **REST API** alongside MCP protocol (high priority)
5. **Container orchestration** with Kubernetes (high priority)
6. **Monitoring & observability** for production operations (high priority)

**Recommended approach**: Start with a **managed platform MVP** (Render/Railway) to validate market fit, then migrate to Kubernetes on AWS/GCP for scale.

**Timeline**: 12-18 months to production-ready SaaS with 3-6 engineers.

**Total investment**: $200K-500K (engineering + infrastructure) for first year.

---

**Next Steps**:

1. Review and validate this strategy with stakeholders
2. Prioritize Phase 1 work (database, auth, multi-tenancy)
3. Set up CI/CD pipeline and testing infrastructure
4. Begin database schema design and migration planning
5. Prototype REST API with FastAPI
6. Conduct security review and penetration testing
