#!/bin/bash

# Timelapse Generator Deployment Script
# This script builds and deploys the timelapse generator to TrueNAS Scale

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="timelapse-generator"
IMAGE_TAG="latest"
NAMESPACE="timelapse-generator"

# Functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    print_info "Checking dependencies..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check if we can connect to Kubernetes
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi
    
    print_success "All dependencies are satisfied"
}

build_image() {
    print_info "Building Docker image..."
    
    if docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .; then
        print_success "Docker image built successfully"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
}

create_namespace() {
    print_info "Creating namespace..."
    
    if kubectl get namespace ${NAMESPACE} &> /dev/null; then
        print_warning "Namespace ${NAMESPACE} already exists"
    else
        if kubectl create namespace ${NAMESPACE}; then
            print_success "Namespace ${NAMESPACE} created"
        else
            print_error "Failed to create namespace"
            exit 1
        fi
    fi
}

deploy_application() {
    print_info "Deploying application..."
    
    # Apply the Kubernetes manifests
    if kubectl apply -f app.yaml; then
        print_success "Application deployed successfully"
    else
        print_error "Failed to deploy application"
        exit 1
    fi
}

wait_for_deployment() {
    print_info "Waiting for deployment to be ready..."
    
    # Wait for the deployment to be ready
    if kubectl wait --for=condition=available --timeout=300s deployment/timelapse-generator -n ${NAMESPACE}; then
        print_success "Deployment is ready"
    else
        print_error "Deployment failed to become ready"
        exit 1
    fi
}

get_service_info() {
    print_info "Getting service information..."
    
    # Get the service URL
    SERVICE_IP=$(kubectl get service timelapse-generator-service -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    
    if [ -n "$SERVICE_IP" ]; then
        print_success "Service is available at: http://${SERVICE_IP}"
    else
        print_warning "Service IP not available yet. You may need to wait a moment or check your ingress configuration."
        print_info "You can check the service status with: kubectl get service -n ${NAMESPACE}"
    fi
    
    # Get pod information
    POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l app=timelapse-generator -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    if [ -n "$POD_NAME" ]; then
        print_info "Pod name: ${POD_NAME}"
        print_info "View logs with: kubectl logs -f ${POD_NAME} -n ${NAMESPACE}"
    fi
}

cleanup() {
    print_info "Cleaning up..."
    
    # Remove temporary files
    rm -f /tmp/ffmpeg_list_*.txt 2>/dev/null || true
    
    print_success "Cleanup completed"
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -b, --build-only    Only build the Docker image"
    echo "  -d, --deploy-only   Only deploy (skip build)"
    echo "  -c, --cleanup       Clean up deployment"
    echo "  -t, --test          Run tests after deployment"
    echo ""
    echo "Examples:"
    echo "  $0                  # Build and deploy"
    echo "  $0 --build-only     # Only build image"
    echo "  $0 --deploy-only    # Only deploy"
    echo "  $0 --cleanup        # Remove deployment"
}

cleanup_deployment() {
    print_info "Cleaning up deployment..."
    
    if kubectl delete -f app.yaml; then
        print_success "Deployment cleaned up successfully"
    else
        print_error "Failed to clean up deployment"
        exit 1
    fi
}

run_tests() {
    print_info "Running tests..."
    
    # Wait a bit for the service to be fully ready
    sleep 10
    
    # Check if the service is responding
    SERVICE_IP=$(kubectl get service timelapse-generator-service -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    
    if [ -n "$SERVICE_IP" ]; then
        if curl -f http://${SERVICE_IP}/api/system/info &> /dev/null; then
            print_success "Service is responding correctly"
        else
            print_error "Service is not responding correctly"
        fi
    else
        print_warning "Cannot test service - IP not available"
    fi
}

# Main script
main() {
    BUILD_ONLY=false
    DEPLOY_ONLY=false
    CLEANUP_ONLY=false
    RUN_TESTS=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -b|--build-only)
                BUILD_ONLY=true
                shift
                ;;
            -d|--deploy-only)
                DEPLOY_ONLY=true
                shift
                ;;
            -c|--cleanup)
                CLEANUP_ONLY=true
                shift
                ;;
            -t|--test)
                RUN_TESTS=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    echo "🎬 Timelapse Generator Deployment Script"
    echo "========================================"
    
    if [ "$CLEANUP_ONLY" = true ]; then
        cleanup_deployment
        exit 0
    fi
    
    check_dependencies
    
    if [ "$DEPLOY_ONLY" = false ]; then
        build_image
    fi
    
    if [ "$BUILD_ONLY" = false ]; then
        create_namespace
        deploy_application
        wait_for_deployment
        get_service_info
        
        if [ "$RUN_TESTS" = true ]; then
            run_tests
        fi
    fi
    
    cleanup
    
    print_success "Deployment completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Access the web interface at the URL shown above"
    echo "2. Configure your input/output folders"
    echo "3. Start creating timelapses!"
    echo ""
    echo "Useful commands:"
    echo "  kubectl logs -f -n ${NAMESPACE} -l app=timelapse-generator"
    echo "  kubectl get pods -n ${NAMESPACE}"
    echo "  kubectl get service -n ${NAMESPACE}"
}

# Run main function with all arguments
main "$@" 