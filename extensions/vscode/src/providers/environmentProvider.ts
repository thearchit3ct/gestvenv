import * as vscode from 'vscode';
import { GestVenvAPI, Environment, Package } from '../api/gestvenvClient';

export class EnvironmentProvider {
    private _onDidChangeEnvironments = new vscode.EventEmitter<void>();
    readonly onDidChangeEnvironments = this._onDidChangeEnvironments.event;

    constructor(private api: GestVenvAPI) {}

    async getEnvironments(): Promise<Environment[]> {
        try {
            return await this.api.listEnvironments();
        } catch (error) {
            console.error('Failed to get environments:', error);
            return [];
        }
    }

    async getPackages(envId: string): Promise<Package[]> {
        try {
            return await this.api.getPackages(envId);
        } catch (error) {
            console.error('Failed to get packages:', error);
            return [];
        }
    }

    refresh(): void {
        this._onDidChangeEnvironments.fire();
    }
}