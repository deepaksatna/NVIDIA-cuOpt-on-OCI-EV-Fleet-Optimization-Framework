#!/bin/bash
# =============================================================================
# Deploy cuOpt to OKE Cluster
# =============================================================================
# Usage:
#   ./deploy-cuopt.sh              # Deploy with default settings
#   ./deploy-cuopt.sh --dev        # Deploy development configuration
#   ./deploy-cuopt.sh --production # Deploy production configuration
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
ENVIRONMENT="production"
for arg in "$@"; do
    case $arg in
        --dev)
            ENVIRONMENT="dev"
            ;;
        --production)
            ENVIRONMENT="production"
            ;;
    esac
done

echo ""
echo "=============================================="
echo "  cuOpt Deployment Script"
echo "=============================================="
echo "  Environment: ${ENVIRONMENT}"
echo "=============================================="
echo ""

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl is not installed"
    exit 1
fi

# Check cluster connectivity
log_info "Checking cluster connectivity..."
if ! kubectl cluster-info &> /dev/null; then
    log_error "Cannot connect to Kubernetes cluster"
    exit 1
fi

# Create namespace
log_info "Creating namespace..."
kubectl apply -f "${PROJECT_DIR}/k8s/base/namespace.yaml"

# Check for secrets
log_info "Checking secrets..."
if [ ! -f "${PROJECT_DIR}/k8s/base/ngc-secret.yaml" ]; then
    log_warn "NGC secret not found. Please create from template:"
    log_warn "  cp configs/ngc-secret.yaml.template k8s/base/ngc-secret.yaml"
    log_warn "  Edit with your NGC API key"
fi

if [ ! -f "${PROJECT_DIR}/k8s/base/ocir-secret.yaml" ]; then
    log_warn "OCIR secret not found. Please create using kubectl:"
    log_warn "  kubectl create secret docker-registry ocir-secret \\"
    log_warn "    --namespace=cuopt \\"
    log_warn "    --docker-server=<region>.ocir.io \\"
    log_warn "    --docker-username='<tenancy>/<username>' \\"
    log_warn "    --docker-password='<auth-token>' \\"
    log_warn "    --dry-run=client -o yaml > k8s/base/ocir-secret.yaml"
fi

# Apply secrets if they exist
if [ -f "${PROJECT_DIR}/k8s/base/ngc-secret.yaml" ]; then
    log_info "Applying NGC secret..."
    kubectl apply -f "${PROJECT_DIR}/k8s/base/ngc-secret.yaml"
fi

if [ -f "${PROJECT_DIR}/k8s/base/ocir-secret.yaml" ]; then
    log_info "Applying OCIR secret..."
    kubectl apply -f "${PROJECT_DIR}/k8s/base/ocir-secret.yaml"
fi

# Deploy cuOpt using kustomize
log_info "Deploying cuOpt (${ENVIRONMENT})..."
kubectl apply -k "${PROJECT_DIR}/k8s/overlays/${ENVIRONMENT}/"

# Wait for deployment
log_info "Waiting for pods to be ready..."
kubectl rollout status deployment/cuopt-nim -n cuopt --timeout=600s

# Show status
echo ""
log_info "=============================================="
log_info "  Deployment Complete!"
log_info "=============================================="
echo ""

kubectl get pods -n cuopt -o wide
echo ""
kubectl get svc -n cuopt
echo ""

# Test health endpoint
log_info "Testing health endpoint..."
SVC_IP=$(kubectl get svc cuopt-external -n cuopt -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
if [ -n "$SVC_IP" ]; then
    log_info "External IP: ${SVC_IP}"
    curl -s "http://${SVC_IP}/cuopt/health" && echo ""
else
    log_warn "External LoadBalancer not yet assigned. Use port-forward to test:"
    log_warn "  kubectl port-forward svc/cuopt-service -n cuopt 8000:8000"
fi

echo ""
log_info "Next steps:"
log_info "  1. Run benchmarks: ./scripts/build-benchmark-image.sh --run"
log_info "  2. Monitor: kubectl logs -f -l app=cuopt-nim -n cuopt"
log_info ""
