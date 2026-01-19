import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { GestVenvAPI, Environment } from '../api/gestvenvClient';

/**
 * Résultat de détection d'environnement
 */
export interface DetectionResult {
    found: boolean;
    type: 'gestvenv' | 'venv' | 'virtualenv' | 'conda' | 'poetry' | 'pdm' | 'uv' | 'none';
    path?: string;
    pythonPath?: string;
    projectFile?: string;
    suggestedAction?: 'activate' | 'create' | 'migrate';
    environment?: Environment;
}

/**
 * Configuration de projet détectée
 */
export interface ProjectConfig {
    hasRequirementsTxt: boolean;
    hasPyprojectToml: boolean;
    hasSetupPy: boolean;
    hasPipfile: boolean;
    hasCondaYaml: boolean;
    hasPoetryLock: boolean;
    hasPdmLock: boolean;
    hasUvLock: boolean;
    hasGestvenvConfig: boolean;
    pythonVersion?: string;
    dependencies: string[];
}

/**
 * Utilitaires de détection d'environnements Python
 */
export class EnvironmentDetector {
    private workspaceRoot: string | undefined;
    private api: GestVenvAPI;
    private diagnosticCollection: vscode.DiagnosticCollection;

    constructor(api: GestVenvAPI) {
        this.api = api;
        this.workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('gestvenv-detection');
    }

    /**
     * Détecte l'environnement Python actif dans le workspace
     */
    async detectEnvironment(): Promise<DetectionResult> {
        if (!this.workspaceRoot) {
            return { found: false, type: 'none' };
        }

        // 1. Vérifier si un environnement GestVenv existe
        const gestvenvResult = await this.checkGestvenvEnvironment();
        if (gestvenvResult.found) {
            return gestvenvResult;
        }

        // 2. Vérifier les autres types d'environnements
        const venvPath = this.findVirtualEnvironment();
        if (venvPath) {
            return {
                found: true,
                type: this.detectVenvType(venvPath),
                path: venvPath,
                pythonPath: this.findPythonExecutable(venvPath),
                suggestedAction: 'migrate'
            };
        }

        // 3. Analyser les fichiers de configuration
        const config = await this.analyzeProjectConfig();
        if (config.hasPyprojectToml || config.hasRequirementsTxt) {
            return {
                found: false,
                type: 'none',
                projectFile: config.hasPyprojectToml ? 'pyproject.toml' : 'requirements.txt',
                suggestedAction: 'create'
            };
        }

        return { found: false, type: 'none', suggestedAction: 'create' };
    }

    /**
     * Vérifie si un environnement GestVenv existe
     */
    private async checkGestvenvEnvironment(): Promise<DetectionResult> {
        if (!this.workspaceRoot) {
            return { found: false, type: 'none' };
        }

        // Vérifier le fichier .gestvenv
        const gestvenvConfigPath = path.join(this.workspaceRoot, '.gestvenv');
        if (fs.existsSync(gestvenvConfigPath)) {
            try {
                const configContent = fs.readFileSync(gestvenvConfigPath, 'utf-8');
                const config = JSON.parse(configContent);

                if (config.environment_id) {
                    const env = await this.api.getEnvironment(config.environment_id);
                    if (env) {
                        return {
                            found: true,
                            type: 'gestvenv',
                            path: env.path,
                            pythonPath: path.join(env.path, 'bin', 'python'),
                            environment: env,
                            suggestedAction: 'activate'
                        };
                    }
                }
            } catch (error) {
                console.error('Error reading .gestvenv config:', error);
            }
        }

        // Vérifier si le dossier .gestvenv existe
        const gestvenvDir = path.join(this.workspaceRoot, '.gestvenv');
        if (fs.existsSync(gestvenvDir) && fs.statSync(gestvenvDir).isDirectory()) {
            return {
                found: true,
                type: 'gestvenv',
                path: gestvenvDir,
                pythonPath: this.findPythonExecutable(gestvenvDir),
                suggestedAction: 'activate'
            };
        }

        return { found: false, type: 'none' };
    }

    /**
     * Recherche un environnement virtuel dans le workspace
     */
    private findVirtualEnvironment(): string | null {
        if (!this.workspaceRoot) return null;

        const possiblePaths = [
            '.venv',
            'venv',
            'env',
            '.env',
            'virtualenv',
            '.virtualenv',
            'conda',
            '.conda'
        ];

        for (const venvName of possiblePaths) {
            const venvPath = path.join(this.workspaceRoot, venvName);
            if (fs.existsSync(venvPath) && this.isValidVirtualEnvironment(venvPath)) {
                return venvPath;
            }
        }

        return null;
    }

    /**
     * Vérifie si un chemin est un environnement virtuel valide
     */
    private isValidVirtualEnvironment(envPath: string): boolean {
        // Vérifier la présence de bin/python ou Scripts/python.exe
        const pythonPath = this.findPythonExecutable(envPath);
        if (!pythonPath) return false;

        // Vérifier la présence de pyvenv.cfg ou activate
        const pyvenvCfg = path.join(envPath, 'pyvenv.cfg');
        const activateScript = path.join(envPath, 'bin', 'activate');
        const activateScriptWin = path.join(envPath, 'Scripts', 'activate.bat');

        return fs.existsSync(pyvenvCfg) ||
               fs.existsSync(activateScript) ||
               fs.existsSync(activateScriptWin);
    }

    /**
     * Trouve l'exécutable Python dans un environnement
     */
    private findPythonExecutable(envPath: string): string | undefined {
        const possiblePaths = [
            path.join(envPath, 'bin', 'python3'),
            path.join(envPath, 'bin', 'python'),
            path.join(envPath, 'Scripts', 'python.exe'),
            path.join(envPath, 'python.exe')
        ];

        for (const p of possiblePaths) {
            if (fs.existsSync(p)) {
                return p;
            }
        }

        return undefined;
    }

    /**
     * Détecte le type d'environnement virtuel
     */
    private detectVenvType(venvPath: string): DetectionResult['type'] {
        // Vérifier si c'est Conda
        const condaMeta = path.join(venvPath, 'conda-meta');
        if (fs.existsSync(condaMeta)) {
            return 'conda';
        }

        // Vérifier si c'est Poetry
        if (this.workspaceRoot) {
            const poetryLock = path.join(this.workspaceRoot, 'poetry.lock');
            if (fs.existsSync(poetryLock)) {
                return 'poetry';
            }
        }

        // Vérifier si c'est PDM
        if (this.workspaceRoot) {
            const pdmLock = path.join(this.workspaceRoot, 'pdm.lock');
            if (fs.existsSync(pdmLock)) {
                return 'pdm';
            }
        }

        // Vérifier si c'est UV
        if (this.workspaceRoot) {
            const uvLock = path.join(this.workspaceRoot, 'uv.lock');
            if (fs.existsSync(uvLock)) {
                return 'uv';
            }
        }

        // Vérifier le pyvenv.cfg pour virtualenv vs venv
        const pyvenvCfg = path.join(venvPath, 'pyvenv.cfg');
        if (fs.existsSync(pyvenvCfg)) {
            const content = fs.readFileSync(pyvenvCfg, 'utf-8');
            if (content.includes('virtualenv')) {
                return 'virtualenv';
            }
        }

        return 'venv';
    }

    /**
     * Analyse la configuration du projet
     */
    async analyzeProjectConfig(): Promise<ProjectConfig> {
        const config: ProjectConfig = {
            hasRequirementsTxt: false,
            hasPyprojectToml: false,
            hasSetupPy: false,
            hasPipfile: false,
            hasCondaYaml: false,
            hasPoetryLock: false,
            hasPdmLock: false,
            hasUvLock: false,
            hasGestvenvConfig: false,
            dependencies: []
        };

        if (!this.workspaceRoot) {
            return config;
        }

        // Vérifier les fichiers de configuration
        config.hasRequirementsTxt = fs.existsSync(path.join(this.workspaceRoot, 'requirements.txt'));
        config.hasPyprojectToml = fs.existsSync(path.join(this.workspaceRoot, 'pyproject.toml'));
        config.hasSetupPy = fs.existsSync(path.join(this.workspaceRoot, 'setup.py'));
        config.hasPipfile = fs.existsSync(path.join(this.workspaceRoot, 'Pipfile'));
        config.hasCondaYaml = fs.existsSync(path.join(this.workspaceRoot, 'environment.yml')) ||
                              fs.existsSync(path.join(this.workspaceRoot, 'environment.yaml'));
        config.hasPoetryLock = fs.existsSync(path.join(this.workspaceRoot, 'poetry.lock'));
        config.hasPdmLock = fs.existsSync(path.join(this.workspaceRoot, 'pdm.lock'));
        config.hasUvLock = fs.existsSync(path.join(this.workspaceRoot, 'uv.lock'));
        config.hasGestvenvConfig = fs.existsSync(path.join(this.workspaceRoot, '.gestvenv'));

        // Extraire les dépendances
        if (config.hasRequirementsTxt) {
            config.dependencies = this.parseRequirementsTxt(
                path.join(this.workspaceRoot, 'requirements.txt')
            );
        } else if (config.hasPyprojectToml) {
            const pyprojectData = await this.parsePyprojectToml(
                path.join(this.workspaceRoot, 'pyproject.toml')
            );
            config.dependencies = pyprojectData.dependencies;
            config.pythonVersion = pyprojectData.pythonVersion;
        }

        return config;
    }

    /**
     * Parse un fichier requirements.txt
     */
    private parseRequirementsTxt(filePath: string): string[] {
        try {
            const content = fs.readFileSync(filePath, 'utf-8');
            return content
                .split('\n')
                .map(line => line.trim())
                .filter(line => line && !line.startsWith('#') && !line.startsWith('-'))
                .map(line => {
                    // Extraire le nom du package (avant ==, >=, etc.)
                    const match = line.match(/^([a-zA-Z0-9_-]+)/);
                    return match ? match[1] : line;
                });
        } catch {
            return [];
        }
    }

    /**
     * Parse un fichier pyproject.toml
     */
    private async parsePyprojectToml(filePath: string): Promise<{ dependencies: string[], pythonVersion?: string }> {
        try {
            const content = fs.readFileSync(filePath, 'utf-8');
            const result: { dependencies: string[], pythonVersion?: string } = { dependencies: [] };

            // Extraire la version Python requise
            const pythonMatch = content.match(/requires-python\s*=\s*["']([^"']+)["']/);
            if (pythonMatch) {
                result.pythonVersion = pythonMatch[1];
            }

            // Extraire les dépendances (format basique, ne gère pas tous les cas TOML)
            const depsMatch = content.match(/dependencies\s*=\s*\[([\s\S]*?)\]/);
            if (depsMatch) {
                const depsBlock = depsMatch[1];
                const deps = depsBlock.match(/["']([a-zA-Z0-9_-]+)(?:[^"']*)?["']/g);
                if (deps) {
                    result.dependencies = deps.map(d => d.replace(/["']/g, '').split(/[<>=\[]/)[0]);
                }
            }

            return result;
        } catch {
            return { dependencies: [] };
        }
    }

    /**
     * Vérifie si des packages sont manquants
     */
    async checkMissingPackages(environment: Environment): Promise<string[]> {
        const config = await this.analyzeProjectConfig();
        const installedPackages = await this.api.getPackages(environment.id);
        const installedNames = new Set(installedPackages.map(p => p.name.toLowerCase()));

        return config.dependencies.filter(dep => !installedNames.has(dep.toLowerCase()));
    }

    /**
     * Propose des actions basées sur la détection
     */
    async suggestActions(result: DetectionResult): Promise<void> {
        if (!result.found && result.suggestedAction === 'create') {
            const action = await vscode.window.showInformationMessage(
                'Aucun environnement Python détecté. Voulez-vous en créer un?',
                'Créer un environnement',
                'Ignorer'
            );

            if (action === 'Créer un environnement') {
                vscode.commands.executeCommand('gestvenv.createEnvironment');
            }
        } else if (result.type !== 'gestvenv' && result.suggestedAction === 'migrate') {
            const action = await vscode.window.showInformationMessage(
                `Environnement ${result.type} détecté. Voulez-vous le migrer vers GestVenv?`,
                'Migrer',
                'Utiliser tel quel',
                'Ignorer'
            );

            if (action === 'Migrer') {
                vscode.commands.executeCommand('gestvenv.migrateEnvironment', result.path);
            }
        } else if (result.found && result.suggestedAction === 'activate') {
            // Auto-activation si configuré
            const config = vscode.workspace.getConfiguration('gestvenv');
            if (config.get<boolean>('autoActivate', true)) {
                if (result.environment) {
                    vscode.commands.executeCommand('gestvenv.activateEnvironment', result.environment);
                }
            }
        }
    }

    /**
     * Active la surveillance des fichiers de configuration
     */
    startWatching(): vscode.Disposable[] {
        const disposables: vscode.Disposable[] = [];

        // Surveiller les changements dans requirements.txt
        const requirementsWatcher = vscode.workspace.createFileSystemWatcher('**/requirements.txt');
        requirementsWatcher.onDidChange(() => this.onConfigFileChanged('requirements.txt'));
        requirementsWatcher.onDidCreate(() => this.onConfigFileChanged('requirements.txt'));
        disposables.push(requirementsWatcher);

        // Surveiller les changements dans pyproject.toml
        const pyprojectWatcher = vscode.workspace.createFileSystemWatcher('**/pyproject.toml');
        pyprojectWatcher.onDidChange(() => this.onConfigFileChanged('pyproject.toml'));
        pyprojectWatcher.onDidCreate(() => this.onConfigFileChanged('pyproject.toml'));
        disposables.push(pyprojectWatcher);

        // Surveiller les changements dans .gestvenv
        const gestvenvWatcher = vscode.workspace.createFileSystemWatcher('**/.gestvenv');
        gestvenvWatcher.onDidChange(() => this.onConfigFileChanged('.gestvenv'));
        gestvenvWatcher.onDidCreate(() => this.onConfigFileChanged('.gestvenv'));
        gestvenvWatcher.onDidDelete(() => this.onConfigFileDeleted('.gestvenv'));
        disposables.push(gestvenvWatcher);

        return disposables;
    }

    private async onConfigFileChanged(fileName: string): Promise<void> {
        console.log(`Configuration file changed: ${fileName}`);

        // Proposer de synchroniser les dépendances
        if (fileName === 'requirements.txt' || fileName === 'pyproject.toml') {
            const result = await this.detectEnvironment();
            if (result.found && result.environment) {
                const missingPackages = await this.checkMissingPackages(result.environment);
                if (missingPackages.length > 0) {
                    const action = await vscode.window.showInformationMessage(
                        `${missingPackages.length} nouveau(x) package(s) détecté(s). Synchroniser?`,
                        'Synchroniser',
                        'Ignorer'
                    );

                    if (action === 'Synchroniser') {
                        vscode.commands.executeCommand('gestvenv.syncDependencies', result.environment);
                    }
                }
            }
        }
    }

    private async onConfigFileDeleted(fileName: string): Promise<void> {
        if (fileName === '.gestvenv') {
            vscode.window.showWarningMessage(
                'Configuration GestVenv supprimée. L\'environnement a été désactivé.'
            );
            vscode.commands.executeCommand('gestvenv.refreshEnvironments');
        }
    }

    dispose(): void {
        this.diagnosticCollection.dispose();
    }
}

/**
 * Créer un fichier de configuration GestVenv
 */
export async function createGestvenvConfig(
    workspacePath: string,
    environmentId: string,
    options: { autoActivate?: boolean; syncOnChange?: boolean } = {}
): Promise<void> {
    const configPath = path.join(workspacePath, '.gestvenv');
    const config = {
        environment_id: environmentId,
        auto_activate: options.autoActivate ?? true,
        sync_on_change: options.syncOnChange ?? true,
        created_at: new Date().toISOString()
    };

    fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
}

/**
 * Lire la configuration GestVenv
 */
export function readGestvenvConfig(workspacePath: string): any | null {
    const configPath = path.join(workspacePath, '.gestvenv');
    if (!fs.existsSync(configPath)) {
        return null;
    }

    try {
        const content = fs.readFileSync(configPath, 'utf-8');
        return JSON.parse(content);
    } catch {
        return null;
    }
}
