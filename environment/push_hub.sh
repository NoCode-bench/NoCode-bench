#!/bin/bash

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


docker login
if [ $? -ne 0 ]; then
  echo "❌ Docker login failed"
  exit 1
fi

for REPO in "${REPOS[@]}"; do
  LOCAL_TAG="fb_${REPO}:dev"
  REMOTE_TAG="nocodebench/nocode-bench:${REPO}"

  echo "🏷️  Tagging $LOCAL_TAG -> $REMOTE_TAG"
  docker tag "$LOCAL_TAG" "$REMOTE_TAG"

  echo "📤 Pushing $REMOTE_TAG"
  docker push "$REMOTE_TAG"

  if [ $? -ne 0 ]; then
    echo "❌ Failed to push: $REMOTE_TAG"
    exit 1
  else
    echo "✅ Push Success: $REMOTE_TAG"
  fi
done
