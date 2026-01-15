# Troubleshooting Guide

## Common Issues

### 1. GPU Not Detected

**Symptoms:**
- Pod stuck in Pending state
- Error: "0/X nodes available: X Insufficient nvidia.com/gpu"

**Solutions:**
```bash
# Check GPU operator
kubectl get pods -n gpu-operator

# Check node labels
kubectl get nodes --show-labels | grep nvidia

# Verify GPU resources
kubectl describe node <node-name> | grep -A5 "Allocatable"
```

### 2. Image Pull Errors

**NGC Image Pull Failed:**
```bash
# Verify NGC secret
kubectl get secret ngc-secret -n cuopt -o yaml

# Test NGC credentials
docker login nvcr.io -u '$oauthtoken' -p '<NGC_API_KEY>'
```

**OCIR Image Pull Failed:**
```bash
# Verify OCIR secret
kubectl get secret ocir-secret -n cuopt -o yaml

# Test OCIR credentials
docker login <region>.ocir.io -u '<tenancy>/<user>' -p '<auth-token>'
```

### 3. Service Not Reachable

**Symptoms:**
- Connection refused
- No endpoints

**Solutions:**
```bash
# Check service endpoints
kubectl get endpoints cuopt-service -n cuopt

# Check pod labels match service selector
kubectl get pods -n cuopt --show-labels
kubectl get svc cuopt-service -n cuopt -o yaml | grep selector -A5

# Fix selector if needed
kubectl patch svc cuopt-service -n cuopt --type='json' \
  -p='[{"op":"replace","path":"/spec/selector","value":{"app":"cuopt-nim"}}]'
```

### 4. Out of Memory

**Symptoms:**
- Pod OOMKilled
- CUDA out of memory errors

**Solutions:**
```bash
# Check current resource usage
kubectl top pods -n cuopt

# Increase memory limits
# Edit k8s/overlays/production/patch-resources.yaml
# Increase memory: "64Gi"
```

### 5. Slow Performance

**Symptoms:**
- Response times higher than expected
- Variable latency

**Solutions:**
```bash
# Check pod distribution
kubectl get pods -n cuopt -o wide

# Ensure anti-affinity is working (pods on different nodes)
# Check for resource contention
kubectl describe node <node-name>
```

### 6. Quota Exceeded

**Symptoms:**
- "exceeded quota" error

**Solutions:**
```bash
# Check quota usage
kubectl describe quota -n cuopt

# Increase quota or reduce resource requests
kubectl edit resourcequota cuopt-quota -n cuopt
```

## Debugging Commands

```bash
# Get all resources
kubectl get all -n cuopt

# Describe pod for events
kubectl describe pod <pod-name> -n cuopt

# Get pod logs
kubectl logs <pod-name> -n cuopt

# Previous pod logs (if restarted)
kubectl logs <pod-name> -n cuopt --previous

# Exec into pod
kubectl exec -it <pod-name> -n cuopt -- /bin/bash

# Check events
kubectl get events -n cuopt --sort-by='.lastTimestamp'
```

## Getting Help

1. Check the [GitHub Issues](https://github.com/your-org/cuopt-oci-ev-fleet/issues)
2. Review NVIDIA cuOpt documentation
3. Contact AI Center of Excellence team
