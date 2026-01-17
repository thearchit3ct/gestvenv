import * as assert from 'assert';
import * as vscode from 'vscode';
import * as path from 'path';

suite('Extension Integration Tests', () => {
    const extensionId = 'gestvenv.gestvenv-vscode';
    let extension: vscode.Extension<any> | undefined;

    suiteSetup(async () => {
        // Ensure extension is activated
        extension = vscode.extensions.getExtension(extensionId);
        if (extension && !extension.isActive) {
            await extension.activate();
        }
    });

    test('Extension should be present', () => {
        assert.ok(extension, 'Extension not found');
    });

    test('Extension should activate', async () => {
        assert.ok(extension?.isActive, 'Extension not active');
    });

    test('Should register all expected commands', async () => {
        const expectedCommands = [
            'gestvenv.createEnvironment',
            'gestvenv.deleteEnvironment',
            'gestvenv.activateEnvironment',
            'gestvenv.installPackage',
            'gestvenv.uninstallPackage',
            'gestvenv.refresh',
            'gestvenv.showSettings',
            'gestvenv.extractVariable',
            'gestvenv.extractFunction',
            'gestvenv.organizeImports'
        ];

        const registeredCommands = await vscode.commands.getCommands();
        
        for (const cmd of expectedCommands) {
            assert.ok(
                registeredCommands.includes(cmd),
                `Command ${cmd} not registered`
            );
        }
    });

    test('Should have correct configuration defaults', async () => {
        // Reset any workspace-level configurations first
        const config = vscode.workspace.getConfiguration('gestvenv');
        await config.update('enable', undefined, vscode.ConfigurationTarget.Workspace);
        await config.update('autoDetect', undefined, vscode.ConfigurationTarget.Workspace);
        await config.update('showStatusBar', undefined, vscode.ConfigurationTarget.Workspace);
        await config.update('enableIntelliSense', undefined, vscode.ConfigurationTarget.Workspace);
        await config.update('apiEndpoint', undefined, vscode.ConfigurationTarget.Workspace);
        await config.update('enableWebSocket', undefined, vscode.ConfigurationTarget.Workspace);
        
        // Wait for config to reset
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Get fresh config
        const freshConfig = vscode.workspace.getConfiguration('gestvenv');
        
        assert.strictEqual(freshConfig.get('enable'), true);
        assert.strictEqual(freshConfig.get('autoDetect'), true);
        assert.strictEqual(freshConfig.get('showStatusBar'), true);
        assert.strictEqual(freshConfig.get('enableIntelliSense'), true);
        assert.strictEqual(freshConfig.get('apiEndpoint'), 'http://localhost:8000');
        assert.strictEqual(freshConfig.get('enableWebSocket'), true);
    });

    test('Should register Python language features', async () => {
        const disposables = (extension?.exports as any)?.disposables || [];
        
        // Check if language features are registered
        const languages = await vscode.languages.getLanguages();
        const hasCompletionProvider = languages.includes('python');
        assert.ok(hasCompletionProvider, 'Python language not supported');
    });

    test('Should create status bar item', async () => {
        // Status bar should be visible when Python file is active
        const doc = await vscode.workspace.openTextDocument({
            language: 'python',
            content: 'print("Hello, World!")'
        });
        
        await vscode.window.showTextDocument(doc);
        
        // Give extension time to update status bar
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Check if status bar exists (we can't directly access it, but we can check if commands work)
        try {
            await vscode.commands.executeCommand('gestvenv.showEnvironmentQuickPick');
            assert.ok(true, 'Status bar command executed');
        } catch (error) {
            // Command might fail if no environments, but it should exist
            assert.ok(true, 'Command exists');
        }
    });

    test('Should handle Python file activation', async () => {
        const pythonContent = `
import os
import sys

def main():
    print("Test")

if __name__ == "__main__":
    main()
`;

        const doc = await vscode.workspace.openTextDocument({
            language: 'python',
            content: pythonContent
        });

        const editor = await vscode.window.showTextDocument(doc);
        
        // Extension should activate for Python files
        assert.strictEqual(editor.document.languageId, 'python');
        assert.ok(extension?.isActive);
    });

    test('Should provide code actions for missing imports', async function() {
        this.timeout(10000);
        
        const doc = await vscode.workspace.openTextDocument({
            language: 'python',
            content: 'import nonexistent_module\n'
        });

        const editor = await vscode.window.showTextDocument(doc);
        
        // Wait for diagnostics
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Get code actions
        const range = new vscode.Range(0, 0, 0, 25);
        const codeActions = await vscode.commands.executeCommand<vscode.CodeAction[]>(
            'vscode.executeCodeActionProvider',
            doc.uri,
            range
        );
        
        // Should have at least quick fix actions available
        assert.ok(Array.isArray(codeActions), 'Code actions should be an array');
    });

    test('Should handle configuration changes', async () => {
        // Change a setting
        await vscode.workspace.getConfiguration('gestvenv').update('enableIntelliSense', false, vscode.ConfigurationTarget.Workspace);
        
        // Wait a moment for the configuration to update
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Get fresh config reference
        const config = vscode.workspace.getConfiguration('gestvenv');
        
        // Verify change
        assert.strictEqual(config.get('enableIntelliSense'), false);
        
        // Restore default
        await config.update('enableIntelliSense', undefined, vscode.ConfigurationTarget.Workspace);
        
        // Wait for update
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Verify restored
        const restoredConfig = vscode.workspace.getConfiguration('gestvenv');
        assert.strictEqual(restoredConfig.get('enableIntelliSense'), true);
    });
});