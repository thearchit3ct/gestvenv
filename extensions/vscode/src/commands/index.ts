import * as vscode from 'vscode';
import { GestVenvAPI, Environment } from '../api/gestvenvClient';
import { EnvironmentExplorer } from '../views/environmentExplorer';
import { StatusBarManager } from '../views/statusBar';

export function registerCommands(
    context: vscode.ExtensionContext,
    api: GestVenvAPI,
    explorer: EnvironmentExplorer,
    statusBar: StatusBarManager
) {
    // Create Environment
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.createEnvironment', async () => {
            await createEnvironmentCommand(api, explorer, statusBar);
        })
    );

    // Select Environment
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.selectEnvironment', async () => {
            await selectEnvironmentCommand(api, statusBar);
        })
    );

    // Install Package
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.installPackage', async (env?: Environment) => {
            await installPackageCommand(api, env, explorer);
        })
    );

    // Sync Dependencies
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.syncDependencies', async (env?: Environment) => {
            await syncDependenciesCommand(api, env, explorer);
        })
    );

    // Refresh Environments
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.refreshEnvironments', () => {
            explorer.refresh();
            statusBar.update();
        })
    );

    // Show Environment Details
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.showEnvironmentDetails', async (env: Environment) => {
            await showEnvironmentDetailsCommand(api, env);
        })
    );

    // Run in Environment
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.runInEnvironment', async (env?: Environment) => {
            await runInEnvironmentCommand(api, env);
        })
    );

    // Show Package Details
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.showPackageDetails', async (pkg: any, env: Environment) => {
            await showPackageDetailsCommand(pkg, env);
        })
    );

    // Show Environment Actions
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.showEnvironmentActions', async (env: Environment) => {
            await showEnvironmentActionsCommand(api, env, explorer);
        })
    );

    // Delete Environment
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.deleteEnvironment', async (env?: Environment) => {
            await deleteEnvironmentCommand(api, env, explorer);
        })
    );

    // Activate Environment
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.activateEnvironment', async (env?: Environment) => {
            if (!env) {
                await selectEnvironmentCommand(api, statusBar);
            } else {
                await statusBar.setActiveEnvironment(env);
                vscode.window.showInformationMessage(`Activated environment: ${env.name}`);
            }
        })
    );

    // Uninstall Package
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.uninstallPackage', async (env?: Environment) => {
            await uninstallPackageCommand(api, env, explorer);
        })
    );

    // Refresh (alias for refreshEnvironments)
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.refresh', () => {
            explorer.refresh();
            statusBar.update();
        })
    );

    // Show Settings
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.showSettings', () => {
            vscode.commands.executeCommand('workbench.action.openSettings', 'gestvenv');
        })
    );

    // Show Environment Quick Pick
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.showEnvironmentQuickPick', async () => {
            await selectEnvironmentCommand(api, statusBar);
        })
    );
}

async function createEnvironmentCommand(
    api: GestVenvAPI,
    explorer: EnvironmentExplorer,
    statusBar: StatusBarManager
) {
    const name = await vscode.window.showInputBox({
        prompt: 'Environment name',
        placeHolder: 'my-project',
        validateInput: (value) => {
            if (!value) return 'Name is required';
            if (!/^[a-zA-Z0-9-_]+$/.test(value)) {
                return 'Name can only contain letters, numbers, hyphens, and underscores';
            }
            return null;
        }
    });

    if (!name) return;

    const backends = ['uv', 'pip', 'pdm', 'poetry'];
    const backend = await vscode.window.showQuickPick(backends, {
        placeHolder: 'Select backend (recommended: uv for speed)'
    });

    if (!backend) return;

    const templates = [
        { label: 'Empty', value: null },
        { label: 'Django', value: 'django' },
        { label: 'FastAPI', value: 'fastapi' },
        { label: 'Data Science', value: 'data-science' },
        { label: 'CLI Application', value: 'cli' }
    ];

    const template = await vscode.window.showQuickPick(templates, {
        placeHolder: 'Select project template (optional)'
    });

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: `Creating environment ${name}...`,
        cancellable: false
    }, async (progress) => {
        try {
            progress.report({ increment: 30, message: 'Initializing...' });
            
            const env = await api.createEnvironment({
                name,
                backend,
                template: template?.value ?? undefined
            });

            progress.report({ increment: 70, message: 'Finalizing...' });
            
            explorer.refresh();
            await statusBar.setActiveEnvironment(env);
            
            vscode.window.showInformationMessage(
                `Environment ${env.name} created successfully!`,
                'Install Packages',
                'Open Terminal'
            ).then(selection => {
                if (selection === 'Install Packages') {
                    vscode.commands.executeCommand('gestvenv.installPackage', env);
                } else if (selection === 'Open Terminal') {
                    const terminal = vscode.window.createTerminal(`GestVenv: ${env.name}`);
                    terminal.sendText(`gestvenv shell --env ${env.name}`);
                    terminal.show();
                }
            });
            
        } catch (error: any) {
            vscode.window.showErrorMessage(`Failed to create environment: ${error.message}`);
        }
    });
}

async function selectEnvironmentCommand(api: GestVenvAPI, statusBar: StatusBarManager) {
    try {
        const environments = await api.listEnvironments();
        
        if (environments.length === 0) {
            const create = await vscode.window.showInformationMessage(
                'No environments found',
                'Create New'
            );
            
            if (create) {
                vscode.commands.executeCommand('gestvenv.createEnvironment');
            }
            return;
        }

        const items = environments.map(env => ({
            label: env.name,
            description: `${env.python_version} - ${env.backend}`,
            detail: `${env.package_count} packages • ${env.path}`,
            env
        }));

        const selected = await vscode.window.showQuickPick(items, {
            placeHolder: 'Select environment to activate'
        });

        if (selected) {
            await statusBar.setActiveEnvironment(selected.env);
            vscode.window.showInformationMessage(
                `Activated environment: ${selected.env.name}`
            );
        }
    } catch (error: any) {
        vscode.window.showErrorMessage(`Failed to list environments: ${error.message}`);
    }
}

async function installPackageCommand(
    api: GestVenvAPI,
    env: Environment | undefined,
    explorer: EnvironmentExplorer
) {
    if (!env) {
        vscode.window.showErrorMessage('No environment selected');
        return;
    }

    const packageName = await vscode.window.showInputBox({
        prompt: 'Package name to install',
        placeHolder: 'requests',
        validateInput: async (value) => {
            if (!value) return 'Package name is required';
            
            // Show checking status
            const exists = await api.checkPackageExists(value);
            if (!exists) {
                return `Package ${value} not found on PyPI`;
            }
            
            return null;
        }
    });

    if (!packageName) return;

    const options = [
        { label: 'Latest version', value: 'latest' },
        { label: 'Specific version', value: 'version' },
        { label: 'From Git repository', value: 'git' },
        { label: 'Editable install (-e)', value: 'editable' }
    ];

    const option = await vscode.window.showQuickPick(options, {
        placeHolder: 'Installation options'
    });

    let installOptions: any = {};

    if (option?.value === 'version') {
        const version = await vscode.window.showInputBox({
            prompt: 'Version to install',
            placeHolder: '2.28.0'
        });
        if (version) {
            installOptions.version = version;
        }
    } else if (option?.value === 'editable') {
        installOptions.editable = true;
    }

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: `Installing ${packageName}...`,
        cancellable: false
    }, async (progress) => {
        try {
            progress.report({ increment: 30, message: 'Downloading...' });
            
            const result = await api.installPackage(env.id, packageName, installOptions);
            
            progress.report({ increment: 70, message: 'Finalizing...' });
            
            if (result.success) {
                explorer.refresh();
                vscode.window.showInformationMessage(
                    `Successfully installed ${packageName} in ${env.name}`
                );
            } else {
                vscode.window.showErrorMessage(
                    `Failed to install ${packageName}: ${result.message}`
                );
            }
        } catch (error: any) {
            vscode.window.showErrorMessage(
                `Failed to install package: ${error.message}`
            );
        }
    });
}

async function syncDependenciesCommand(
    api: GestVenvAPI,
    env: Environment | undefined,
    explorer: EnvironmentExplorer
) {
    if (!env) {
        vscode.window.showErrorMessage('No environment selected');
        return;
    }

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: `Syncing dependencies for ${env.name}...`,
        cancellable: false
    }, async (progress) => {
        try {
            progress.report({ increment: 50, message: 'Analyzing dependencies...' });
            
            const result = await api.syncDependencies(env.id);
            
            if (result.success) {
                explorer.refresh();
                vscode.window.showInformationMessage(
                    `Dependencies synced successfully for ${env.name}`
                );
            } else {
                vscode.window.showErrorMessage(
                    `Failed to sync dependencies: ${result.message}`
                );
            }
        } catch (error: any) {
            vscode.window.showErrorMessage(
                `Failed to sync dependencies: ${error.message}`
            );
        }
    });
}

async function showEnvironmentDetailsCommand(api: GestVenvAPI, env: Environment) {
    const panel = vscode.window.createWebviewPanel(
        'gestvenvEnvironmentDetails',
        `Environment: ${env.name}`,
        vscode.ViewColumn.One,
        {
            enableScripts: true
        }
    );

    const packages = await api.getPackages(env.id);
    
    panel.webview.html = getEnvironmentDetailsHtml(env, packages);
}

async function runInEnvironmentCommand(api: GestVenvAPI, env: Environment | undefined) {
    if (!env) {
        vscode.window.showErrorMessage('No environment selected');
        return;
    }

    const command = await vscode.window.showInputBox({
        prompt: 'Command to run',
        placeHolder: 'python script.py'
    });

    if (!command) return;

    const outputChannel = vscode.window.createOutputChannel(`GestVenv: ${env.name}`);
    outputChannel.show();
    
    outputChannel.appendLine(`Running: ${command}`);
    outputChannel.appendLine('---');

    try {
        const result = await api.runCommand(env.id, command);
        
        if (result.stdout) {
            outputChannel.appendLine(result.stdout);
        }
        
        if (result.stderr) {
            outputChannel.appendLine('STDERR:');
            outputChannel.appendLine(result.stderr);
        }
        
        outputChannel.appendLine('---');
        outputChannel.appendLine(`Exit code: ${result.returncode}`);
        
    } catch (error: any) {
        outputChannel.appendLine(`ERROR: ${error.message}`);
    }
}

async function showPackageDetailsCommand(pkg: any, env: Environment) {
    const panel = vscode.window.createWebviewPanel(
        'gestvenvPackageDetails',
        `Package: ${pkg.name}`,
        vscode.ViewColumn.One,
        {}
    );

    panel.webview.html = getPackageDetailsHtml(pkg, env);
}

async function showEnvironmentActionsCommand(
    api: GestVenvAPI,
    env: Environment,
    explorer: EnvironmentExplorer
) {
    const actions = [
        { label: '$(package) Install Package', value: 'install' },
        { label: '$(sync) Sync Dependencies', value: 'sync' },
        { label: '$(terminal) Open Terminal', value: 'terminal' },
        { label: '$(play) Run Command', value: 'run' },
        { label: '$(info) Show Details', value: 'details' }
    ];

    const selected = await vscode.window.showQuickPick(actions, {
        placeHolder: `Actions for ${env.name}`
    });

    if (!selected) return;

    switch (selected.value) {
        case 'install':
            vscode.commands.executeCommand('gestvenv.installPackage', env);
            break;
        case 'sync':
            vscode.commands.executeCommand('gestvenv.syncDependencies', env);
            break;
        case 'terminal':
            const terminal = vscode.window.createTerminal(`GestVenv: ${env.name}`);
            terminal.sendText(`gestvenv shell --env ${env.name}`);
            terminal.show();
            break;
        case 'run':
            vscode.commands.executeCommand('gestvenv.runInEnvironment', env);
            break;
        case 'details':
            vscode.commands.executeCommand('gestvenv.showEnvironmentDetails', env);
            break;
    }
}

function getEnvironmentDetailsHtml(env: Environment, packages: any[]): string {
    return `
<!DOCTYPE html>
<html>
<head>
    <style>
        body {
            font-family: var(--vscode-font-family);
            color: var(--vscode-foreground);
            background-color: var(--vscode-editor-background);
            padding: 20px;
        }
        h1, h2 {
            border-bottom: 1px solid var(--vscode-panel-border);
            padding-bottom: 10px;
        }
        .info-grid {
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 10px;
            margin: 20px 0;
        }
        .label {
            font-weight: bold;
            color: var(--vscode-descriptionForeground);
        }
        .package-list {
            margin-top: 20px;
        }
        .package {
            padding: 10px;
            margin: 5px 0;
            background-color: var(--vscode-editor-inactiveSelectionBackground);
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <h1>${env.name}</h1>
    
    <div class="info-grid">
        <span class="label">Python Version:</span>
        <span>${env.python_version}</span>
        
        <span class="label">Backend:</span>
        <span>${env.backend}</span>
        
        <span class="label">Path:</span>
        <span>${env.path}</span>
        
        <span class="label">Created:</span>
        <span>${new Date(env.created_at).toLocaleString()}</span>
        
        <span class="label">Status:</span>
        <span>${env.is_active ? 'Active' : 'Inactive'}</span>
    </div>
    
    <h2>Installed Packages (${packages.length})</h2>
    <div class="package-list">
        ${packages.map(pkg => `
            <div class="package">
                <strong>${pkg.name}</strong> ${pkg.version}
                ${pkg.description ? `<br><small>${pkg.description}</small>` : ''}
            </div>
        `).join('')}
    </div>
</body>
</html>
    `;
}

async function deleteEnvironmentCommand(
    api: GestVenvAPI,
    env: Environment | undefined,
    explorer: EnvironmentExplorer
) {
    if (!env) {
        vscode.window.showErrorMessage('No environment selected');
        return;
    }

    const confirm = await vscode.window.showWarningMessage(
        `Are you sure you want to delete environment '${env.name}'?`,
        'Yes',
        'No'
    );

    if (confirm !== 'Yes') {
        return;
    }

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: `Deleting environment ${env.name}...`,
        cancellable: false
    }, async (progress) => {
        try {
            progress.report({ increment: 50, message: 'Removing files...' });
            
            const result = await api.deleteEnvironment(env.id);
            
            if (result.success) {
                explorer.refresh();
                vscode.window.showInformationMessage(
                    `Environment ${env.name} deleted successfully`
                );
            } else {
                vscode.window.showErrorMessage(
                    `Failed to delete environment: ${result.message}`
                );
            }
        } catch (error: any) {
            vscode.window.showErrorMessage(
                `Failed to delete environment: ${error.message}`
            );
        }
    });
}

async function uninstallPackageCommand(
    api: GestVenvAPI,
    env: Environment | undefined,
    explorer: EnvironmentExplorer
) {
    if (!env) {
        vscode.window.showErrorMessage('No environment selected');
        return;
    }

    const packages = await api.getPackages(env.id);
    
    if (packages.length === 0) {
        vscode.window.showInformationMessage('No packages installed in this environment');
        return;
    }

    const items = packages.map(pkg => ({
        label: pkg.name,
        description: pkg.version,
        pkg
    }));

    const selected = await vscode.window.showQuickPick(items, {
        placeHolder: 'Select package to uninstall',
        canPickMany: true
    });

    if (!selected || selected.length === 0) {
        return;
    }

    const packageNames = selected.map(item => item.pkg.name);
    const packageList = packageNames.join(', ');

    const confirm = await vscode.window.showWarningMessage(
        `Uninstall ${packageList}?`,
        'Yes',
        'No'
    );

    if (confirm !== 'Yes') {
        return;
    }

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: `Uninstalling packages...`,
        cancellable: false
    }, async (progress) => {
        try {
            progress.report({ increment: 50, message: 'Removing packages...' });
            
            const result = await api.uninstallPackages(env.id, packageNames);
            
            if (result.success) {
                explorer.refresh();
                vscode.window.showInformationMessage(
                    `Successfully uninstalled ${packageList}`
                );
            } else {
                vscode.window.showErrorMessage(
                    `Failed to uninstall packages: ${result.message}`
                );
            }
        } catch (error: any) {
            vscode.window.showErrorMessage(
                `Failed to uninstall packages: ${error.message}`
            );
        }
    });
}

function getPackageDetailsHtml(pkg: any, env: Environment): string {
    return `
<!DOCTYPE html>
<html>
<head>
    <style>
        body {
            font-family: var(--vscode-font-family);
            color: var(--vscode-foreground);
            background-color: var(--vscode-editor-background);
            padding: 20px;
        }
        h1 {
            border-bottom: 1px solid var(--vscode-panel-border);
            padding-bottom: 10px;
        }
        .info {
            margin: 10px 0;
        }
        .label {
            font-weight: bold;
            color: var(--vscode-descriptionForeground);
        }
    </style>
</head>
<body>
    <h1>${pkg.name} ${pkg.version}</h1>
    
    <div class="info">
        <span class="label">Environment:</span> ${env.name}
    </div>
    
    ${pkg.description ? `
    <div class="info">
        <span class="label">Description:</span><br>
        ${pkg.description}
    </div>
    ` : ''}
    
    ${pkg.metadata?.home_page ? `
    <div class="info">
        <span class="label">Homepage:</span> 
        <a href="${pkg.metadata.home_page}">${pkg.metadata.home_page}</a>
    </div>
    ` : ''}
    
    ${pkg.metadata?.author ? `
    <div class="info">
        <span class="label">Author:</span> ${pkg.metadata.author}
    </div>
    ` : ''}
    
    ${pkg.metadata?.license ? `
    <div class="info">
        <span class="label">License:</span> ${pkg.metadata.license}
    </div>
    ` : ''}
</body>
</html>
    `;
}