import * as path from 'path';
import { runTests } from '@vscode/test-electron';

async function main() {
    try {
        // The folder containing the Extension Manifest package.json
        const extensionDevelopmentPath = path.resolve(__dirname, '../../');

        // The path to test runner
        const extensionTestsPath = path.resolve(__dirname, './suite/index');

        // Minimal workspace for tests
        const testWorkspace = path.resolve(__dirname, '../../test-workspace');

        // Download VS Code, unzip it and run the integration test
        await runTests({ 
            extensionDevelopmentPath, 
            extensionTestsPath,
            launchArgs: [testWorkspace, '--disable-extensions']
        });
    } catch (err) {
        console.error('Failed to run tests:', err);
        process.exit(1);
    }
}

main();