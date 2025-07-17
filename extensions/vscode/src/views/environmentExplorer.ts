import * as vscode from 'vscode';
import { Environment, Package } from '../api/gestvenvClient';
import { EnvironmentProvider } from '../providers/environmentProvider';

export class EnvironmentExplorer implements vscode.TreeDataProvider<EnvironmentNode> {
    private _onDidChangeTreeData = new vscode.EventEmitter<EnvironmentNode | undefined | null | void>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    constructor(private provider: EnvironmentProvider) {
        // Subscribe to provider changes
        provider.onDidChangeEnvironments(() => this.refresh());
    }

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: EnvironmentNode): vscode.TreeItem {
        return element;
    }

    async getChildren(element?: EnvironmentNode): Promise<EnvironmentNode[]> {
        if (!element) {
            // Root level - show environments
            const environments = await this.provider.getEnvironments();
            return environments.map(env => new EnvironmentItem(env));
        }

        if (element instanceof EnvironmentItem) {
            // Environment children
            return [
                new DetailsNode(element.environment),
                new PackagesNode(element.environment),
                new ActionsNode(element.environment)
            ];
        }

        if (element instanceof PackagesNode) {
            // Show packages
            const packages = await this.provider.getPackages(element.environment.id);
            return packages.map(pkg => new PackageItem(pkg, element.environment));
        }

        if (element instanceof DetailsNode) {
            // Show environment details
            return [
                new DetailItem('Python Version', element.environment.python_version, 'versions'),
                new DetailItem('Backend', element.environment.backend, 'gear'),
                new DetailItem('Path', element.environment.path, 'folder'),
                new DetailItem('Created', new Date(element.environment.created_at).toLocaleDateString(), 'calendar'),
                new DetailItem('Packages', element.environment.package_count.toString(), 'package')
            ];
        }

        return [];
    }
}

abstract class EnvironmentNode extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState
    ) {
        super(label, collapsibleState);
    }
}

class EnvironmentItem extends EnvironmentNode {
    constructor(public readonly environment: Environment) {
        super(environment.name, vscode.TreeItemCollapsibleState.Collapsed);
        
        this.tooltip = `${environment.name} (${environment.python_version})`;
        this.description = environment.is_active ? '● Active' : '';
        
        // Set icon based on state
        this.iconPath = new vscode.ThemeIcon(
            environment.is_active ? 'vm-active' : 'vm',
            environment.is_active 
                ? new vscode.ThemeColor('charts.green')
                : new vscode.ThemeColor('foreground')
        );
        
        this.contextValue = 'environment';
    }
}

class PackagesNode extends EnvironmentNode {
    constructor(public readonly environment: Environment) {
        super('Packages', vscode.TreeItemCollapsibleState.Collapsed);
        this.iconPath = new vscode.ThemeIcon('package');
        this.description = `${environment.package_count} installed`;
        this.contextValue = 'packages';
    }
}

class DetailsNode extends EnvironmentNode {
    constructor(public readonly environment: Environment) {
        super('Details', vscode.TreeItemCollapsibleState.Collapsed);
        this.iconPath = new vscode.ThemeIcon('info');
        this.contextValue = 'details';
    }
}

class ActionsNode extends EnvironmentNode {
    constructor(public readonly environment: Environment) {
        super('Actions', vscode.TreeItemCollapsibleState.None);
        this.iconPath = new vscode.ThemeIcon('play');
        this.contextValue = 'actions';
        
        // Add inline actions
        this.command = {
            command: 'gestvenv.showEnvironmentActions',
            title: 'Show Actions',
            arguments: [environment]
        };
    }
}

class PackageItem extends EnvironmentNode {
    constructor(
        public readonly pkg: Package,
        public readonly environment: Environment
    ) {
        super(pkg.name, vscode.TreeItemCollapsibleState.None);
        
        this.description = pkg.version;
        this.tooltip = `${pkg.name} ${pkg.version}${pkg.description ? '\n' + pkg.description : ''}`;
        this.iconPath = new vscode.ThemeIcon('library');
        this.contextValue = 'package';
        
        // Add command to show package details
        this.command = {
            command: 'gestvenv.showPackageDetails',
            title: 'Show Package Details',
            arguments: [pkg, environment]
        };
    }
}

class DetailItem extends EnvironmentNode {
    constructor(
        label: string,
        public readonly value: string,
        iconId?: string
    ) {
        super(label, vscode.TreeItemCollapsibleState.None);
        
        this.description = value;
        if (iconId) {
            this.iconPath = new vscode.ThemeIcon(iconId);
        }
        this.contextValue = 'detail';
    }
}