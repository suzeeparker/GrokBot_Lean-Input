#!/bin/bash
# Copies skill-prompts from this workspace to the global Amazon Q prompts folder

SRC="$(dirname "$0")/../skill-prompts"
DEST="$HOME/.aws/amazonq/prompts"

mkdir -p "$DEST"
cp "$SRC"/*.md "$DEST"/
echo "Copied prompts from $SRC to $DEST"
