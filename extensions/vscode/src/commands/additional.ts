import * as vscode from 'vscode';
import { GestVenvAPI, Environment } from '../api/gestvenvClient';
import { EnvironmentExplorer } from '../views/environmentExplorer';
import { StatusBarManager } from '../views/statusBar';
import { EnvironmentDetector, createGestvenvConfig } from '../utils/detection';

/**
 * Enregistre les commandes supplémentaires
 */
export function registerAdditionalCommands(
    context: vscode.ExtensionContext,
    api: GestVenvAPI,
    explorer: EnvironmentExplorer,
    statusBar: StatusBarManager
) {
    const detector = new EnvironmentDetector(api);

    // Run Diagnostic
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.runDiagnostic', async () => {
            await runDiagnosticCommand(api);
        })
    );

    // Show Environment Info
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.showEnvironmentInfo', async () => {
            await showEnvironmentInfoCommand(api, statusBar);
        })
    );

    // Open Web UI
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.openWebUI', () => {
            openWebUICommand();
        })
    );

    // Open Shell
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.openShell', async () => {
            await openShellCommand(statusBar);
        })
    );

    // Migrate Environment
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.migrateEnvironment', async (envPath?: string) => {
            await migrateEnvironmentCommand(api, explorer, statusBar, envPath);
        })
    );

    // Install Package from Cursor
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.installFromCursor', async () => {
            await installFromCursorCommand(api, explorer, statusBar);
        })
    );

    // Show Package Info
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.showPackageInfo', async () => {
            await showPackageInfoCommand(api, statusBar);
        })
    );

    // Update All Packages
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.updateAllPackages', async () => {
            await updateAllPackagesCommand(api, explorer, statusBar);
        })
    );

    // Start file watchers
    const watchers = detector.startWatching();
    context.subscriptions.push(...watchers);
    context.subscriptions.push({ dispose: () => detector.dispose() });
}

/**
 * Exécute un diagnostic complet
 */
async function runDiagnosticCommand(api: GestVenvAPI): Promise<void> {
    const outputChannel = vscode.window.createOutputChannel('GestVenv Diagnostic');
    outputChannel.show();
    outputChannel.appendLine('=== GestVenv Diagnostic ===');
    outputChannel.appendLine(`Date: ${new Date().toISOString()}`);
    outputChannel.appendLine('');

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Exécution du diagnostic...',
        cancellable: false
    }, async (progress) => {
        try {
            // Test API connection
            progress.report({ increment: 20, message: 'Test connexion API...' });
            const isConnected = await api.testConnection();
            outputChannel.appendLine(`API Connection: ${isConnected ? '✅ OK' : '❌ Failed'}`);

            if (isConnected) {
                // List environments
                progress.report({ increment: 20, message: 'Liste des environnements...' });
                const environments = await api.listEnvironments();
                outputChannel.appendLine(`\nEnvironments: ${environments.length} found`);

                for (const env of environments) {
                    outputChannel.appendLine(`  - ${env.name} (Python ${env.python_version}, ${env.backend})`);
                    outputChannel.appendLine(`    Path: ${env.path}`);
                    outputChannel.appendLine(`    Packages: ${env.package_count}`);
                }

                // Check workspace
                progress.report({ increment: 20, message: 'Analyse du workspace...' });
                const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
                if (workspaceFolder) {
                    outputChannel.appendLine(`\nWorkspace: ${workspaceFolder.uri.fsPath}`);

                    const detector = new EnvironmentDetector(api);
                    const detection = await detector.detectEnvironment();
                    outputChannel.appendLine(`Detected environment type: ${detection.type}`);
                    if (detection.path) {
                        outputChannel.appendLine(`Environment path: ${detection.path}`);
                    }

                    const config = await detector.analyzeProjectConfig();
                    outputChannel.appendLine('\nProject files:');
                    outputChannel.appendLine(`  requirements.txt: ${config.hasRequirementsTxt ? '✅' : '❌'}`);
                    outputChannel.appendLine(`  pyproject.toml: ${config.hasPyprojectToml ? '✅' : '❌'}`);
                    outputChannel.appendLine(`  setup.py: ${config.hasSetupPy ? '✅' : '❌'}`);
                    outputChannel.appendLine(`  .gestvenv: ${config.hasGestvenvConfig ? '✅' : '❌'}`);

                    if (config.dependencies.length > 0) {
                        outputChannel.appendLine(`\nDependencies found: ${config.dependencies.length}`);
                        config.dependencies.slice(0, 10).forEach(dep => {
                            outputChannel.appendLine(`  - ${dep}`);
                        });
                        if (config.dependencies.length > 10) {
                            outputChannel.appendLine(`  ... and ${config.dependencies.length - 10} more`);
                        }
                    }

                    detector.dispose();
                } else {
                    outputChannel.appendLine('\nNo workspace folder open');
                }

                // System info
                progress.report({ increment: 20, message: 'Informations système...' });
                outputChannel.appendLine('\nSystem Information:');
                outputChannel.appendLine(`  VS Code: ${vscode.version}`);
                outputChannel.appendLine(`  Platform: ${process.platform}`);
                outputChannel.appendLine(`  Node: ${process.version}`);
            }

            progress.report({ increment: 20, message: 'Terminé' });
            outputChannel.appendLine('\n=== Diagnostic Complete ===');

            vscode.window.showInformationMessage(
                'Diagnostic terminé. Voir la sortie pour les détails.',
                'Voir la sortie'
            ).then(selection => {
                if (selection) {
                    outputChannel.show();
                }
            });

        } catch (error: any) {
            outputChannel.appendLine(`\n❌ Error: ${error.message}`);
            vscode.window.showErrorMessage(`Diagnostic failed: ${error.message}`);
        }
    });
}

/**
 * Affiche les informations de l'environnement actif
 */
async function showEnvironmentInfoCommand(api: GestVenvAPI, statusBar: StatusBarManager): Promise<void> {
    const activeEnv = statusBar.getActiveEnvironment();

    if (!activeEnv) {
        vscode.window.showInformationMessage(
            'Aucun environnement actif. Sélectionnez-en un d\'abord.',
            'Sélectionner'
        ).then(selection => {
            if (selection) {
                vscode.commands.executeCommand('gestvenv.selectEnvironment');
            }
        });
        return;
    }

    const info = [
        `**Nom:** ${activeEnv.name}`,
        `**Python:** ${activeEnv.python_version}`,
        `**Backend:** ${activeEnv.backend}`,
        `**Packages:** ${activeEnv.package_count}`,
        `**Chemin:** ${activeEnv.path}`,
        `**Créé le:** ${new Date(activeEnv.created_at).toLocaleDateString()}`
    ].join('\n\n');

    const selection = await vscode.window.showInformationMessage(
        `Environnement: ${activeEnv.name}`,
        { modal: false },
        'Voir les packages',
        'Ouvrir le terminal',
        'Copier le chemin'
    );

    switch (selection) {
        case 'Voir les packages':
            vscode.commands.executeCommand('gestvenv.showEnvironmentDetails', activeEnv);
            break;
        case 'Ouvrir le terminal':
            vscode.commands.executeCommand('gestvenv.openShell');
            break;
        case 'Copier le chemin':
            await vscode.env.clipboard.writeText(activeEnv.path);
            vscode.window.showInformationMessage('Chemin copié dans le presse-papiers');
            break;
    }
}

/**
 * Ouvre l'interface Web GestVenv
 */
function openWebUICommand(): void {
    const config = vscode.workspace.getConfiguration('gestvenv');
    const webUIUrl = config.get<string>('webUIUrl', 'http://localhost:5173');

    vscode.env.openExternal(vscode.Uri.parse(webUIUrl));
}

/**
 * Ouvre un terminal avec l'environnement activé
 */
async function openShellCommand(statusBar: StatusBarManager): Promise<void> {
    const activeEnv = statusBar.getActiveEnvironment();

    if (!activeEnv) {
        const selection = await vscode.window.showWarningMessage(
            'Aucun environnement actif.',
            'Sélectionner un environnement'
        );

        if (selection) {
            vscode.commands.executeCommand('gestvenv.selectEnvironment');
        }
        return;
    }

    const terminal = vscode.window.createTerminal({
        name: `GestVenv: ${activeEnv.name}`,
        env: {
            'VIRTUAL_ENV': activeEnv.path,
            'PATH': `${activeEnv.path}/bin:${process.env.PATH}`
        }
    });

    // Activer l'environnement
    terminal.sendText(`source "${activeEnv.path}/bin/activate" 2>/dev/null || . "${activeEnv.path}/Scripts/activate" 2>/dev/null`);
    terminal.show();
}

/**
 * Migre un environnement existant vers GestVenv
 */
async function migrateEnvironmentCommand(
    api: GestVenvAPI,
    explorer: EnvironmentExplorer,
    statusBar: StatusBarManager,
    envPath?: string
): Promise<void> {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (!workspaceFolder) {
        vscode.window.showErrorMessage('Ouvrez un dossier de workspace d\'abord');
        return;
    }

    // Si pas de chemin fourni, demander à l'utilisateur
    if (!envPath) {
        const detector = new EnvironmentDetector(api);
        const detection = await detector.detectEnvironment();
        detector.dispose();

        if (detection.found && detection.path && detection.type !== 'gestvenv') {
            envPath = detection.path;
        } else {
            const input = await vscode.window.showInputBox({
                prompt: 'Chemin vers l\'environnement à migrer',
                placeHolder: '.venv, venv, ou chemin complet'
            });

            if (!input) return;
            envPath = input;
        }
    }

    const name = await vscode.window.showInputBox({
        prompt: 'Nom du nouvel environnement GestVenv',
        value: workspaceFolder.name,
        validateInput: (value) => {
            if (!value) return 'Le nom est requis';
            if (!/^[a-zA-Z0-9-_]+$/.test(value)) {
                return 'Le nom ne peut contenir que des lettres, chiffres, tirets et underscores';
            }
            return null;
        }
    });

    if (!name) return;

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Migration en cours...',
        cancellable: false
    }, async (progress) => {
        try {
            progress.report({ increment: 30, message: 'Analyse de l\'environnement...' });

            const result = await api.migrateEnvironment({
                source_path: envPath!,
                name: name,
                workspace_path: workspaceFolder.uri.fsPath
            });

            progress.report({ increment: 70, message: 'Finalisation...' });

            if (result.success && result.environment) {
                // Créer le fichier de configuration
                await createGestvenvConfig(workspaceFolder.uri.fsPath, result.environment.id);

                explorer.refresh();
                await statusBar.setActiveEnvironment(result.environment);

                vscode.window.showInformationMessage(
                    `Migration réussie! Environnement ${name} créé.`,
                    'Voir les packages'
                ).then(selection => {
                    if (selection) {
                        vscode.commands.executeCommand('gestvenv.showEnvironmentDetails', result.environment);
                    }
                });
            } else {
                vscode.window.showErrorMessage(`Migration échouée: ${result.message}`);
            }
        } catch (error: any) {
            vscode.window.showErrorMessage(`Erreur de migration: ${error.message}`);
        }
    });
}

/**
 * Installe un package depuis la position du curseur
 */
async function installFromCursorCommand(
    api: GestVenvAPI,
    explorer: EnvironmentExplorer,
    statusBar: StatusBarManager
): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document.languageId !== 'python') {
        vscode.window.showWarningMessage('Cette commande fonctionne uniquement dans les fichiers Python');
        return;
    }

    const activeEnv = statusBar.getActiveEnvironment();
    if (!activeEnv) {
        vscode.window.showWarningMessage('Aucun environnement actif');
        return;
    }

    // Extraire le nom du package depuis la ligne courante
    const line = editor.document.lineAt(editor.selection.active.line);
    const importMatch = line.text.match(/(?:from|import)\s+([a-zA-Z0-9_]+)/);

    if (!importMatch) {
        // Essayer d'extraire le mot sous le curseur
        const wordRange = editor.document.getWordRangeAtPosition(editor.selection.active);
        if (wordRange) {
            const word = editor.document.getText(wordRange);
            await installPackageWithConfirmation(api, activeEnv, word, explorer);
        } else {
            vscode.window.showWarningMessage('Impossible de détecter le nom du package');
        }
        return;
    }

    const packageName = importMatch[1];
    await installPackageWithConfirmation(api, activeEnv, packageName, explorer);
}

async function installPackageWithConfirmation(
    api: GestVenvAPI,
    env: Environment,
    packageName: string,
    explorer: EnvironmentExplorer
): Promise<void> {
    // Vérifier si le package existe sur PyPI
    const exists = await api.checkPackageExists(packageName);
    if (!exists) {
        vscode.window.showWarningMessage(`Package "${packageName}" non trouvé sur PyPI`);
        return;
    }

    const selection = await vscode.window.showInformationMessage(
        `Installer "${packageName}" dans ${env.name}?`,
        'Installer',
        'Annuler'
    );

    if (selection !== 'Installer') return;

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: `Installation de ${packageName}...`,
        cancellable: false
    }, async () => {
        try {
            const result = await api.installPackage(env.id, packageName, {});
            if (result.success) {
                explorer.refresh();
                vscode.window.showInformationMessage(`${packageName} installé avec succès`);
            } else {
                vscode.window.showErrorMessage(`Échec de l'installation: ${result.message}`);
            }
        } catch (error: any) {
            vscode.window.showErrorMessage(`Erreur: ${error.message}`);
        }
    });
}

/**
 * Affiche les informations d'un package
 */
async function showPackageInfoCommand(api: GestVenvAPI, statusBar: StatusBarManager): Promise<void> {
    const activeEnv = statusBar.getActiveEnvironment();
    if (!activeEnv) {
        vscode.window.showWarningMessage('Aucun environnement actif');
        return;
    }

    const packageName = await vscode.window.showInputBox({
        prompt: 'Nom du package',
        placeHolder: 'requests'
    });

    if (!packageName) return;

    try {
        const packageInfo = await api.getPackageInfo(packageName);

        if (packageInfo) {
            const panel = vscode.window.createWebviewPanel(
                'gestvenvPackageInfo',
                `Package: ${packageName}`,
                vscode.ViewColumn.One,
                {}
            );

            panel.webview.html = `
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
        h1 { border-bottom: 1px solid var(--vscode-panel-border); padding-bottom: 10px; }
        .info { margin: 10px 0; }
        .label { font-weight: bold; color: var(--vscode-descriptionForeground); }
        a { color: var(--vscode-textLink-foreground); }
    </style>
</head>
<body>
    <h1>${packageInfo.name} ${packageInfo.version}</h1>

    ${packageInfo.description ? `<div class="info">${packageInfo.description}</div>` : ''}

    <div class="info">
        <span class="label">Version:</span> ${packageInfo.version}
    </div>

    ${packageInfo.author ? `
    <div class="info">
        <span class="label">Auteur:</span> ${packageInfo.author}
    </div>
    ` : ''}

    ${packageInfo.license ? `
    <div class="info">
        <span class="label">Licence:</span> ${packageInfo.license}
    </div>
    ` : ''}

    ${packageInfo.home_page ? `
    <div class="info">
        <span class="label">Site web:</span>
        <a href="${packageInfo.home_page}">${packageInfo.home_page}</a>
    </div>
    ` : ''}

    <div class="info">
        <span class="label">PyPI:</span>
        <a href="https://pypi.org/project/${packageName}/">https://pypi.org/project/${packageName}/</a>
    </div>
</body>
</html>
            `;
        } else {
            vscode.window.showWarningMessage(`Package "${packageName}" non trouvé`);
        }
    } catch (error: any) {
        vscode.window.showErrorMessage(`Erreur: ${error.message}`);
    }
}

/**
 * Met à jour tous les packages
 */
async function updateAllPackagesCommand(
    api: GestVenvAPI,
    explorer: EnvironmentExplorer,
    statusBar: StatusBarManager
): Promise<void> {
    const activeEnv = statusBar.getActiveEnvironment();
    if (!activeEnv) {
        vscode.window.showWarningMessage('Aucun environnement actif');
        return;
    }

    const confirm = await vscode.window.showWarningMessage(
        `Mettre à jour tous les packages de ${activeEnv.name}?`,
        'Oui',
        'Non'
    );

    if (confirm !== 'Oui') return;

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Mise à jour des packages...',
        cancellable: false
    }, async (progress) => {
        try {
            progress.report({ increment: 30, message: 'Vérification des mises à jour...' });

            const result = await api.updateAllPackages(activeEnv.id);

            progress.report({ increment: 70, message: 'Finalisation...' });

            if (result.success) {
                explorer.refresh();
                vscode.window.showInformationMessage(
                    `${result.updated_count} package(s) mis à jour dans ${activeEnv.name}`
                );
            } else {
                vscode.window.showErrorMessage(`Échec de la mise à jour: ${result.message}`);
            }
        } catch (error: any) {
            vscode.window.showErrorMessage(`Erreur: ${error.message}`);
        }
    });
}
