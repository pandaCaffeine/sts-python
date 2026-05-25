#!/bin/bash
# build_and_push.sh - Build and push Docker image to Docker Hub
# Usage: ./build_and_push.sh [version]

# Configuration
IMAGE_NAME="pandacaffeine/sts"
DOCKERFILE="Dockerfile"
PLATFORM="linux/amd64"

# Get version from argument or use default
VERSION="${1:-2.0}"
FULL_IMAGE="${IMAGE_NAME}:${VERSION}"
LATEST_IMAGE="${IMAGE_NAME}:latest"

echo "=== Building Docker image: ${FULL_IMAGE} ==="

# Build the image
docker build \
    --platform "${PLATFORM}" \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    -t "${FULL_IMAGE}" \
    -t "${LATEST_IMAGE}" \
    -f "${DOCKERFILE}" \
    .

echo "=== Image built successfully ==="
echo "Pushing to Docker Hub..."

# Push both version tag and latest
# docker push "${FULL_IMAGE}"
# docker push "${LATEST_IMAGE}"

echo "=== Done! ==="
echo "Image pushed: ${FULL_IMAGE}"
echo "Also tagged as: ${LATEST_IMAGE}"