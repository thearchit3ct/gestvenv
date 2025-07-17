import * as vscode from 'vscode';
import * as path from 'path';
import { LanguageClient, LanguageClientOptions, ServerOptions, TransportKind } from 'vscode-languageclient/node';
import { GestVenvAPI } from '../api/gestvenvClient';

export class GestVenvLanguageClient {
    private client: LanguageClient | undefined;

    constructor(
        private context: vscode.ExtensionContext,
        private api: GestVenvAPI
    ) {}

    async start() {
        const serverModule = this.context.asAbsolutePath(
            path.join('out', 'language', 'server.js')
        );

        const debugOptions = { execArgv: ['--nolazy', '--inspect=6009'] };

        const serverOptions: ServerOptions = {
            run: { module: serverModule, transport: TransportKind.ipc },
            debug: {
                module: serverModule,
                transport: TransportKind.ipc,
                options: debugOptions
            }
        };

        const clientOptions: LanguageClientOptions = {
            documentSelector: [{ scheme: 'file', language: 'python' }],
            synchronize: {
                configurationSection: 'gestvenv',
                fileEvents: vscode.workspace.createFileSystemWatcher('**/*.py')
            },
            initializationOptions: {
                apiEndpoint: vscode.workspace.getConfiguration('gestvenv').get('apiEndpoint')
            }
        };

        this.client = new LanguageClient(
            'gestvenv',
            'GestVenv Language Server',
            serverOptions,
            clientOptions
        );

        await this.client.start();
    }

    async stop() {
        if (this.client) {
            await this.client.stop();
        }
    }
}