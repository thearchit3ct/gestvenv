import * as vscode from 'vscode';
import { GestVenvAPI, Environment, Package } from '../api/gestvenvClient';
import { CompletionCache } from '../cache/completionCache';

export class PythonCompletionProvider implements vscode.CompletionItemProvider, vscode.HoverProvider {
    private cache: CompletionCache;
    private activeEnvironment: Environment | null = null;

    constructor(private api: GestVenvAPI) {
        this.cache = new CompletionCache();
    }

    setActiveEnvironment(env: Environment | null) {
        this.activeEnvironment = env;
        if (!env) {
            this.cache.clear();
        }
    }

    async provideCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken,
        context: vscode.CompletionContext
    ): Promise<vscode.CompletionItem[]> {
        if (!this.activeEnvironment) {
            return [];
        }

        const line = document.lineAt(position);
        const linePrefix = line.text.substring(0, position.character);

        // Import completions
        if (this.isImportContext(linePrefix)) {
            return this.getImportCompletions(linePrefix);
        }

        // Attribute completions
        if (this.isAttributeContext(linePrefix)) {
            return this.getAttributeCompletions(document, position);
        }

        return [];
    }

    async provideHover(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken
    ): Promise<vscode.Hover | null> {
        if (!this.activeEnvironment) {
            return null;
        }

        const wordRange = document.getWordRangeAtPosition(position);
        if (!wordRange) {
            return null;
        }

        const word = document.getText(wordRange);
        
        // Check if it's a known package
        const packages = await this.api.getPackages(this.activeEnvironment.id);
        const pkg = packages.find(p => p.name === word);
        
        if (pkg) {
            const markdown = new vscode.MarkdownString();
            markdown.appendMarkdown(`**${pkg.name}** v${pkg.version}\n\n`);
            
            if (pkg.description) {
                markdown.appendMarkdown(`${pkg.description}\n\n`);
            }
            
            if (pkg.metadata?.home_page) {
                markdown.appendMarkdown(`[Homepage](${pkg.metadata.home_page})\n\n`);
            }
            
            if (pkg.metadata?.download_stats) {
                markdown.appendMarkdown(`📊 ${pkg.metadata.download_stats.last_month.toLocaleString()} downloads/month\n`);
            }
            
            return new vscode.Hover(markdown);
        }

        return null;
    }

    private isImportContext(linePrefix: string): boolean {
        return /^\s*(from\s+\S*\s*)?import\s+\S*$/.test(linePrefix) ||
               /^\s*from\s+\S*$/.test(linePrefix);
    }

    private isAttributeContext(linePrefix: string): boolean {
        return /\.\s*\w*$/.test(linePrefix);
    }

    private async getImportCompletions(linePrefix: string): Promise<vscode.CompletionItem[]> {
        if (!this.activeEnvironment) {
            return [];
        }

        const cacheKey = `import:${this.activeEnvironment.id}`;
        const cached = this.cache.get(cacheKey);
        if (cached && Array.isArray(cached)) {
            return cached;
        }

        const packages = await this.api.getPackagesWithModules(this.activeEnvironment.id);
        const items: vscode.CompletionItem[] = [];

        // Check if we're in a "from X import" context
        const fromMatch = linePrefix.match(/from\s+(\S+)\s+import\s*$/);
        if (fromMatch) {
            const moduleName = fromMatch[1];
            const pkg = packages.find(p => p.name === moduleName || p.modules?.includes(moduleName));
            
            if (pkg && pkg.modules) {
                // Add submodules
                for (const submodule of pkg.modules) {
                    if (submodule.startsWith(moduleName + '.')) {
                        const subName = submodule.substring(moduleName.length + 1);
                        const item = new vscode.CompletionItem(subName, vscode.CompletionItemKind.Module);
                        item.detail = `from ${moduleName}`;
                        items.push(item);
                    }
                }
            }
        } else {
            // Regular import
            for (const pkg of packages) {
                const item = new vscode.CompletionItem(pkg.name, vscode.CompletionItemKind.Module);
                item.detail = `${pkg.name} ${pkg.version}`;
                
                const doc = new vscode.MarkdownString();
                doc.appendMarkdown(`**${pkg.name}** v${pkg.version}`);
                
                if (pkg.description) {
                    doc.appendMarkdown(`\n\n${pkg.description}`);
                }
                
                if (pkg.metadata?.download_stats) {
                    doc.appendMarkdown(`\n\n📊 ${pkg.metadata.download_stats.last_month.toLocaleString()} downloads/month`);
                }
                
                item.documentation = doc;
                items.push(item);

                // Add main modules
                if (pkg.modules) {
                    for (const module of pkg.modules) {
                        if (!module.includes('.')) {
                            const moduleItem = new vscode.CompletionItem(module, vscode.CompletionItemKind.Module);
                            moduleItem.detail = `from ${pkg.name}`;
                            items.push(moduleItem);
                        }
                    }
                }
            }
        }

        this.cache.set(cacheKey, items);
        return items;
    }

    private async getAttributeCompletions(
        document: vscode.TextDocument,
        position: vscode.Position
    ): Promise<vscode.CompletionItem[]> {
        if (!this.activeEnvironment) {
            return [];
        }

        const objectName = this.extractObjectName(document, position);
        if (!objectName) {
            return [];
        }

        try {
            const response = await this.api.getObjectAttributes({
                environment_id: this.activeEnvironment.id,
                object_path: objectName,
                context: this.getContext(document, position)
            });

            return response.attributes.map(attr => {
                const item = new vscode.CompletionItem(
                    attr.name,
                    this.getCompletionKind(attr.type)
                );

                item.detail = attr.signature || attr.type;
                
                if (attr.doc) {
                    item.documentation = new vscode.MarkdownString(attr.doc);
                }

                // Add snippet for functions
                if (attr.type === 'function' && attr.parameters) {
                    item.insertText = new vscode.SnippetString(
                        this.buildFunctionSnippet(attr)
                    );
                }

                return item;
            });
        } catch (error) {
            console.error('Failed to get attributes:', error);
            return [];
        }
    }

    private extractObjectName(document: vscode.TextDocument, position: vscode.Position): string | null {
        const line = document.lineAt(position);
        const text = line.text.substring(0, position.character);
        
        // Find the last dot
        const lastDot = text.lastIndexOf('.');
        if (lastDot === -1) {
            return null;
        }

        // Extract the object name before the dot
        const beforeDot = text.substring(0, lastDot);
        const match = beforeDot.match(/(\w+(?:\.\w+)*)$/);
        
        return match ? match[1] : null;
    }

    private getContext(document: vscode.TextDocument, position: vscode.Position): string {
        const start = Math.max(0, position.line - 5);
        const end = Math.min(document.lineCount - 1, position.line + 5);
        
        const lines = [];
        for (let i = start; i <= end; i++) {
            lines.push(document.lineAt(i).text);
        }
        
        return lines.join('\n');
    }

    private getCompletionKind(type: string): vscode.CompletionItemKind {
        switch (type) {
            case 'function':
            case 'method':
                return vscode.CompletionItemKind.Function;
            case 'class':
                return vscode.CompletionItemKind.Class;
            case 'module':
                return vscode.CompletionItemKind.Module;
            case 'variable':
            case 'attribute':
                return vscode.CompletionItemKind.Variable;
            case 'property':
                return vscode.CompletionItemKind.Property;
            default:
                return vscode.CompletionItemKind.Text;
        }
    }

    private buildFunctionSnippet(attr: any): string {
        if (!attr.parameters || attr.parameters.length === 0) {
            return `${attr.name}()`;
        }

        const params = attr.parameters.map((param: any, index: number) => {
            if (param.default) {
                return `\${${index + 1}:${param.name}=${param.default}}`;
            }
            return `\${${index + 1}:${param.name}}`;
        });

        return `${attr.name}(${params.join(', ')})`;
    }
}