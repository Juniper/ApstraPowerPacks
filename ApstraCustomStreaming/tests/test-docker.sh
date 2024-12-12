#!/bin/bash

# Set project-specific variables
PROJECT_NAME="apstra-task-audit"
CONTAINER_NAME="apstra-task-audit"

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored status messages
print_status() {
    echo -e "${YELLOW}[STATUS]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if container is healthy
check_container_health() {
    local max_attempts=30
    local attempt=1
    local delay=2

    while [ $attempt -le $max_attempts ]; do
        if docker logs $CONTAINER_NAME 2>&1 | grep -q "Apstra Task Audit Trail Service Started"; then
            return 0
        fi
        print_status "Waiting for container to be ready... (Attempt $attempt/$max_attempts)"
        sleep $delay
        ((attempt++))
    done
    return 1
}

# Clean up function
cleanup() {
    print_status "Cleaning up..."
    
    # Stop container if running
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        print_status "Stopping container $CONTAINER_NAME..."
        docker stop $CONTAINER_NAME > /dev/null
    fi

    # Remove container if exists
    if docker ps -aq -f name=$CONTAINER_NAME | grep -q .; then
        print_status "Removing container $CONTAINER_NAME..."
        docker rm $CONTAINER_NAME > /dev/null
    fi

    # Remove image if exists
    if docker images $PROJECT_NAME | grep -q $PROJECT_NAME; then
        print_status "Removing image $PROJECT_NAME..."
        docker rmi $PROJECT_NAME > /dev/null
    fi

    # Clean up any dangling images related to our project
    if docker images -f "dangling=true" | grep -q "none"; then
        print_status "Removing dangling images..."
        docker images -f "dangling=true" -q | xargs docker rmi > /dev/null 2>&1
    fi
}

# Main test function
run_test() {
    print_status "Starting test run for $PROJECT_NAME"
    
    # Initial cleanup
    cleanup

    # Build new image
    print_status "Building new Docker image..."
    if ! docker build -t $PROJECT_NAME .; then
        print_error "Failed to build Docker image"
        cleanup
        return 1
    fi
    print_success "Docker image built successfully"

    # Run container
    print_status "Starting container..."
    if ! docker run -d --name $CONTAINER_NAME $PROJECT_NAME; then
        print_error "Failed to start container"
        cleanup
        return 1
    fi
    print_success "Container started"

    # Check container health
    print_status "Checking container health..."
    if ! check_container_health; then
        print_error "Container health check failed"
        print_error "Container logs:"
        docker logs $CONTAINER_NAME
        cleanup
        return 1
    fi
    print_success "Container is healthy"

    # Display container info
    print_status "Container information:"
    echo "----------------------------------------"
    docker ps -f name=$CONTAINER_NAME
    echo "----------------------------------------"

    # Clean up
    print_status "Test completed successfully. Cleaning up..."
    cleanup
    print_success "All done! Test completed successfully"
}

# Create dev-tools directory and move script there
create_dev_tools() {
    # Create dev-tools directory if it doesn't exist
    mkdir -p dev-tools/docker
    
    # Copy this script to dev-tools/docker
    cp "$0" dev-tools/docker/test-docker.sh
    chmod +x dev-tools/docker/test-docker.sh
    
    print_success "Dev tools set up in dev-tools/docker/"
    print_status "You can run the test script using: ./dev-tools/docker/test-docker.sh"
}

# Main execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Check if we're in the project root
    if [[ ! -f "Dockerfile" ]]; then
        print_error "Please run this script from the project root directory"
        exit 1
    fi
    
    # Create dev-tools directory and move script there if it's not already in dev-tools
    if [[ ! "$0" =~ "dev-tools/docker" ]]; then
        create_dev_tools
        exit 0
    fi
    
    # Run the test
    run_test
fi
