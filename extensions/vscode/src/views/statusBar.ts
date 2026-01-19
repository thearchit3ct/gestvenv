import * as vscode from 'vscode';
import { GestVenvAPI, Environment } from '../api/gestvenvClient';

export class StatusBarManager implements vscode.Disposable {
    private statusBarItem: vscode.StatusBarItem;
    private activeEnvironment: Environment | null = null;

    constructor(private api: GestVenvAPI) {
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Left,
            100
        );
        
        this.statusBarItem.command = 'gestvenv.selectEnvironment';
        this.update();
    }

    getActiveEnvironment(): Environment | null {
        return this.activeEnvironment;
    }

    async setActiveEnvironment(env: Environment | null) {
        this.activeEnvironment = env;
        await this.update();
    }

    async update() {
        const config = vscode.workspace.getConfiguration('gestvenv');
        if (!config.get<boolean>('showStatusBar', true)) {
            this.statusBarItem.hide();
            return;
        }

        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            this.statusBarItem.hide();
            return;
        }

        // Try to detect active environment if not set
        if (!this.activeEnvironment) {
            try {
                this.activeEnvironment = await this.api.detectActiveEnvironment(
                    workspaceFolder.uri.fsPath
                );
            } catch (error) {
                console.error('Failed to detect environment:', error);
            }
        }

        if (this.activeEnvironment) {
            this.statusBarItem.text = `$(vm) ${this.activeEnvironment.name} (${this.activeEnvironment.python_version})`;
            this.statusBarItem.tooltip = new vscode.MarkdownString(
                `**GestVenv Environment**\n\n` +
                `- **Name:** ${this.activeEnvironment.name}\n` +
                `- **Backend:** ${this.activeEnvironment.backend}\n` +
                `- **Python:** ${this.activeEnvironment.python_version}\n` +
                `- **Packages:** ${this.activeEnvironment.package_count}\n` +
                `- **Path:** ${this.activeEnvironment.path}\n\n` +
                `Click to change environment`
            );
            this.statusBarItem.backgroundColor = undefined;
        } else {
            this.statusBarItem.text = '$(vm) No Environment';
            this.statusBarItem.tooltip = 'Click to create or select a GestVenv environment';
            this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
        }

        this.statusBarItem.show();
    }

    dispose() {
        this.statusBarItem.dispose();
    }
}