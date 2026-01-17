import * as assert from 'assert';
import * as vscode from 'vscode';

suite('Extension Test Suite', () => {
    test('Extension should be present', () => {
        const extension = vscode.extensions.getExtension('gestvenv.gestvenv-vscode');
        assert.ok(extension, 'Extension should be installed');
    });

    test('Extension should have correct properties', () => {
        const extension = vscode.extensions.getExtension('gestvenv.gestvenv-vscode');
        assert.ok(extension);
        assert.strictEqual(extension.id, 'gestvenv.gestvenv-vscode');
        assert.ok(extension.extensionPath);
    });

    test('Should load package.json', () => {
        const extension = vscode.extensions.getExtension('gestvenv.gestvenv-vscode');
        const packageJSON = extension?.packageJSON;
        
        assert.ok(packageJSON);
        assert.strictEqual(packageJSON.name, 'gestvenv-vscode');
        assert.strictEqual(packageJSON.displayName, 'GestVenv');
        assert.ok(packageJSON.version);
        assert.ok(packageJSON.engines.vscode);
    });

    test('Configuration schema should be defined', () => {
        const extension = vscode.extensions.getExtension('gestvenv.gestvenv-vscode');
        const configProps = extension?.packageJSON?.contributes?.configuration?.properties;
        
        assert.ok(configProps);
        assert.ok(configProps['gestvenv.enable']);
        assert.ok(configProps['gestvenv.apiEndpoint']);
        assert.ok(configProps['gestvenv.enableIntelliSense']);
    });

    test('Commands should be defined in package.json', () => {
        const extension = vscode.extensions.getExtension('gestvenv.gestvenv-vscode');
        const commands = extension?.packageJSON?.contributes?.commands;
        
        assert.ok(commands);
        assert.ok(commands.length > 0);
        
        const commandIds = commands.map((cmd: any) => cmd.command);
        assert.ok(commandIds.includes('gestvenv.createEnvironment'));
        assert.ok(commandIds.includes('gestvenv.installPackage'));
    });

    test('Activation events should be defined', () => {
        const extension = vscode.extensions.getExtension('gestvenv.gestvenv-vscode');
        const activationEvents = extension?.packageJSON?.activationEvents;
        
        assert.ok(activationEvents);
        assert.ok(activationEvents.includes('onLanguage:python'));
        assert.ok(activationEvents.includes('workspaceContains:**/*.py'));
    });
});