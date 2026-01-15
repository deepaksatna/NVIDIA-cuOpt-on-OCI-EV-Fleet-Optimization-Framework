# Deployment Guide

## Prerequisites

### OCI Requirements
- OCI Account with appropriate quotas
- GPU quota for VM.GPU.A10.1 instances (or equivalent)
- OKE cluster with GPU node pool

### Tools
- `kubectl` configured for your OKE cluster
- Docker for building images
- OCI CLI (optional, for automation)

### Credentials
- NVIDIA NGC API Key
- OCI Auth Token for OCIR

## Step-by-Step Deployment

### 1. Clone and Configure

```bash
git clone <repository-url>
cd cuopt-oci-ev-fleet

# Copy credential templates
cp configs/credentials.env.template configs/credentials.env

# Edit with your values
nano configs/credentials.env
```

### 2. Create Kubernetes Secrets

**NGC Secret (for pulling cuOpt image):**
```bash
# Generate the secret
NGC_API_KEY="your-ngc-api-key"
kubectl create secret docker-registry ngc-secret \
  --namespace=cuopt \
  --docker-server=nvcr.io \
  --docker-username='$oauthtoken' \
  --docker-password="${NGC_API_KEY}" \
  --dry-run=client -o yaml > k8s/base/ngc-secret.yaml
```

**OCIR Secret (for pulling benchmark image):**
```bash
kubectl create secret docker-registry ocir-secret \
  --namespace=cuopt \
  --docker-server=<region>.ocir.io \
  --docker-username='<tenancy>/<username>' \
  --docker-password='<auth-token>' \
  --dry-run=client -o yaml > k8s/base/ocir-secret.yaml
```

### 3. Deploy cuOpt

```bash
# Create namespace
kubectl apply -f k8s/base/namespace.yaml

# Apply secrets
kubectl apply -f k8s/base/ngc-secret.yaml
kubectl apply -f k8s/base/ocir-secret.yaml

# Deploy cuOpt (production config)
kubectl apply -k k8s/overlays/production/

# Watch deployment
kubectl get pods -n cuopt -w
```

### 4. Verify Deployment

```bash
# Check pods
kubectl get pods -n cuopt

# Check service
kubectl get svc -n cuopt

# Test health endpoint
kubectl port-forward svc/cuopt-service 8000:8000 -n cuopt &
curl http://localhost:8000/cuopt/health
```

### 5. Run Benchmarks

```bash
# Build and push benchmark image
./scripts/build-benchmark-image.sh --push

# Deploy benchmark job
./scripts/build-benchmark-image.sh --run

# Monitor
kubectl logs -f -l app=cuopt-benchmark-full -n cuopt
```

## Scaling

### Add More GPU Nodes
```bash
# Scale the node pool in OCI Console or using OCI CLI
oci ce node-pool update --node-pool-id <pool-id> --size 8
```

### Adjust Replicas
```bash
# Edit production overlay
vi k8s/overlays/production/patch-replicas.yaml
# Change replicas: 8

# Apply
kubectl apply -k k8s/overlays/production/
```

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.
