# GestVenv VS Code Extension

Native VS Code integration for GestVenv - Modern Python virtual environment manager.

## Features

### 🎯 Smart IntelliSense
- **Package-aware completions**: Auto-complete for all packages installed in your GestVenv environment
- **Module discovery**: Automatic discovery of sub-modules and packages
- **Rich documentation**: Inline documentation and package statistics

### 🔄 Automatic Environment Detection
- Detects and activates GestVenv environments automatically
- Shows active environment in status bar
- Quick environment switching

### 📦 Package Management
- Install packages directly from VS Code
- Visual package explorer
- Dependency synchronization

### 🩺 Smart Diagnostics
- Missing import detection
- Quick fixes for package installation
- Real-time validation

### 🎨 Rich UI
- Tree view of all environments
- Package explorer with search
- Environment details panel
- Status bar integration

## Installation

1. Install GestVenv CLI:
   ```bash
   pip install gestvenv
   ```

2. Install the extension from VS Code Marketplace:
   - Search for "GestVenv" in extensions
   - Click Install

## Usage

### Creating an Environment

1. Open Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`)
2. Run `GestVenv: Create Environment`
3. Follow the prompts to select backend and template

### Installing Packages

1. Right-click on an environment in the explorer
2. Select "Install Package"
3. Search and select the package to install

### Switching Environments

Click on the environment name in the status bar to quickly switch between environments.

## Configuration

```json
{
  "gestvenv.enable": true,
  "gestvenv.autoDetect": true,
  "gestvenv.showStatusBar": true,
  "gestvenv.enableIntelliSense": true,
  "gestvenv.apiEndpoint": "http://localhost:8000",
  "gestvenv.cache.enable": true,
  "gestvenv.cache.ttl": 300,
  "gestvenv.diagnostics.enable": true
}
```

## Requirements

- VS Code 1.85.0 or higher
- Python 3.8 or higher
- GestVenv CLI installed and available in PATH
- GestVenv API running (for advanced features)

## Troubleshooting

### Extension not detecting environments

1. Ensure GestVenv CLI is installed: `gestvenv --version`
2. Check that the workspace contains Python files
3. Verify API endpoint in settings if using advanced features

### IntelliSense not working

1. Ensure `gestvenv.enableIntelliSense` is enabled
2. Check that the environment is activated (shown in status bar)
3. Reload the window after environment changes

## Contributing

Visit our [GitHub repository](https://github.com/gestvenv/gestvenv) to contribute or report issues.

## License

MIT License - see LICENSE file for details.