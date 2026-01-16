#!/bin/bash
# Build Offline Images for cuOpt Deployment
# Creates air-gapped deployment bundle for OCI OKE

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CUOPT_VERSION="${CUOPT_VERSION:-24.03}"
BUNDLE_NAME="cuopt-offline-bundle"
BUNDLE_DIR="${PROJECT_DIR}/offline-bundle"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check prerequisites
check_prereqs() {
    log_info "Checking prerequisites..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if [ -z "$NGC_API_KEY" ]; then
        log_error "NGC_API_KEY environment variable is not set"
        log_info "Get your API key from https://ngc.nvidia.com/setup/api-key"
        exit 1
    fi

    log_info "Prerequisites check passed"
}

# Login to NGC registry
ngc_login() {
    log_info "Logging into NGC registry..."
    echo "$NGC_API_KEY" | docker login nvcr.io -u '$oauthtoken' --password-stdin
}

# Pull cuOpt NIM image
pull_cuopt_image() {
    log_info "Pulling cuOpt NIM image (v${CUOPT_VERSION})..."
    # Using NVIDIA NIM format
    docker pull nvcr.io/nim/nvidia/cuopt:${CUOPT_VERSION}
}

# Build benchmark client image
build_benchmark_image() {
    log_info "Building benchmark client image..."
    docker build \
        -f "${SCRIPT_DIR}/Dockerfile.benchmark" \
        -t cuopt-benchmark:latest \
        "${PROJECT_DIR}"
}

# Build offline cuOpt image with pre-cached models
build_offline_image() {
    log_info "Building offline cuOpt image..."

    # Create config directory if not exists
    mkdir -p "${SCRIPT_DIR}/configs"

    # Create default server config
    cat > "${SCRIPT_DIR}/configs/cuopt-server-config.yaml" << 'EOF'
server:
  host: 0.0.0.0
  port: 8000
  workers: 4

logging:
  level: INFO
  format: json

optimization:
  max_time_limit: 300
  default_time_limit: 30
  enable_cache: true
  cache_size_mb: 1024

metrics:
  enabled: true
  port: 8001
  path: /metrics

health:
  enabled: true
  path: /health
EOF

    docker build \
        -f "${SCRIPT_DIR}/Dockerfile.cuopt-offline" \
        -t cuopt-nim-offline:${CUOPT_VERSION} \
        --build-arg CUOPT_VERSION=${CUOPT_VERSION} \
        "${SCRIPT_DIR}"
}

# Save images to tar files
save_images() {
    log_info "Saving images to tar files..."

    mkdir -p "${BUNDLE_DIR}/images"

    log_info "Saving cuOpt NIM image..."
    docker save nvcr.io/nim/nvidia/cuopt:${CUOPT_VERSION} \
        -o "${BUNDLE_DIR}/images/cuopt-nim-${CUOPT_VERSION}.tar"

    log_info "Saving offline cuOpt image..."
    docker save cuopt-nim-offline:${CUOPT_VERSION} \
        -o "${BUNDLE_DIR}/images/cuopt-nim-offline-${CUOPT_VERSION}.tar"

    log_info "Saving benchmark client image..."
    docker save cuopt-benchmark:latest \
        -o "${BUNDLE_DIR}/images/cuopt-benchmark.tar"

    log_info "Pulling and saving Redis image..."
    docker pull redis:7.2-alpine
    docker save redis:7.2-alpine \
        -o "${BUNDLE_DIR}/images/redis-7.2-alpine.tar"
}

# Copy manifests and scripts
copy_manifests() {
    log_info "Copying Kubernetes manifests and scripts..."

    mkdir -p "${BUNDLE_DIR}/manifests"
    mkdir -p "${BUNDLE_DIR}/scripts"
    mkdir -p "${BUNDLE_DIR}/data"

    cp -r "${PROJECT_DIR}/k8s" "${BUNDLE_DIR}/manifests/"
    cp -r "${PROJECT_DIR}/scripts" "${BUNDLE_DIR}/"
    cp -r "${PROJECT_DIR}/data/sample" "${BUNDLE_DIR}/data/"
    cp -r "${PROJECT_DIR}/benchmarks" "${BUNDLE_DIR}/"
    cp -r "${PROJECT_DIR}/use-cases" "${BUNDLE_DIR}/"
    cp "${PROJECT_DIR}/README.md" "${BUNDLE_DIR}/"
}

# Create offline deployment script
create_offline_deploy_script() {
    log_info "Creating offline deployment script..."

    cat > "${BUNDLE_DIR}/deploy-offline.sh" << 'DEPLOY_SCRIPT'
#!/bin/bash
# Offline Deployment Script for cuOpt on OKE
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CUOPT_VERSION="${CUOPT_VERSION:-24.03}"

echo "=== cuOpt Offline Deployment ==="

# Load images
echo "Loading Docker images..."
for img in "${SCRIPT_DIR}/images"/*.tar; do
    echo "Loading: $(basename "$img")"
    docker load -i "$img"
done

# Tag for local registry (update with your OCIR details)
OCIR_REGION="${OCIR_REGION:-fra}"
OCIR_NAMESPACE="${OCIR_NAMESPACE:-frntrd2vyxvi}"
OCIR_REPO="fra.ocir.io/${OCIR_NAMESPACE}/models"

echo "Tagging images for OCIR Frankfurt..."
docker tag cuopt-nim-offline:${CUOPT_VERSION} ${OCIR_REPO}:cuopt-nim-${CUOPT_VERSION}
docker tag cuopt-benchmark:latest ${OCIR_REPO}:cuopt-benchmark-latest
docker tag redis:7.2-alpine ${OCIR_REPO}:redis-7.2-alpine

echo "Pushing images to OCIR..."
docker push ${OCIR_REPO}:cuopt-nim-${CUOPT_VERSION}
docker push ${OCIR_REPO}:cuopt-benchmark-latest
docker push ${OCIR_REPO}:redis-7.2-alpine

echo "Deploying to Kubernetes..."
kubectl apply -k "${SCRIPT_DIR}/manifests/k8s/overlays/production"

echo "=== Deployment Complete ==="
kubectl get pods -n cuopt
DEPLOY_SCRIPT

    chmod +x "${BUNDLE_DIR}/deploy-offline.sh"
}

# Create bundle archive
create_bundle() {
    log_info "Creating offline bundle archive..."

    cd "${PROJECT_DIR}"
    tar -czvf "${BUNDLE_NAME}.tar.gz" -C "${BUNDLE_DIR}" .

    log_info "Bundle created: ${PROJECT_DIR}/${BUNDLE_NAME}.tar.gz"
    log_info "Bundle size: $(du -h "${BUNDLE_NAME}.tar.gz" | cut -f1)"
}

# Main execution
main() {
    log_info "Starting offline build process..."
    log_info "cuOpt Version: ${CUOPT_VERSION}"

    check_prereqs
    ngc_login
    pull_cuopt_image
    build_benchmark_image
    build_offline_image
    save_images
    copy_manifests
    create_offline_deploy_script
    create_bundle

    log_info "=== Build Complete ==="
    log_info "Offline bundle ready: ${PROJECT_DIR}/${BUNDLE_NAME}.tar.gz"
    log_info ""
    log_info "To deploy in air-gapped environment:"
    log_info "  1. Transfer ${BUNDLE_NAME}.tar.gz to target system"
    log_info "  2. Extract: tar -xzf ${BUNDLE_NAME}.tar.gz"
    log_info "  3. Run: ./deploy-offline.sh"
}

main "$@"
