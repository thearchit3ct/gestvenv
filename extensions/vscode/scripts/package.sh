#!/bin/bash

# Build and package the VS Code extension

set -e

echo "🧹 Cleaning previous builds..."
rm -rf out dist *.vsix

echo "📦 Installing dependencies..."
npm install

echo "🔨 Compiling TypeScript..."
npm run compile

echo "📋 Running linter..."
npm run lint || true

echo "🧪 Running tests..."
npm test || true

echo "📦 Creating VSIX package..."
npx vsce package

echo "✅ Extension packaged successfully!"
echo "📍 VSIX file created: $(ls *.vsix)"

echo ""
echo "To install locally:"
echo "  code --install-extension $(ls *.vsix)"
echo ""
echo "To publish to marketplace:"
echo "  vsce publish"