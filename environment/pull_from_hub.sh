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

for REPO in "${REPOS[@]}"; do
  REMOTE_TAG="nocodebench/nocode-bench:${REPO}"
  LOCAL_TAG="fb_${REPO}:dev"

  echo "⬇️  Pulling $REMOTE_TAG"
  docker pull "$REMOTE_TAG"

  if [ $? -ne 0 ]; then
    echo "❌ Failed to pull: $REMOTE_TAG"
    exit 1
  fi

  echo "🏷️  Retagging $REMOTE_TAG -> $LOCAL_TAG"
  docker tag "$REMOTE_TAG" "$LOCAL_TAG"

  echo "✅ Done: $LOCAL_TAG"
done
