import * as vscode from 'vscode';
import { GestVenvAPI, ImportAnalysis } from '../api/gestvenvClient';

export class DiagnosticProvider implements vscode.Disposable {
    private diagnosticCollection: vscode.DiagnosticCollection;
    private disposables: vscode.Disposable[] = [];

    constructor(private api: GestVenvAPI) {
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('gestvenv');
        
        // Register diagnostics on file changes
        this.disposables.push(
            vscode.workspace.onDidChangeTextDocument(e => {
                if (e.document.languageId === 'python') {
                    this.updateDiagnostics(e.document);
                }
            })
        );

        // Register diagnostics on file open
        this.disposables.push(
            vscode.workspace.onDidOpenTextDocument(doc => {
                if (doc.languageId === 'python') {
                    this.updateDiagnostics(doc);
                }
            })
        );

        // Check all open documents
        vscode.workspace.textDocuments.forEach(doc => {
            if (doc.languageId === 'python') {
                this.updateDiagnostics(doc);
            }
        });
    }

    private async updateDiagnostics(document: vscode.TextDocument) {
        const config = vscode.workspace.getConfiguration('gestvenv.diagnostics');
        if (!config.get<boolean>('enable', true)) {
            return;
        }

        try {
            const analysis = await this.api.analyzeImports(
                document.getText(),
                document.fileName
            );

            const diagnostics: vscode.Diagnostic[] = [];

            // Check for missing imports
            if (config.get<boolean>('showMissingImports', true)) {
                for (const missing of analysis.missing) {
                    const diagnostic = this.createMissingImportDiagnostic(document, missing, analysis);
                    if (diagnostic) {
                        diagnostics.push(diagnostic);
                    }
                }
            }

            this.diagnosticCollection.set(document.uri, diagnostics);

        } catch (error) {
            console.error('Failed to analyze imports:', error);
        }
    }

    private createMissingImportDiagnostic(
        document: vscode.TextDocument,
        missingModule: string,
        analysis: ImportAnalysis
    ): vscode.Diagnostic | null {
        // Find the import line
        const importInfo = analysis.imports.find(imp => imp.module === missingModule);
        if (!importInfo) {
            return null;
        }

        const line = document.lineAt(importInfo.line - 1);
        const range = new vscode.Range(
            importInfo.line - 1,
            line.firstNonWhitespaceCharacterIndex,
            importInfo.line - 1,
            line.text.length
        );

        const diagnostic = new vscode.Diagnostic(
            range,
            `Module '${missingModule}' is not installed`,
            vscode.DiagnosticSeverity.Error
        );

        diagnostic.code = 'missing-import';
        diagnostic.source = 'GestVenv';
        // Store custom data for code actions
        (diagnostic as any).data = { packageName: missingModule };

        // Add suggested packages as related information
        const suggestions = analysis.suggestions.filter(
            pkg => pkg.name === missingModule || pkg.modules?.includes(missingModule)
        );

        if (suggestions.length > 0) {
            diagnostic.relatedInformation = suggestions.map(pkg => {
                return new vscode.DiagnosticRelatedInformation(
                    new vscode.Location(document.uri, range),
                    `Install '${pkg.name}' (${pkg.version})`
                );
            });
        }

        return diagnostic;
    }

    dispose() {
        this.diagnosticCollection.dispose();
        this.disposables.forEach(d => d.dispose());
    }
}