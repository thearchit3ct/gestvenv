import * as vscode from 'vscode';
import { GestVenvAPI } from './api/gestvenvClient';
import { PythonCompletionProvider } from './providers/pythonProvider';
import { EnvironmentProvider } from './providers/environmentProvider';
import { EnvironmentExplorer } from './views/environmentExplorer';
import { StatusBarManager } from './views/statusBar';
import { registerCommands } from './commands';
import { DiagnosticProvider } from './providers/diagnosticProvider';
import { GestVenvLanguageClient } from './language/client';

let api: GestVenvAPI;
let statusBar: StatusBarManager;
let environmentExplorer: EnvironmentExplorer;
let languageClient: GestVenvLanguageClient;

export async function activate(context: vscode.ExtensionContext) {
    console.log('GestVenv extension is activating...');

    try {
        // Initialize API client
        const config = vscode.workspace.getConfiguration('gestvenv');
        const apiEndpoint = config.get<string>('apiEndpoint', 'http://localhost:8000');
        api = new GestVenvAPI(apiEndpoint);

        // Test API connection
        const isConnected = await api.testConnection();
        if (!isConnected) {
            vscode.window.showWarningMessage(
                'GestVenv API is not available. Some features may not work.',
                'Open Settings'
            ).then(selection => {
                if (selection === 'Open Settings') {
                    vscode.commands.executeCommand('workbench.action.openSettings', 'gestvenv.apiEndpoint');
                }
            });
        }

        // Initialize status bar
        statusBar = new StatusBarManager(api);
        context.subscriptions.push(statusBar);

        // Initialize environment explorer
        const environmentProvider = new EnvironmentProvider(api);
        environmentExplorer = new EnvironmentExplorer(environmentProvider);
        
        vscode.window.createTreeView('gestvenvEnvironments', {
            treeDataProvider: environmentExplorer,
            showCollapseAll: true
        });

        // Register commands
        registerCommands(context, api, environmentExplorer, statusBar);

        // Initialize Python providers if enabled
        if (config.get<boolean>('enableIntelliSense', true)) {
            // Register completion provider
            const completionProvider = new PythonCompletionProvider(api);
            context.subscriptions.push(
                vscode.languages.registerCompletionItemProvider(
                    { scheme: 'file', language: 'python' },
                    completionProvider,
                    '.', '"', "'", ' '
                )
            );

            // Register hover provider
            context.subscriptions.push(
                vscode.languages.registerHoverProvider(
                    { scheme: 'file', language: 'python' },
                    completionProvider
                )
            );

            // Initialize diagnostic provider
            const diagnosticProvider = new DiagnosticProvider(api);
            context.subscriptions.push(diagnosticProvider);

            // Start language server
            languageClient = new GestVenvLanguageClient(context, api);
            await languageClient.start();
        }

        // Auto-detect environment on startup
        if (config.get<boolean>('autoDetect', true)) {
            await detectAndActivateEnvironment();
        }

        // Watch for workspace changes
        context.subscriptions.push(
            vscode.workspace.onDidChangeWorkspaceFolders(async () => {
                await detectAndActivateEnvironment();
            })
        );

        // Watch for Python file activation
        context.subscriptions.push(
            vscode.window.onDidChangeActiveTextEditor(async (editor) => {
                if (editor?.document.languageId === 'python') {
                    await statusBar.update();
                }
            })
        );

        console.log('GestVenv extension activated successfully');

    } catch (error) {
        console.error('Failed to activate GestVenv extension:', error);
        vscode.window.showErrorMessage(`Failed to activate GestVenv: ${error}`);
    }
}

export function deactivate() {
    console.log('GestVenv extension is deactivating...');
    
    if (languageClient) {
        languageClient.stop();
    }
    
    if (api) {
        api.dispose();
    }
}

async function detectAndActivateEnvironment() {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (!workspaceFolder) {
        return;
    }

    try {
        const environment = await api.detectActiveEnvironment(workspaceFolder.uri.fsPath);
        if (environment) {
            await statusBar.setActiveEnvironment(environment);
            environmentExplorer.refresh();
            
            vscode.window.showInformationMessage(
                `Activated GestVenv environment: ${environment.name}`
            );
        }
    } catch (error) {
        console.error('Failed to detect environment:', error);
    }
}