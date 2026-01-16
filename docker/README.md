# Docker Images Build Guide

This directory contains all Dockerfiles and build scripts for the cuOpt deployment.

## Overview

| Image | Dockerfile | Purpose | Size |
|-------|------------|---------|------|
| **cuOpt Offline** | `Dockerfile.cuopt-offline` | Main cuOpt NIM for air-gapped/offline deployment | ~15GB |
| **Benchmark Client** | `Dockerfile.benchmark` | Benchmark client for testing cuOpt (10-500 vehicles) | ~500MB |
| **Redis** | Docker Hub | Caching layer for cuOpt optimization results | ~30MB |

---

## Prerequisites

### Required Tools
- Docker 20.10+ with BuildKit support
- NVIDIA NGC account and API key
- Access to NVIDIA GPU (for running cuOpt)

### Required Credentials

| Credential | Description | Where to Get |
|------------|-------------|--------------|
| `NGC_API_KEY` | NVIDIA NGC API key | [ngc.nvidia.com/setup/api-key](https://ngc.nvidia.com/setup/api-key) |
| OCIR credentials | Oracle Container Registry access | OCI Console > Auth Tokens |

---

## Building Images

### Option 1: Automated Build (Recommended)

Use the provided build script for a complete offline deployment bundle:

```bash
# Set your NGC API key
export NGC_API_KEY="your-ngc-api-key-here"

# Run the build script
cd docker
./build-offline.sh
```

This script will:
1. Login to NGC registry
2. Pull the cuOpt NIM image
3. Build the offline cuOpt image
4. Build the benchmark client image
5. Save all images as tar files
6. Create a complete offline deployment bundle

**Output:** `cuopt-offline-bundle.tar.gz` containing all images and manifests.

---

### Option 2: Manual Build

#### 1. Build cuOpt Offline Image

This image wraps the NVIDIA cuOpt NIM for offline/air-gapped deployment.

```bash
# Login to NGC registry
echo "$NGC_API_KEY" | docker login nvcr.io -u '$oauthtoken' --password-stdin

# Pull base cuOpt NIM image (required first)
docker pull nvcr.io/nim/nvidia/cuopt:24.03

# Build offline image
docker build \
  -f Dockerfile.cuopt-offline \
  -t cuopt-nim-offline:24.03 \
  --build-arg CUOPT_VERSION=24.03 \
  .

# Verify build
docker images | grep cuopt-nim-offline
```

**Build Arguments:**

| Argument | Default | Description |
|----------|---------|-------------|
| `CUOPT_VERSION` | `24.03` | cuOpt NIM version to use |

**Environment Variables (runtime):**

| Variable | Default | Description |
|----------|---------|-------------|
| `CUOPT_SERVER_HOST` | `0.0.0.0` | Server bind address |
| `CUOPT_SERVER_PORT` | `8000` | Server port |
| `CUOPT_LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `CUOPT_MAX_CONCURRENT_REQUESTS` | `10` | Max concurrent optimization requests |
| `CUOPT_ENABLE_METRICS` | `true` | Enable Prometheus metrics |
| `CUOPT_TELEMETRY_ENABLED` | `false` | Telemetry (disabled for offline) |

---

#### 2. Build Benchmark Client Image

This image contains the benchmark client for testing cuOpt with EV fleet scenarios.

```bash
# Build from project root (one level up from docker/)
cd ..

docker build \
  -f docker/Dockerfile.benchmark \
  -t cuopt-benchmark:v2 \
  .

# Verify build
docker images | grep cuopt-benchmark
```

**Test locally:**

```bash
# Run with local cuOpt endpoint
docker run --rm \
  -e CUOPT_ENDPOINT=http://host.docker.internal:8000 \
  -v $(pwd)/results:/results \
  cuopt-benchmark:v2
```

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `CUOPT_ENDPOINT` | `http://cuopt-service:8000` | cuOpt service endpoint |
| `RESULTS_DIR` | `/results` | Directory to save benchmark results |

---

#### 3. Pull Redis Image

Redis is used as a caching layer for cuOpt optimization results. Pull from Docker Hub:

```bash
# Pull Redis Alpine (lightweight)
docker pull redis:7.2-alpine

# Verify
docker images | grep redis
```

**Redis Configuration (in Kubernetes deployment):**

| Parameter | Value | Description |
|-----------|-------|-------------|
| `maxmemory` | `512mb` | Maximum memory for cache |
| `maxmemory-policy` | `allkeys-lru` | Eviction policy (Least Recently Used) |
| `appendonly` | `yes` | Enable persistence |

---

## Pushing to Oracle Container Registry (OCIR)

### 1. Login to OCIR

```bash
# Frankfurt region example
OCIR_REGION="fra"
OCIR_NAMESPACE="your-tenancy-namespace"
OCIR_USERNAME="your-tenancy/your-username"
OCIR_PASSWORD="your-auth-token"

docker login ${OCIR_REGION}.ocir.io -u "${OCIR_USERNAME}" -p "${OCIR_PASSWORD}"
```

### 2. Tag and Push Images

```bash
# Define registry
OCIR_REPO="${OCIR_REGION}.ocir.io/${OCIR_NAMESPACE}/models"

# Tag images
docker tag cuopt-nim-offline:24.03 ${OCIR_REPO}:cuopt-nim-24.03
docker tag cuopt-benchmark:v2 ${OCIR_REPO}:cuopt-benchmark-v2
docker tag redis:7.2-alpine ${OCIR_REPO}:redis-7.2-alpine

# Push images
docker push ${OCIR_REPO}:cuopt-nim-24.03
docker push ${OCIR_REPO}:cuopt-benchmark-v2
docker push ${OCIR_REPO}:redis-7.2-alpine
```

---

## Offline/Air-Gapped Deployment

For environments without internet access:

### 1. Save Images to Tar Files

```bash
# Save cuOpt NIM
docker save cuopt-nim-offline:24.03 -o cuopt-nim-offline-24.03.tar

# Save benchmark client
docker save cuopt-benchmark:v2 -o cuopt-benchmark-v2.tar

# Save Redis
docker save redis:7.2-alpine -o redis-7.2-alpine.tar

# Create bundle
tar -czvf cuopt-images-bundle.tar.gz \
  cuopt-nim-offline-24.03.tar \
  cuopt-benchmark-v2.tar \
  redis-7.2-alpine.tar
```

### 2. Transfer to Air-Gapped System

```bash
# Copy bundle to target system
scp cuopt-images-bundle.tar.gz user@target-system:/path/to/images/
```

### 3. Load Images on Target

```bash
# Extract bundle
tar -xzvf cuopt-images-bundle.tar.gz

# Load images
docker load -i cuopt-nim-offline-24.03.tar
docker load -i cuopt-benchmark-v2.tar
docker load -i redis-7.2-alpine.tar

# Verify
docker images | grep -E "cuopt|redis"
```

### 4. Push to Internal Registry

```bash
# Tag for internal registry
docker tag cuopt-nim-offline:24.03 internal-registry.local/cuopt:nim-24.03
docker tag cuopt-benchmark:v2 internal-registry.local/cuopt:benchmark-v2
docker tag redis:7.2-alpine internal-registry.local/cuopt:redis-7.2-alpine

# Push
docker push internal-registry.local/cuopt:nim-24.03
docker push internal-registry.local/cuopt:benchmark-v2
docker push internal-registry.local/cuopt:redis-7.2-alpine
```

---

## Directory Structure

```
docker/
├── README.md                      # This file
├── Dockerfile.cuopt-offline       # cuOpt NIM for offline deployment
├── Dockerfile.benchmark           # Benchmark client image
├── build-offline.sh               # Automated build script
└── configs/
    └── cuopt-server-config.yaml   # cuOpt server configuration
```

---

## Troubleshooting

### NGC Login Failed

```bash
# Verify API key is set
echo $NGC_API_KEY

# Test login manually
docker login nvcr.io -u '$oauthtoken' -p "$NGC_API_KEY"
```

### Build Fails - Missing Base Image

```bash
# Ensure you pulled the base image first
docker pull nvcr.io/nim/nvidia/cuopt:24.03

# Check available tags
# Visit: https://catalog.ngc.nvidia.com/orgs/nim/teams/nvidia/containers/cuopt
```

### Out of Disk Space

cuOpt images are large (~15GB). Ensure sufficient disk space:

```bash
# Check disk space
df -h

# Clean unused Docker resources
docker system prune -a
```

### OCIR Push Fails

```bash
# Verify login
docker login fra.ocir.io

# Check image exists
docker images | grep cuopt

# Ensure repository exists in OCIR (create via OCI Console if needed)
```

---

## Quick Reference

### Build Commands

```bash
# Build all (automated)
export NGC_API_KEY="your-key"
./build-offline.sh

# Build cuOpt offline only
docker build -f Dockerfile.cuopt-offline -t cuopt-nim-offline:24.03 .

# Build benchmark only (from project root)
docker build -f docker/Dockerfile.benchmark -t cuopt-benchmark:v2 ..

# Pull Redis
docker pull redis:7.2-alpine
```

### Push Commands

```bash
# Push to OCIR Frankfurt
docker tag cuopt-nim-offline:24.03 fra.ocir.io/namespace/models:cuopt-nim-24.03
docker tag cuopt-benchmark:v2 fra.ocir.io/namespace/models:cuopt-benchmark-v2
docker tag redis:7.2-alpine fra.ocir.io/namespace/models:redis-7.2-alpine

docker push fra.ocir.io/namespace/models:cuopt-nim-24.03
docker push fra.ocir.io/namespace/models:cuopt-benchmark-v2
docker push fra.ocir.io/namespace/models:redis-7.2-alpine
```

### Run Commands

```bash
# Run cuOpt locally (requires NVIDIA GPU)
docker run --gpus all -p 8000:8000 cuopt-nim-offline:24.03

# Run Redis locally
docker run -d -p 6379:6379 --name redis redis:7.2-alpine

# Run benchmark
docker run -e CUOPT_ENDPOINT=http://localhost:8000 cuopt-benchmark:v2
```

---

## Related Documentation

- [Deployment Guide](../docs/DEPLOYMENT.md) - Kubernetes deployment instructions
- [Troubleshooting](../docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Main README](../README.md) - Project overview and benchmark results
