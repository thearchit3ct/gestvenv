import {
    createConnection,
    TextDocuments,
    ProposedFeatures,
    InitializeParams,
    CompletionItem,
    TextDocumentPositionParams,
    CompletionItemKind,
    InitializeResult,
    TextDocumentSyncKind,
    HoverParams,
    Hover,
    MarkupKind,
    DiagnosticSeverity,
    Diagnostic,
    CodeAction,
    CodeActionKind,
    Command
} from 'vscode-languageserver/node';

import { TextDocument } from 'vscode-languageserver-textdocument';
import axios, { AxiosInstance } from 'axios';

interface Environment {
    id: string;
    name: string;
    python_version: string;
    backend: string;
}

interface Package {
    name: string;
    version: string;
    description?: string;
    modules?: string[];
}

class GestVenvLanguageServer {
    private connection = createConnection(ProposedFeatures.all);
    private documents = new TextDocuments(TextDocument);
    private apiClient!: AxiosInstance;
    private environmentCache: Map<string, Environment> = new Map();
    private packageCache: Map<string, Package[]> = new Map();
    private activeEnvironment: Environment | null = null;

    constructor() {
        this.setupHandlers();
        this.documents.listen(this.connection);
        this.connection.listen();
    }

    private setupHandlers() {
        this.connection.onInitialize(this.onInitialize.bind(this));
        this.connection.onInitialized(this.onInitialized.bind(this));
        this.connection.onCompletion(this.onCompletion.bind(this));
        this.connection.onCompletionResolve(this.onCompletionResolve.bind(this));
        this.connection.onHover(this.onHover.bind(this));
        this.connection.onCodeAction(this.onCodeAction.bind(this));
        
        // Document changes
        this.documents.onDidChangeContent(change => {
            this.validateDocument(change.document);
        });
    }

    private async onInitialize(params: InitializeParams): Promise<InitializeResult> {
        // Initialize API client
        const apiEndpoint = params.initializationOptions?.apiEndpoint || 'http://localhost:8000';
        this.apiClient = axios.create({
            baseURL: apiEndpoint,
            timeout: 5000
        });

        const result: InitializeResult = {
            capabilities: {
                textDocumentSync: TextDocumentSyncKind.Incremental,
                completionProvider: {
                    resolveProvider: true,
                    triggerCharacters: ['.', ' ', '"', "'"]
                },
                hoverProvider: true,
                codeActionProvider: true
            }
        };

        return result;
    }

    private async onInitialized() {
        this.connection.console.log('GestVenv Language Server initialized');
        
        // Try to detect active environment
        try {
            const response = await this.apiClient.post('/api/v1/environments/detect', {
                workspace_path: process.cwd()
            });
            
            if (response.data) {
                this.activeEnvironment = response.data;
                this.connection.console.log(`Active environment: ${this.activeEnvironment?.name}`);
            }
        } catch (error) {
            this.connection.console.error('Failed to detect environment');
        }
    }

    private async onCompletion(params: TextDocumentPositionParams): Promise<CompletionItem[]> {
        const document = this.documents.get(params.textDocument.uri);
        if (!document || !this.activeEnvironment) {
            return [];
        }

        const line = document.getText({
            start: { line: params.position.line, character: 0 },
            end: params.position
        });

        // Import completions
        if (this.isImportContext(line)) {
            return this.getImportCompletions();
        }

        return [];
    }

    private async onCompletionResolve(item: CompletionItem): Promise<CompletionItem> {
        // Add additional details to completion items
        if (item.data?.packageName) {
            try {
                const response = await this.apiClient.get(
                    `/api/v1/ide/environments/${this.activeEnvironment?.id}/packages/${item.data.packageName}`
                );
                
                const pkg = response.data;
                item.detail = `${pkg.name} ${pkg.version}`;
                item.documentation = {
                    kind: MarkupKind.Markdown,
                    value: pkg.description || ''
                };
            } catch (error) {
                // Ignore errors
            }
        }
        
        return item;
    }

    private async onHover(params: HoverParams): Promise<Hover | null> {
        const document = this.documents.get(params.textDocument.uri);
        if (!document || !this.activeEnvironment) {
            return null;
        }

        const word = this.getWordAtPosition(document, params.position);
        if (!word) {
            return null;
        }

        // Check if it's a known package
        const packages = await this.getPackages();
        const pkg = packages.find(p => p.name === word);
        
        if (pkg) {
            return {
                contents: {
                    kind: MarkupKind.Markdown,
                    value: [
                        `**${pkg.name}** v${pkg.version}`,
                        '',
                        pkg.description || 'No description available'
                    ].join('\n')
                }
            };
        }

        return null;
    }

    private async onCodeAction(params: any): Promise<(Command | CodeAction)[]> {
        const document = this.documents.get(params.textDocument.uri);
        if (!document) {
            return [];
        }

        const actions: CodeAction[] = [];
        
        for (const diagnostic of params.context.diagnostics) {
            if (diagnostic.code === 'missing-import' && diagnostic.data?.packageName) {
                const action: CodeAction = {
                    title: `Install ${diagnostic.data.packageName}`,
                    kind: CodeActionKind.QuickFix,
                    diagnostics: [diagnostic],
                    command: {
                        title: 'Install Package',
                        command: 'gestvenv.installPackage',
                        arguments: [this.activeEnvironment, diagnostic.data.packageName]
                    }
                };
                actions.push(action);
            }
        }

        return actions;
    }

    private async validateDocument(document: TextDocument) {
        if (!this.activeEnvironment) {
            return;
        }

        const text = document.getText();
        const diagnostics: Diagnostic[] = [];

        // Simple import validation
        const importRegex = /^(?:from\s+(\S+)|import\s+(\S+))/gm;
        let match;
        
        const packages = await this.getPackages();
        const availableModules = new Set<string>();
        
        packages.forEach(pkg => {
            availableModules.add(pkg.name);
            pkg.modules?.forEach(m => availableModules.add(m));
        });

        while ((match = importRegex.exec(text)) !== null) {
            const moduleName = match[1] || match[2];
            if (!availableModules.has(moduleName) && !this.isBuiltinModule(moduleName)) {
                const line = document.positionAt(match.index).line;
                
                diagnostics.push({
                    severity: DiagnosticSeverity.Error,
                    range: {
                        start: { line, character: 0 },
                        end: { line, character: match[0].length }
                    },
                    message: `Module '${moduleName}' is not installed`,
                    source: 'GestVenv',
                    code: 'missing-import',
                    data: { packageName: moduleName }
                });
            }
        }

        this.connection.sendDiagnostics({ uri: document.uri, diagnostics });
    }

    private isImportContext(line: string): boolean {
        return /^\s*(from\s+\S*\s*)?import\s+/.test(line);
    }

    private async getImportCompletions(): Promise<CompletionItem[]> {
        const packages = await this.getPackages();
        const items: CompletionItem[] = [];

        packages.forEach(pkg => {
            items.push({
                label: pkg.name,
                kind: CompletionItemKind.Module,
                detail: `${pkg.name} ${pkg.version}`,
                data: { packageName: pkg.name }
            });

            // Add modules
            pkg.modules?.forEach(module => {
                items.push({
                    label: module,
                    kind: CompletionItemKind.Module,
                    detail: `from ${pkg.name}`,
                    data: { packageName: pkg.name, module }
                });
            });
        });

        return items;
    }

    private async getPackages(): Promise<Package[]> {
        if (!this.activeEnvironment) {
            return [];
        }

        const cached = this.packageCache.get(this.activeEnvironment.id);
        if (cached) {
            return cached;
        }

        try {
            const response = await this.apiClient.get(
                `/api/v1/ide/environments/${this.activeEnvironment.id}/packages`
            );
            
            const packages = response.data;
            this.packageCache.set(this.activeEnvironment.id, packages);
            
            // Clear cache after 5 minutes
            setTimeout(() => {
                if (this.activeEnvironment) {
                    this.packageCache.delete(this.activeEnvironment.id);
                }
            }, 300000);
            
            return packages;
        } catch (error) {
            this.connection.console.error('Failed to get packages');
            return [];
        }
    }

    private getWordAtPosition(document: TextDocument, position: any): string | null {
        const text = document.getText();
        const offset = document.offsetAt(position);
        
        // Find word boundaries
        let start = offset;
        let end = offset;
        
        while (start > 0 && /\w/.test(text[start - 1])) {
            start--;
        }
        
        while (end < text.length && /\w/.test(text[end])) {
            end++;
        }
        
        return start < end ? text.substring(start, end) : null;
    }

    private isBuiltinModule(name: string): boolean {
        const builtins = [
            'sys', 'os', 'json', 'math', 'random', 'datetime', 'time',
            're', 'collections', 'itertools', 'functools', 'typing',
            'pathlib', 'io', 'asyncio', 'threading', 'subprocess'
        ];
        
        return builtins.includes(name) || name.startsWith('_');
    }
}

// Start the server
new GestVenvLanguageServer();