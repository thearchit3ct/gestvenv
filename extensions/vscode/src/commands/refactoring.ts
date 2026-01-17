import * as vscode from 'vscode';
import { GestVenvAPI } from '../api/gestvenvClient';
import { RefactoringProvider } from '../providers/codeActionProvider';

export function registerRefactoringCommands(
    context: vscode.ExtensionContext,
    api: GestVenvAPI
): void {
    const refactoringProvider = new RefactoringProvider(api);

    // Extract Variable command
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.extractVariable', async (document: vscode.TextDocument, range: vscode.Range) => {
            try {
                await refactoringProvider.extractVariable(document, range);
                vscode.window.showInformationMessage('Variable extracted successfully');
            } catch (error) {
                vscode.window.showErrorMessage(`Failed to extract variable: ${error}`);
            }
        })
    );

    // Extract Function command
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.extractFunction', async (document: vscode.TextDocument, range: vscode.Range) => {
            try {
                await refactoringProvider.extractFunction(document, range);
                vscode.window.showInformationMessage('Function extracted successfully');
            } catch (error) {
                vscode.window.showErrorMessage(`Failed to extract function: ${error}`);
            }
        })
    );

    // Organize Imports command
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.organizeImports', async (document: vscode.TextDocument) => {
            try {
                await refactoringProvider.organizeImports(document);
                vscode.window.showInformationMessage('Imports organized successfully');
            } catch (error) {
                vscode.window.showErrorMessage(`Failed to organize imports: ${error}`);
            }
        })
    );

    // Add missing import command
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.addMissingImport', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                return;
            }

            const document = editor.document;
            const position = editor.selection.active;
            const wordRange = document.getWordRangeAtPosition(position);
            
            if (!wordRange) {
                vscode.window.showWarningMessage('No symbol selected');
                return;
            }

            const word = document.getText(wordRange);
            
            try {
                // Get import suggestions
                const suggestions = await api.getSuggestedImports(word);
                
                if (suggestions.length === 0) {
                    vscode.window.showInformationMessage(`No import suggestions found for '${word}'`);
                    return;
                }

                // Show quick pick
                const items = suggestions.map((s: any) => ({
                    label: s.module,
                    description: s.package,
                    detail: s.description,
                    suggestion: s
                }));

                const selected = await vscode.window.showQuickPick(items, {
                    placeHolder: `Select import for '${word}'`
                });

                if (!selected) {
                    return;
                }

                // Add import
                const edit = new vscode.WorkspaceEdit();
                const importStatement = (selected as any).suggestion.import_type === 'direct'
                    ? `import ${(selected as any).suggestion.module}`
                    : `from ${(selected as any).suggestion.package} import ${(selected as any).suggestion.module}`;
                
                const insertPosition = findImportInsertPosition(document);
                edit.insert(document.uri, insertPosition, importStatement + '\n');
                
                await vscode.workspace.applyEdit(edit);
                vscode.window.showInformationMessage(`Added import: ${importStatement}`);
                
            } catch (error) {
                vscode.window.showErrorMessage(`Failed to add import: ${error}`);
            }
        })
    );

    // Inline variable command
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.inlineVariable', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                return;
            }

            const document = editor.document;
            const position = editor.selection.active;
            const wordRange = document.getWordRangeAtPosition(position);
            
            if (!wordRange) {
                vscode.window.showWarningMessage('No variable selected');
                return;
            }

            const variableName = document.getText(wordRange);
            
            try {
                // Find variable definition
                const definition = await findVariableDefinition(document, variableName, position);
                
                if (!definition) {
                    vscode.window.showWarningMessage(`Cannot find definition for '${variableName}'`);
                    return;
                }

                // Find all usages
                const usages = await findVariableUsages(document, variableName, definition.line);
                
                if (usages.length === 0) {
                    vscode.window.showWarningMessage(`No usages found for '${variableName}'`);
                    return;
                }

                // Create edit
                const edit = new vscode.WorkspaceEdit();
                
                // Replace all usages with the value
                for (const usage of usages) {
                    edit.replace(document.uri, usage.range, definition.value);
                }
                
                // Remove the variable definition
                const defLine = document.lineAt(definition.line);
                edit.delete(document.uri, defLine.rangeIncludingLineBreak);
                
                await vscode.workspace.applyEdit(edit);
                vscode.window.showInformationMessage(`Inlined variable '${variableName}'`);
                
            } catch (error) {
                vscode.window.showErrorMessage(`Failed to inline variable: ${error}`);
            }
        })
    );

    // Convert to f-string command
    context.subscriptions.push(
        vscode.commands.registerCommand('gestvenv.convertToFString', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                return;
            }

            const document = editor.document;
            const selection = editor.selection;
            
            try {
                const line = document.lineAt(selection.start.line);
                const lineText = line.text;
                
                // Check if it's a string formatting operation
                const formatMatch = lineText.match(/(['"])(.+?)\1\s*%\s*(.+)/);
                const formatMethodMatch = lineText.match(/(['"])(.+?)\1\.format\((.+)\)/);
                
                let newText: string | undefined;
                
                if (formatMatch) {
                    // Convert % formatting to f-string
                    const [, quote, template, args] = formatMatch;
                    newText = convertPercentToFString(template, args, quote);
                } else if (formatMethodMatch) {
                    // Convert .format() to f-string
                    const [, quote, template, args] = formatMethodMatch;
                    newText = convertFormatToFString(template, args, quote);
                } else {
                    vscode.window.showWarningMessage('No string formatting found on current line');
                    return;
                }

                if (newText) {
                    const edit = new vscode.WorkspaceEdit();
                    edit.replace(document.uri, line.range, newText);
                    await vscode.workspace.applyEdit(edit);
                    vscode.window.showInformationMessage('Converted to f-string');
                }
                
            } catch (error) {
                vscode.window.showErrorMessage(`Failed to convert to f-string: ${error}`);
            }
        })
    );
}

function findImportInsertPosition(document: vscode.TextDocument): vscode.Position {
    let lastImportLine = -1;
    
    for (let i = 0; i < document.lineCount; i++) {
        const line = document.lineAt(i).text;
        if (/^\s*(import|from)\s+/.test(line)) {
            lastImportLine = i;
        } else if (lastImportLine >= 0 && line.trim() !== '') {
            break;
        }
    }
    
    if (lastImportLine >= 0) {
        return new vscode.Position(lastImportLine + 1, 0);
    }
    
    return new vscode.Position(0, 0);
}

async function findVariableDefinition(
    document: vscode.TextDocument,
    variableName: string,
    currentPosition: vscode.Position
): Promise<{ line: number; value: string } | undefined> {
    // Simple regex-based search for variable assignment
    const pattern = new RegExp(`^\\s*${variableName}\\s*=\\s*(.+)$`);
    
    // Search backwards from current position
    for (let i = currentPosition.line - 1; i >= 0; i--) {
        const line = document.lineAt(i).text;
        const match = line.match(pattern);
        
        if (match) {
            return {
                line: i,
                value: match[1].trim()
            };
        }
    }
    
    return undefined;
}

async function findVariableUsages(
    document: vscode.TextDocument,
    variableName: string,
    definitionLine: number
): Promise<{ line: number; range: vscode.Range }[]> {
    const usages: { line: number; range: vscode.Range }[] = [];
    const pattern = new RegExp(`\\b${variableName}\\b`, 'g');
    
    // Search from definition line onwards
    for (let i = definitionLine + 1; i < document.lineCount; i++) {
        const line = document.lineAt(i);
        const text = line.text;
        
        let match;
        while ((match = pattern.exec(text)) !== null) {
            const range = new vscode.Range(
                i, match.index,
                i, match.index + variableName.length
            );
            usages.push({ line: i, range });
        }
    }
    
    return usages;
}

function convertPercentToFString(template: string, args: string, quote: string): string {
    // Simple conversion - handles basic cases
    const argList = args.split(',').map(a => a.trim());
    let result = template;
    let argIndex = 0;
    
    // Replace %s, %d, %f with {arg}
    result = result.replace(/%[sdf]/g, () => {
        if (argIndex < argList.length) {
            return `{${argList[argIndex++]}}`;
        }
        return '%s';
    });
    
    return `f${quote}${result}${quote}`;
}

function convertFormatToFString(template: string, args: string, quote: string): string {
    // Parse .format() arguments
    const argList = parseFormatArgs(args);
    let result = template;
    
    // Replace {} with corresponding arguments
    let argIndex = 0;
    result = result.replace(/\{(\w*)\}/g, (match, name) => {
        if (name) {
            // Named placeholder
            const arg = argList.find(a => a.name === name);
            return arg ? `{${arg.value}}` : match;
        } else {
            // Positional placeholder
            if (argIndex < argList.length) {
                return `{${argList[argIndex++].value}}`;
            }
            return match;
        }
    });
    
    return `f${quote}${result}${quote}`;
}

function parseFormatArgs(args: string): { name?: string; value: string }[] {
    const result: { name?: string; value: string }[] = [];
    
    // Simple parser - splits by comma and handles key=value
    const parts = args.split(',');
    
    for (const part of parts) {
        const trimmed = part.trim();
        const equalIndex = trimmed.indexOf('=');
        
        if (equalIndex > 0) {
            // Named argument
            result.push({
                name: trimmed.substring(0, equalIndex).trim(),
                value: trimmed.substring(equalIndex + 1).trim()
            });
        } else {
            // Positional argument
            result.push({ value: trimmed });
        }
    }
    
    return result;
}