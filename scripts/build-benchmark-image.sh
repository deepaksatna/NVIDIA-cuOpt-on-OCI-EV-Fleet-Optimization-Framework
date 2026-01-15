#!/bin/bash
# =============================================================================
# Build and Push cuOpt Benchmark Image to OCIR
# =============================================================================
# Usage:
#   ./build-benchmark-image.sh          # Build only
#   ./build-benchmark-image.sh --push   # Build and push to OCIR
#   ./build-benchmark-image.sh --run    # Build, push, and deploy job
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Load configuration
if [ -f "${PROJECT_DIR}/configs/credentials.env" ]; then
    source "${PROJECT_DIR}/configs/credentials.env"
else
    log_error "Configuration file not found: configs/credentials.env"
    log_info "Please copy configs/credentials.env.template to configs/credentials.env"
    exit 1
fi

# Validate required variables
if [ -z "$OCIR_REGISTRY" ]; then
    log_error "OCIR_REGISTRY not set in credentials.env"
    exit 1
fi

IMAGE_NAME="cuopt-benchmark-v2"
FULL_IMAGE="${OCIR_REGISTRY}:${IMAGE_NAME}"
NAMESPACE="cuopt"

# Parse arguments
PUSH_IMAGE=false
RUN_JOB=false
for arg in "$@"; do
    case $arg in
        --push)
            PUSH_IMAGE=true
            ;;
        --run)
            PUSH_IMAGE=true
            RUN_JOB=true
            ;;
    esac
done

echo ""
echo "=============================================="
echo "  cuOpt Benchmark Image Builder"
echo "=============================================="
echo "  Image: ${FULL_IMAGE}"
echo "  Project: ${PROJECT_DIR}"
echo "=============================================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed"
    exit 1
fi

# Build image
log_info "Building benchmark image..."
cd "$PROJECT_DIR"

docker build \
    -f docker/Dockerfile.benchmark \
    -t ${FULL_IMAGE} \
    --no-cache \
    .

log_info "Image built successfully: ${FULL_IMAGE}"

# Push if requested
if [ "$PUSH_IMAGE" = true ]; then
    log_info "Logging into OCIR..."

    if [ -z "$OCIR_PASSWORD" ]; then
        echo "Enter OCIR password (auth token):"
        read -s OCIR_PASSWORD
    fi

    echo "$OCIR_PASSWORD" | docker login $(echo $OCIR_REGISTRY | cut -d'/' -f1) -u "$OCIR_USERNAME" --password-stdin

    log_info "Pushing image to OCIR..."
    docker push ${FULL_IMAGE}

    log_info "Image pushed successfully!"
fi

# Run job if requested
if [ "$RUN_JOB" = true ]; then
    log_info "Deploying benchmark job to cluster..."

    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi

    # Update job manifest with image
    sed "s|\${OCIR_REGISTRY}|${OCIR_REGISTRY}|g" \
        "${PROJECT_DIR}/k8s/base/benchmark-job.yaml" | \
        kubectl apply -f -

    log_info "Benchmark job deployed!"
    log_info ""
    log_info "Monitor progress:"
    log_info "  kubectl logs -f -l app=cuopt-benchmark-full -n ${NAMESPACE}"
fi

echo ""
log_info "=============================================="
log_info "  Build Complete!"
log_info "=============================================="
echo ""
log_info "Next steps:"
log_info "  1. Push to OCIR:  $0 --push"
log_info "  2. Run benchmark: $0 --run"
log_info ""
