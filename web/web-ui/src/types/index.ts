// Types pour l'interface GestVenv Web

export interface Environment {
  name: string
  path: string
  python_version?: string
  backend: BackendType
  status: EnvironmentStatus
  created_at: string
  last_used?: string
  package_count: number
  size_mb: number
  active: boolean
}

export interface EnvironmentDetails extends Environment {
  packages: Package[]
  config: Record<string, any>
  health_info: Record<string, any>
}

export interface EnvironmentCreate {
  name: string
  python_version?: string
  backend: BackendType
  template?: string
  packages?: string[]
  path?: string
  author?: string
  email?: string
  version?: string
  output?: string
}

export interface Package {
  name: string
  version?: string
  installed_version?: string
  latest_version?: string
  status: PackageStatus
  group: string
  size_mb: number
  description?: string
}

export interface PackageInstall {
  name: string
  version?: string
  group?: string
  editable?: boolean
  upgrade?: boolean
}

export interface CacheInfo {
  total_size_mb: number
  package_count: number
  hit_rate: number
  location: string
  last_cleanup?: string
}

export interface SystemInfo {
  os: string
  python_version: string
  gestvenv_version: string
  backends_available: BackendType[]
  disk_usage: Record<string, number>
  memory_usage: Record<string, number>
}

export interface Operation {
  id: string
  type: string
  status: OperationStatus
  progress: number
  message: string
  started_at: string
  completed_at?: string
  result?: Record<string, any>
  error?: string
}

export interface TemplateInfo {
  name: string
  description: string
  category: string
  dependencies: string[]
  files: string[]
  variables: string[]
}

export interface ApiResponse<T = any> {
  success: boolean
  message: string
  data?: T
}

// Enums
export enum EnvironmentStatus {
  HEALTHY = 'healthy',
  WARNING = 'warning',
  ERROR = 'error',
  CREATING = 'creating',
  DELETING = 'deleting'
}

export enum BackendType {
  PIP = 'pip',
  UV = 'uv',
  POETRY = 'poetry',
  PDM = 'pdm',
  AUTO = 'auto'
}

export enum PackageStatus {
  INSTALLED = 'installed',
  OUTDATED = 'outdated',
  MISSING = 'missing'
}

export enum OperationStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

// WebSocket types
export interface WSMessage {
  type: WSMessageType
  data: Record<string, any>
  timestamp: string
}

export enum WSMessageType {
  ENVIRONMENT_CREATED = 'environment_created',
  ENVIRONMENT_DELETED = 'environment_deleted',
  ENVIRONMENT_UPDATED = 'environment_updated',
  PACKAGE_INSTALLED = 'package_installed',
  PACKAGE_UNINSTALLED = 'package_uninstalled',
  OPERATION_PROGRESS = 'operation_progress',
  OPERATION_COMPLETED = 'operation_completed',
  CACHE_UPDATED = 'cache_updated'
}

// Filtres et tri
export interface EnvironmentFilters {
  backend?: BackendType
  status?: EnvironmentStatus
  search?: string
}

export interface EnvironmentSort {
  field: 'name' | 'created' | 'used' | 'size'
  direction: 'asc' | 'desc'
}

// Formulaires
export interface CreateEnvironmentForm {
  name: string
  python_version: string
  backend: BackendType
  template: string
  packages: string[]
  useTemplate: boolean
  templateData: {
    author: string
    email: string
    version: string
    output: string
  }
}

export interface InstallPackageForm {
  package: string
  group: string
  editable: boolean
  upgrade: boolean
}

// Configuration
export interface AppConfig {
  apiBaseUrl: string
  wsUrl: string
  theme: 'light' | 'dark' | 'auto'
  language: string
  autoRefresh: boolean
  refreshInterval: number
}

// Navigation
export interface NavigationItem {
  name: string
  path: string
  icon: string
  badge?: string | number
  children?: NavigationItem[]
}