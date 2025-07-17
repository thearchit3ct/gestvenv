import * as assert from 'assert';
import * as vscode from 'vscode';
import * as path from 'path';

suite('Extension Test Suite', () => {
    vscode.window.showInformationMessage('Start all tests.');

    test('Extension should be present', () => {
        assert.ok(vscode.extensions.getExtension('gestvenv.gestvenv-vscode'));
    });

    test('Should register all commands', async () => {
        const extension = vscode.extensions.getExtension('gestvenv.gestvenv-vscode');
        if (!extension) {
            assert.fail('Extension not found');
        }

        await extension.activate();

        const commands = [
            'gestvenv.createEnvironment',
            'gestvenv.deleteEnvironment',
            'gestvenv.activateEnvironment',
            'gestvenv.installPackage',
            'gestvenv.uninstallPackage',
            'gestvenv.refresh',
            'gestvenv.showSettings'
        ];

        const registeredCommands = await vscode.commands.getCommands();
        
        for (const command of commands) {
            assert.ok(
                registeredCommands.includes(command),
                `Command ${command} not registered`
            );
        }
    });

    test('Should activate on Python files', async () => {
        const document = await vscode.workspace.openTextDocument({
            language: 'python',
            content: 'import sys\nprint("Hello")'
        });

        await vscode.window.showTextDocument(document);

        const extension = vscode.extensions.getExtension('gestvenv.gestvenv-vscode');
        assert.ok(extension?.isActive, 'Extension should be active for Python files');
    });

    test('Configuration should have default values', () => {
        const config = vscode.workspace.getConfiguration('gestvenv');
        
        assert.strictEqual(config.get('enable'), true);
        assert.strictEqual(config.get('autoDetect'), true);
        assert.strictEqual(config.get('showStatusBar'), true);
        assert.strictEqual(config.get('enableIntelliSense'), true);
        assert.strictEqual(config.get('apiEndpoint'), 'http://localhost:8000');
    });
});