import axios, { AxiosInstance } from 'axios';
import * as vscode from 'vscode';

export interface Environment {
    id: string;
    name: string;
    path: string;
    python_version: string;
    backend: string;
    is_active: boolean;
    package_count: number;
    created_at: string;
    last_activated: string;
    packages?: Package[];
}

export interface Package {
    name: string;
    version: string;
    description?: string;
    modules?: string[];
    location?: string;
    metadata?: PackageMetadata;
}

export interface PackageMetadata {
    home_page?: string;
    author?: string;
    license?: string;
    requires_dist?: string[];
    download_stats?: {
        last_month: number;
        last_week: number;
    };
}

export interface CompletionContext {
    file_path: string;
    line: number;
    column: number;
    context: string;
}

export interface CompletionResponse {
    completions: CompletionItem[];
}

export interface CompletionItem {
    label: string;
    kind: string;
    detail?: string;
    documentation?: string;
    insertText?: string;
    data?: any;
}

export interface ImportAnalysis {
    imports: Import[];
    missing: string[];
    suggestions: Package[];
}

export interface Import {
    module: string;
    name?: string;
    alias?: string;
    line: number;
}

export interface OperationResult {
    success: boolean;
    message?: string;
    data?: any;
}

export class GestVenvAPI {
    private client: AxiosInstance;
    private cache: Map<string, { data: any; timestamp: number }> = new Map();
    private cacheTimeout = 300000; // 5 minutes

    constructor(private baseURL: string) {
        this.client = axios.create({
            baseURL,
            timeout: 10000,
            headers: {
                'Content-Type': 'application/json',
                'X-Client': 'vscode-extension'
            }
        });

        // Add request/response interceptors
        this.client.interceptors.response.use(
            response => response,
            error => {
                console.error('API Error:', error);
                throw error;
            }
        );
    }

    async testConnection(): Promise<boolean> {
        try {
            await this.client.get('/health');
            return true;
        } catch {
            return false;
        }
    }

    async listEnvironments(): Promise<Environment[]> {
        const cacheKey = 'environments';
        const cached = this.getCached(cacheKey);
        if (cached) { return cached; }

        const response = await this.client.get<Environment[]>('/api/v1/environments');
        this.setCache(cacheKey, response.data);
        return response.data;
    }

    async getEnvironment(envId: string): Promise<Environment> {
        const response = await this.client.get<Environment>(`/api/v1/environments/${envId}`);
        return response.data;
    }

    async createEnvironment(params: {
        name: string;
        backend?: string;
        python_version?: string;
        template?: string;
    }): Promise<Environment> {
        const response = await this.client.post<Environment>('/api/v1/environments', params);
        this.invalidateCache('environments');
        return response.data;
    }

    async detectActiveEnvironment(workspacePath: string): Promise<Environment | null> {
        try {
            const response = await this.client.post<Environment | null>('/api/v1/environments/detect', {
                workspace_path: workspacePath
            });
            return response.data;
        } catch {
            return null;
        }
    }

    async getPackages(envId: string): Promise<Package[]> {
        const cacheKey = `packages:${envId}`;
        const cached = this.getCached(cacheKey);
        if (cached) { return cached; }

        const response = await this.client.get<Package[]>(`/api/v1/ide/environments/${envId}/packages`);
        this.setCache(cacheKey, response.data);
        return response.data;
    }

    async getPackagesWithModules(envId: string): Promise<Package[]> {
        const packages = await this.getPackages(envId);
        
        // Fetch detailed info for packages without modules
        const packagesNeedingDetails = packages.filter(p => !p.modules);
        
        if (packagesNeedingDetails.length > 0) {
            const detailsPromises = packagesNeedingDetails.map(pkg =>
                this.getPackageDetails(envId, pkg.name)
            );
            
            const details = await Promise.all(detailsPromises);
            
            // Merge details back
            details.forEach((detail, index) => {
                const pkg = packagesNeedingDetails[index];
                pkg.modules = detail.modules;
                pkg.metadata = detail.metadata;
            });
        }
        
        return packages;
    }

    async getPackageDetails(envId: string, packageName: string): Promise<Package> {
        const response = await this.client.get<Package>(
            `/api/v1/ide/environments/${envId}/packages/${packageName}`
        );
        return response.data;
    }

    async installPackage(envId: string, packageName: string, options?: {
        version?: string;
        editable?: boolean;
        extras?: string[];
    }): Promise<OperationResult> {
        const response = await this.client.post<OperationResult>(
            `/api/v1/environments/${envId}/packages/install`,
            {
                package: packageName,
                ...options
            }
        );
        
        this.invalidateCache(`packages:${envId}`);
        return response.data;
    }

    async getCompletion(envId: string, context: CompletionContext): Promise<CompletionResponse> {
        const response = await this.client.post<CompletionResponse>(
            `/api/v1/ide/environments/${envId}/completion`,
            context
        );
        return response.data;
    }

    async getObjectAttributes(params: {
        environment_id: string;
        object_path: string;
        context: string;
    }): Promise<{ attributes: any[] }> {
        const response = await this.client.post<{ attributes: any[] }>(
            '/api/v1/ide/analysis/attributes',
            params
        );
        return response.data;
    }

    async analyzeImports(fileContent: string, filePath: string): Promise<ImportAnalysis> {
        const response = await this.client.post<ImportAnalysis>(
            '/api/v1/ide/analysis/imports',
            {
                file_content: fileContent,
                file_path: filePath
            }
        );
        return response.data;
    }

    async checkPackageExists(packageName: string): Promise<boolean> {
        try {
            const response = await this.client.get('/api/v1/packages/check', {
                params: { name: packageName }
            });
            return response.data.exists;
        } catch {
            return false;
        }
    }

    async syncDependencies(envId: string): Promise<OperationResult> {
        const response = await this.client.post<OperationResult>(
            `/api/v1/environments/${envId}/sync`
        );
        
        this.invalidateCache(`packages:${envId}`);
        return response.data;
    }

    async runCommand(envId: string, command: string): Promise<{
        stdout: string;
        stderr: string;
        returncode: number;
    }> {
        const response = await this.client.post(
            `/api/v1/environments/${envId}/run`,
            { command }
        );
        return response.data;
    }

    async getSuggestedImports(symbol: string): Promise<any[]> {
        const activeEnv = await this.getActiveEnvironment();
        if (!activeEnv) {
            return [];
        }
        
        const response = await this.client.get('/api/v1/ide/suggest/imports', {
            params: {
                symbol,
                environment_id: activeEnv.id
            }
        });
        return response.data.suggestions || [];
    }

    async analyzeCodeForRefactoring(params: {
        code: string;
        refactoring_type: string;
        context?: string;
    }): Promise<any> {
        const response = await this.client.post('/api/v1/ide/analyze/refactoring', params);
        return response.data;
    }

    async migrateEnvironment(params: {
        source_path: string;
        name: string;
        workspace_path: string;
    }): Promise<{ success: boolean; message?: string; environment?: Environment }> {
        try {
            const response = await this.client.post('/api/v1/environments/migrate', params);
            this.invalidateCache();
            return {
                success: true,
                environment: response.data
            };
        } catch (error: any) {
            return {
                success: false,
                message: error.response?.data?.detail || error.message
            };
        }
    }

    async getPackageInfo(packageName: string): Promise<any | null> {
        try {
            const response = await this.client.get(`/api/v1/packages/${packageName}/info`);
            return response.data;
        } catch (error: any) {
            console.error(`Failed to get package info for ${packageName}:`, error);
            return null;
        }
    }

    async updateAllPackages(envId: string): Promise<{ success: boolean; message?: string; updated_count?: number }> {
        try {
            const response = await this.client.post(`/api/v1/environments/${envId}/update-all`);
            this.invalidateCache(`packages:${envId}`);
            return {
                success: true,
                updated_count: response.data?.updated_count || 0
            };
        } catch (error: any) {
            return {
                success: false,
                message: error.response?.data?.detail || error.message
            };
        }
    }

    async deleteEnvironment(envId: string): Promise<{ success: boolean; message?: string }> {
        try {
            await this.client.delete(`/api/v1/environments/${envId}`);
            this.invalidateCache();
            return { success: true };
        } catch (error: any) {
            return { 
                success: false, 
                message: error.response?.data?.detail || error.message 
            };
        }
    }

    async uninstallPackages(envId: string, packages: string[]): Promise<{ success: boolean; message?: string }> {
        try {
            await this.client.post(
                `/api/v1/environments/${envId}/uninstall`,
                { packages }
            );
            this.invalidateCache(`packages:${envId}`);
            return { success: true };
        } catch (error: any) {
            return { 
                success: false, 
                message: error.response?.data?.detail || error.message 
            };
        }
    }


    private async getActiveEnvironment(): Promise<Environment | null> {
        try {
            const response = await this.client.post('/api/v1/environments/detect', {
                workspace_path: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd()
            });
            return response.data || null;
        } catch (error) {
            console.error('Failed to get active environment:', error);
            return null;
        }
    }

    private getCached(key: string): any {
        const cached = this.cache.get(key);
        if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
            return cached.data;
        }
        return null;
    }

    private setCache(key: string, data: any): void {
        this.cache.set(key, { data, timestamp: Date.now() });
    }

    private invalidateCache(pattern?: string): void {
        if (!pattern) {
            this.cache.clear();
            return;
        }

        for (const key of this.cache.keys()) {
            if (key.includes(pattern)) {
                this.cache.delete(key);
            }
        }
    }

    dispose(): void {
        this.cache.clear();
    }
}