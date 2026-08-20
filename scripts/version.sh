#!/usr/bin/env bash
set -e
VER=${1:-patch} # patch|minor|major
CUR=$(cat VERSION 2>/dev/null || echo "0.1.0-beta")
# simple bump for beta
NEW=$(echo $CUR | awk -F. '{print $1"." $2 "." ($3+1)}')
echo $NEW | cut -d- -f1 > VERSION
for d in services/*/; do echo $(cat VERSION) > $d/VERSION; done
echo "bumped $CUR -> $(cat VERSION)"
