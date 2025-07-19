#!/bin/bash

docker build -f ./dockerfiles/FB_BASE/Dockerfile -t fb_base:dev .

REPOS=(
  astropy
  django
  matplotlib
  pylint
  pytest
  requests
  scikit-learn
  seaborn
  sphinx
  xarray
)


for REPO in "${REPOS[@]}"; do
  echo "🔨 Building Repository: $REPO"
  docker build \
    -f ./dockerfiles/FB_REPO/Dockerfile \
    --build-arg REPO_NAME=$REPO \
    -t fb_${REPO}:dev .

  if [ $? -ne 0 ]; then
    echo "❌ Fail to build: $REPO"
    exit 1
  else
    echo "✅ Build Success: fb_${REPO}:dev"
  fi
done
