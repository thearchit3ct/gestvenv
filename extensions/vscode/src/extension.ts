import * as vscode from 'vscode';
import { GestVenvAPI } from './api/gestvenvClient';
import { PythonCompletionProvider } from './providers/pythonProvider';
import { EnvironmentProvider } from './providers/environmentProvider';
import { EnvironmentExplorer } from './views/environmentExplorer';
import { StatusBarManager } from './views/statusBar';
import { registerCommands } from './commands';
import { DiagnosticProvider } from './providers/diagnosticProvider';
import { GestVenvLanguageClient } from './language/client';
import { CodeActionProvider } from './providers/codeActionProvider';
import { WebSocketClient } from './websocket/client';
import { registerRefactoringCommands } from './commands/refactoring';

let api: GestVenvAPI;
let statusBar: StatusBarManager;
let environmentExplorer: EnvironmentExplorer;
let languageClient: GestVenvLanguageClient;
let webSocketClient: WebSocketClient;
let diagnosticCollection: vscode.DiagnosticCollection;

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
        
        // Register refactoring commands
        registerRefactoringCommands(context, api);

        // Initialize WebSocket client for real-time updates
        if (config.get<boolean>('enableWebSocket', true)) {
            const wsUrl = apiEndpoint.replace('http', 'ws');
            const clientId = `vscode_${vscode.env.machineId}_${Date.now()}`;
            webSocketClient = new WebSocketClient(wsUrl, clientId);
            
            // Set up WebSocket event handlers
            webSocketClient.on('environment-change', (message) => {
                environmentExplorer.refresh();
                statusBar.update();
            });
            
            webSocketClient.on('package-change', (message) => {
                environmentExplorer.refresh();
                if (diagnosticCollection) {
                    // Re-run diagnostics when packages change
                    vscode.window.visibleTextEditors.forEach(editor => {
                        if (editor.document.languageId === 'python') {
                            vscode.commands.executeCommand('gestvenv.refreshDiagnostics', editor.document);
                        }
                    });
                }
            });
            
            webSocketClient.on('error', (error) => {
                console.error('WebSocket error:', error);
            });
            
            // Connect WebSocket
            webSocketClient.connect().catch(error => {
                console.error('Failed to connect WebSocket:', error);
            });
        }

        // Initialize Python providers if enabled
        if (config.get<boolean>('enableIntelliSense', true)) {
            // Create diagnostic collection
            diagnosticCollection = vscode.languages.createDiagnosticCollection('gestvenv');
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
            
            // Register code action provider
            const codeActionProvider = new CodeActionProvider(api, diagnosticCollection);
            context.subscriptions.push(
                vscode.languages.registerCodeActionsProvider(
                    { scheme: 'file', language: 'python' },
                    codeActionProvider,
                    {
                        providedCodeActionKinds: [
                            vscode.CodeActionKind.QuickFix,
                            vscode.CodeActionKind.RefactorExtract,
                            vscode.CodeActionKind.RefactorInline,
                            vscode.CodeActionKind.RefactorRewrite,
                            vscode.CodeActionKind.SourceOrganizeImports
                        ]
                    }
                )
            );

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
    
    if (webSocketClient) {
        webSocketClient.disconnect();
    }
    
    if (languageClient) {
        languageClient.stop();
    }
    
    if (api) {
        api.dispose();
    }
    
    if (diagnosticCollection) {
        diagnosticCollection.dispose();
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
            
            // Subscribe to WebSocket updates for this environment
            if (webSocketClient) {
                webSocketClient.subscribe(environment.id);
            }
            
            vscode.window.showInformationMessage(
                `Activated GestVenv environment: ${environment.name}`
            );
        }
    } catch (error) {
        console.error('Failed to detect environment:', error);
    }
}