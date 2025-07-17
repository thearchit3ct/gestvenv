// Mock VS Code API for unit tests
export enum CompletionItemKind {
    Text = 0,
    Method = 1,
    Function = 2,
    Constructor = 3,
    Field = 4,
    Variable = 5,
    Class = 6,
    Interface = 7,
    Module = 8,
    Property = 9,
    Unit = 10,
    Value = 11,
    Enum = 12,
    Keyword = 13,
    Snippet = 14,
    Color = 15,
    File = 16,
    Reference = 17,
    Folder = 18,
    EnumMember = 19,
    Constant = 20,
    Struct = 21,
    Event = 22,
    Operator = 23,
    TypeParameter = 24
}

export class CompletionItem {
    label: string;
    kind?: CompletionItemKind;
    detail?: string;
    documentation?: any;
    insertText?: string;
    
    constructor(label: string, kind?: CompletionItemKind) {
        this.label = label;
        this.kind = kind;
    }
}

export class Range {
    constructor(
        public start: Position,
        public end: Position
    ) {}
}

export class Position {
    constructor(
        public line: number,
        public character: number
    ) {}
}

export class Uri {
    static file(path: string): Uri {
        return new Uri('file', path);
    }
    
    constructor(
        public scheme: string,
        public path: string
    ) {}
    
    get fsPath(): string {
        return this.path;
    }
}

export const workspace = {
    workspaceFolders: [{
        uri: Uri.file('/test/workspace')
    }],
    getConfiguration: (section: string) => ({
        get: (key: string, defaultValue?: any) => defaultValue,
        update: async () => {},
        has: () => false,
        inspect: () => undefined
    })
};

export const window = {
    showInformationMessage: async (message: string) => undefined,
    showErrorMessage: async (message: string) => undefined,
    showWarningMessage: async (message: string) => undefined,
    showQuickPick: async (items: any[]) => items[0],
    showInputBox: async () => 'test-input'
};

export const languages = {
    createDiagnosticCollection: () => ({
        set: () => {},
        clear: () => {},
        dispose: () => {}
    })
};

export const env = {
    machineId: 'test-machine-id'
};

export const version = '1.85.0';

export const extensions = {
    getExtension: (id: string) => ({
        packageJSON: { version: '0.1.0' }
    })
};