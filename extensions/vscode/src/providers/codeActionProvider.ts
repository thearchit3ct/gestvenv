import * as vscode from 'vscode';
import { GestVenvAPI } from '../api/gestvenvClient';

export class CodeActionProvider implements vscode.CodeActionProvider {
    private diagnosticCollection: vscode.DiagnosticCollection;

    constructor(
        private api: GestVenvAPI,
        diagnosticCollection: vscode.DiagnosticCollection
    ) {
        this.diagnosticCollection = diagnosticCollection;
    }

    async provideCodeActions(
        document: vscode.TextDocument,
        range: vscode.Range | vscode.Selection,
        context: vscode.CodeActionContext,
        token: vscode.CancellationToken
    ): Promise<vscode.CodeAction[]> {
        const actions: vscode.CodeAction[] = [];

        // Handle diagnostics in the current range
        for (const diagnostic of context.diagnostics) {
            if (diagnostic.source === 'GestVenv') {
                const action = this.createActionForDiagnostic(document, diagnostic);
                if (action) {
                    actions.push(action);
                }
            }
        }

        // Add refactoring actions
        const refactoringActions = await this.getRefactoringActions(document, range);
        actions.push(...refactoringActions);

        // Add import organization actions
        if (this.isImportLine(document, range)) {
            const organizeAction = this.createOrganizeImportsAction(document);
            if (organizeAction) {
                actions.push(organizeAction);
            }
        }

        return actions;
    }

    private createActionForDiagnostic(
        document: vscode.TextDocument,
        diagnostic: vscode.Diagnostic
    ): vscode.CodeAction | undefined {
        // Handle missing import diagnostics
        if (diagnostic.code === 'missing-import') {
            const data = (diagnostic as any).data;
            if (data?.packageName) {
                const action = new vscode.CodeAction(
                    `Install '${data.packageName}'`,
                    vscode.CodeActionKind.QuickFix
                );
                
                action.diagnostics = [diagnostic];
                action.command = {
                    command: 'gestvenv.installPackage',
                    title: 'Install Package',
                    arguments: [null, data.packageName]
                };
                
                return action;
            }
        }

        // Handle outdated package diagnostics
        if (diagnostic.code === 'outdated-package') {
            const data = (diagnostic as any).data;
            if (data?.packageName && data?.latestVersion) {
                const action = new vscode.CodeAction(
                    `Update '${data.packageName}' to ${data.latestVersion}`,
                    vscode.CodeActionKind.QuickFix
                );
                
                action.diagnostics = [diagnostic];
                action.command = {
                    command: 'gestvenv.updatePackage',
                    title: 'Update Package',
                    arguments: [null, data.packageName, data.latestVersion]
                };
                
                return action;
            }
        }

        return undefined;
    }

    private async getRefactoringActions(
        document: vscode.TextDocument,
        range: vscode.Range
    ): Promise<vscode.CodeAction[]> {
        const actions: vscode.CodeAction[] = [];

        // Extract variable
        if (!range.isEmpty) {
            const extractVariableAction = new vscode.CodeAction(
                'Extract Variable',
                vscode.CodeActionKind.RefactorExtract
            );
            
            extractVariableAction.command = {
                command: 'gestvenv.extractVariable',
                title: 'Extract Variable',
                arguments: [document, range]
            };
            
            actions.push(extractVariableAction);
        }

        // Extract function
        if (this.canExtractFunction(document, range)) {
            const extractFunctionAction = new vscode.CodeAction(
                'Extract Function',
                vscode.CodeActionKind.RefactorExtract
            );
            
            extractFunctionAction.command = {
                command: 'gestvenv.extractFunction',
                title: 'Extract Function',
                arguments: [document, range]
            };
            
            actions.push(extractFunctionAction);
        }

        // Rename symbol
        const wordRange = document.getWordRangeAtPosition(range.start);
        if (wordRange) {
            const renameAction = new vscode.CodeAction(
                'Rename Symbol',
                vscode.CodeActionKind.Refactor
            );
            
            renameAction.command = {
                command: 'editor.action.rename',
                title: 'Rename Symbol'
            };
            
            actions.push(renameAction);
        }

        // Add import for undefined name
        const word = document.getText(wordRange);
        if (word && await this.isUndefinedName(document, word)) {
            const suggestions = await this.api.getSuggestedImports(word);
            
            for (const suggestion of suggestions.slice(0, 3)) {
                const action = new vscode.CodeAction(
                    `Import ${suggestion.module} from ${suggestion.package}`,
                    vscode.CodeActionKind.QuickFix
                );
                
                action.edit = new vscode.WorkspaceEdit();
                const importLine = this.generateImportStatement(suggestion);
                const position = this.findImportInsertPosition(document);
                
                action.edit.insert(document.uri, position, importLine + '\n');
                actions.push(action);
            }
        }

        return actions;
    }

    private createOrganizeImportsAction(document: vscode.TextDocument): vscode.CodeAction | undefined {
        const action = new vscode.CodeAction(
            'Organize Imports',
            vscode.CodeActionKind.SourceOrganizeImports
        );
        
        action.command = {
            command: 'gestvenv.organizeImports',
            title: 'Organize Imports',
            arguments: [document]
        };
        
        return action;
    }

    private isImportLine(document: vscode.TextDocument, range: vscode.Range): boolean {
        const line = document.lineAt(range.start.line).text;
        return /^\s*(import|from)\s+/.test(line);
    }

    private canExtractFunction(document: vscode.TextDocument, range: vscode.Range): boolean {
        // Check if selection contains complete statements
        if (range.isEmpty) {
            return false;
        }
        
        const text = document.getText(range);
        // Simple heuristic: contains at least one complete line
        return text.includes('\n') || /[;:]/.test(text);
    }

    private async isUndefinedName(document: vscode.TextDocument, name: string): Promise<boolean> {
        // Simple check - could be enhanced with proper Python parsing
        const text = document.getText();
        const importRegex = new RegExp(`\\b(import\\s+${name}|from\\s+\\S+\\s+import\\s+.*\\b${name}\\b)`, 'gm');
        const definitionRegex = new RegExp(`\\b(def|class)\\s+${name}\\b`, 'gm');
        
        return !importRegex.test(text) && !definitionRegex.test(text);
    }

    private generateImportStatement(suggestion: any): string {
        if (suggestion.import_type === 'direct') {
            return `import ${suggestion.module}`;
        } else {
            return `from ${suggestion.package} import ${suggestion.module}`;
        }
    }

    findImportInsertPosition(document: vscode.TextDocument): vscode.Position {
        // Find the last import statement
        let lastImportLine = -1;
        
        for (let i = 0; i < document.lineCount; i++) {
            const line = document.lineAt(i).text;
            if (/^\s*(import|from)\s+/.test(line)) {
                lastImportLine = i;
            } else if (lastImportLine >= 0 && line.trim() !== '') {
                // Found first non-import, non-empty line after imports
                break;
            }
        }
        
        if (lastImportLine >= 0) {
            return new vscode.Position(lastImportLine + 1, 0);
        }
        
        // No imports found, insert at beginning after any comments/docstrings
        for (let i = 0; i < document.lineCount; i++) {
            const line = document.lineAt(i).text.trim();
            if (line && !line.startsWith('#') && !line.startsWith('"""') && !line.startsWith("'''")) {
                return new vscode.Position(i, 0);
            }
        }
        
        return new vscode.Position(0, 0);
    }
}

export class RefactoringProvider {
    constructor(private api: GestVenvAPI) {}

    async extractVariable(
        document: vscode.TextDocument,
        range: vscode.Range
    ): Promise<void> {
        const selectedText = document.getText(range);
        
        const variableName = await vscode.window.showInputBox({
            prompt: 'Enter variable name',
            value: 'extracted_var'
        });
        
        if (!variableName) {
            return;
        }
        
        const edit = new vscode.WorkspaceEdit();
        
        // Find appropriate position for variable declaration
        const line = range.start.line;
        const indent = this.getIndentation(document, line);
        
        // Insert variable declaration
        const declarationPosition = new vscode.Position(line, 0);
        edit.insert(document.uri, declarationPosition, `${indent}${variableName} = ${selectedText}\n`);
        
        // Replace selected text with variable name
        edit.replace(document.uri, range, variableName);
        
        await vscode.workspace.applyEdit(edit);
    }

    async extractFunction(
        document: vscode.TextDocument,
        range: vscode.Range
    ): Promise<void> {
        const selectedText = document.getText(range);
        
        const functionName = await vscode.window.showInputBox({
            prompt: 'Enter function name',
            value: 'extracted_function'
        });
        
        if (!functionName) {
            return;
        }
        
        // Analyze the selected code to determine parameters
        const analysis = await this.api.analyzeCodeForRefactoring({
            code: selectedText,
            refactoring_type: 'extract_function',
            context: document.getText()
        });
        
        const edit = new vscode.WorkspaceEdit();
        
        // Create function definition
        const parameters = analysis.suggested_parameters || [];
        const paramList = parameters.join(', ');
        const functionDef = `def ${functionName}(${paramList}):\n${this.indentText(selectedText, '    ')}\n`;
        
        // Find position to insert function (before current function/class or at module level)
        const insertPosition = this.findFunctionInsertPosition(document, range.start);
        edit.insert(document.uri, insertPosition, functionDef + '\n');
        
        // Replace selected text with function call
        const callParams = analysis.call_parameters || parameters;
        const functionCall = `${functionName}(${callParams.join(', ')})`;
        edit.replace(document.uri, range, functionCall);
        
        await vscode.workspace.applyEdit(edit);
    }

    async organizeImports(document: vscode.TextDocument): Promise<void> {
        const imports = this.extractImports(document);
        if (imports.length === 0) {
            return;
        }
        
        // Sort imports
        const sortedImports = this.sortImports(imports);
        
        // Group imports
        const groupedImports = this.groupImports(sortedImports);
        
        // Create edit
        const edit = new vscode.WorkspaceEdit();
        
        // Remove existing imports
        for (const imp of imports) {
            const line = document.lineAt(imp.line);
            const range = new vscode.Range(
                imp.line, 0,
                imp.line + 1, 0
            );
            edit.delete(document.uri, range);
        }
        
        // Insert organized imports
        const insertPosition = new vscode.Position(imports[0].line, 0);
        const organizedText = this.formatImportGroups(groupedImports);
        edit.insert(document.uri, insertPosition, organizedText);
        
        await vscode.workspace.applyEdit(edit);
    }

    private getIndentation(document: vscode.TextDocument, line: number): string {
        const lineText = document.lineAt(line).text;
        const match = lineText.match(/^(\s*)/);
        return match ? match[1] : '';
    }

    private indentText(text: string, indent: string): string {
        return text.split('\n').map(line => indent + line).join('\n');
    }

    private findImportInsertPositionPrivate(document: vscode.TextDocument): vscode.Position {
        // Find the last import statement
        let lastImportLine = -1;
        
        for (let i = 0; i < document.lineCount; i++) {
            const line = document.lineAt(i).text;
            if (/^\s*(import|from)\s+/.test(line)) {
                lastImportLine = i;
            } else if (lastImportLine >= 0 && line.trim() !== '') {
                // Found first non-import, non-empty line after imports
                break;
            }
        }
        
        if (lastImportLine >= 0) {
            return new vscode.Position(lastImportLine + 1, 0);
        }
        
        // No imports found, insert at beginning after any comments/docstrings
        for (let i = 0; i < document.lineCount; i++) {
            const line = document.lineAt(i).text.trim();
            if (line && !line.startsWith('#') && !line.startsWith('"""') && !line.startsWith("'''")) {
                return new vscode.Position(i, 0);
            }
        }
        
        return new vscode.Position(0, 0);
    }

    private findFunctionInsertPosition(document: vscode.TextDocument, currentPosition: vscode.Position): vscode.Position {
        // Simple implementation - find the start of current function/class
        for (let i = currentPosition.line - 1; i >= 0; i--) {
            const line = document.lineAt(i).text;
            if (/^(def|class)\s+/.test(line)) {
                return new vscode.Position(i, 0);
            }
        }
        
        // If no function/class found, insert at top after imports
        return this.findImportInsertPositionPrivate(document);
    }

    private extractImports(document: vscode.TextDocument): any[] {
        const imports = [];
        
        for (let i = 0; i < document.lineCount; i++) {
            const line = document.lineAt(i).text;
            const importMatch = line.match(/^\s*import\s+(.+)/);
            const fromMatch = line.match(/^\s*from\s+(\S+)\s+import\s+(.+)/);
            
            if (importMatch) {
                imports.push({
                    line: i,
                    type: 'import',
                    module: importMatch[1].trim(),
                    text: line
                });
            } else if (fromMatch) {
                imports.push({
                    line: i,
                    type: 'from',
                    module: fromMatch[1].trim(),
                    names: fromMatch[2].trim(),
                    text: line
                });
            }
        }
        
        return imports;
    }

    private sortImports(imports: any[]): any[] {
        return imports.sort((a, b) => {
            // First sort by type (import before from)
            if (a.type !== b.type) {
                return a.type === 'import' ? -1 : 1;
            }
            // Then by module name
            return a.module.localeCompare(b.module);
        });
    }

    private groupImports(imports: any[]): Map<string, any[]> {
        const groups = new Map<string, any[]>();
        groups.set('stdlib', []);
        groups.set('third_party', []);
        groups.set('local', []);
        
        const stdlibModules = new Set([
            'os', 'sys', 'json', 'datetime', 'time', 'math', 'random',
            're', 'collections', 'itertools', 'functools', 'pathlib'
        ]);
        
        for (const imp of imports) {
            const mainModule = imp.module.split('.')[0];
            
            if (stdlibModules.has(mainModule)) {
                groups.get('stdlib')!.push(imp);
            } else if (imp.module.startsWith('.')) {
                groups.get('local')!.push(imp);
            } else {
                groups.get('third_party')!.push(imp);
            }
        }
        
        return groups;
    }

    private formatImportGroups(groups: Map<string, any[]>): string {
        const sections = [];
        
        const stdlib = groups.get('stdlib')!;
        if (stdlib.length > 0) {
            sections.push(stdlib.map(imp => imp.text.trimRight()).join('\n'));
        }
        
        const thirdParty = groups.get('third_party')!;
        if (thirdParty.length > 0) {
            sections.push(thirdParty.map(imp => imp.text.trimRight()).join('\n'));
        }
        
        const local = groups.get('local')!;
        if (local.length > 0) {
            sections.push(local.map(imp => imp.text.trimRight()).join('\n'));
        }
        
        return sections.join('\n\n') + '\n\n';
    }
}