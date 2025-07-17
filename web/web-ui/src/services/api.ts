import axios, { AxiosInstance, AxiosResponse } from 'axios'
import type {
  Environment,
  EnvironmentDetails,
  EnvironmentCreate,
  Package,
  PackageInstall,
  CacheInfo,
  SystemInfo,
  Operation,
  TemplateInfo,
  ApiResponse
} from '@/types'

class ApiService {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: '/api/v1',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json'
      }
    })

    // Intercepteurs pour la gestion des erreurs
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('API Error:', error)
        return Promise.reject(error)
      }
    )
  }

  // ===== Environnements =====

  async getEnvironments(params?: {
    backend?: string
    status?: string
    sort_by?: string
  }): Promise<Environment[]> {
    const response = await this.client.get<Environment[]>('/environments', { params })
    return response.data
  }

  async getEnvironment(name: string): Promise<EnvironmentDetails> {
    const response = await this.client.get<EnvironmentDetails>(`/environments/${name}`)
    return response.data
  }

  async createEnvironment(data: EnvironmentCreate): Promise<ApiResponse> {
    const response = await this.client.post<ApiResponse>('/environments', data)
    return response.data
  }

  async deleteEnvironment(name: string, force = false): Promise<ApiResponse> {
    const response = await this.client.delete<ApiResponse>(`/environments/${name}`, {
      params: { force }
    })
    return response.data
  }

  async activateEnvironment(name: string): Promise<ApiResponse> {
    const response = await this.client.post<ApiResponse>(`/environments/${name}/activate`)
    return response.data
  }

  async syncEnvironment(
    name: string,
    params?: { groups?: string; clean?: boolean }
  ): Promise<ApiResponse> {
    const response = await this.client.post<ApiResponse>(`/environments/${name}/sync`, null, {
      params
    })
    return response.data
  }

  // ===== Packages =====

  async getEnvironmentPackages(
    name: string,
    params?: { group?: string; outdated_only?: boolean }
  ): Promise<Package[]> {
    const response = await this.client.get<Package[]>(`/environments/${name}/packages`, {
      params
    })
    return response.data
  }

  async installPackage(envName: string, packageData: PackageInstall): Promise<ApiResponse> {
    const response = await this.client.post<ApiResponse>('/packages/install', packageData, {
      params: { env_name: envName }
    })
    return response.data
  }

  async uninstallPackage(envName: string, packageName: string): Promise<ApiResponse> {
    const response = await this.client.delete<ApiResponse>(`/packages/${packageName}`, {
      params: { env_name: envName }
    })
    return response.data
  }

  async updatePackages(
    envName: string,
    packages?: string[]
  ): Promise<ApiResponse> {
    const response = await this.client.post<ApiResponse>('/packages/update', null, {
      params: { env_name: envName, packages: packages?.join(',') }
    })
    return response.data
  }

  // ===== Cache =====

  async getCacheInfo(): Promise<CacheInfo> {
    const response = await this.client.get<CacheInfo>('/cache/info')
    return response.data
  }

  async cleanCache(params?: {
    older_than?: number
    size_limit?: string
  }): Promise<ApiResponse> {
    const response = await this.client.post<ApiResponse>('/cache/clean', null, { params })
    return response.data
  }

  async exportCache(outputPath: string, compress = true): Promise<ApiResponse> {
    const response = await this.client.post<ApiResponse>('/cache/export', {
      output_path: outputPath,
      compress
    })
    return response.data
  }

  async importCache(
    sourcePath: string,
    merge = false,
    verify = true
  ): Promise<ApiResponse> {
    const response = await this.client.post<ApiResponse>('/cache/import', {
      source_path: sourcePath,
      merge,
      verify
    })
    return response.data
  }

  // ===== Système =====

  async getSystemInfo(): Promise<SystemInfo> {
    const response = await this.client.get<SystemInfo>('/system/info')
    return response.data
  }

  async getSystemHealth(): Promise<any> {
    const response = await this.client.get('/system/health')
    return response.data
  }

  async runDoctor(params?: {
    env_name?: string
    auto_fix?: boolean
  }): Promise<ApiResponse> {
    const response = await this.client.post<ApiResponse>('/system/doctor', null, { params })
    return response.data
  }

  async cleanupSystem(params?: {
    orphaned_only?: boolean
    clean_cache?: boolean
  }): Promise<ApiResponse> {
    const response = await this.client.post<ApiResponse>('/system/cleanup', null, { params })
    return response.data
  }

  // ===== Opérations =====

  async getOperations(operationType?: string): Promise<Operation[]> {
    const response = await this.client.get<Operation[]>('/system/operations', {
      params: { operation_type: operationType }
    })
    return response.data
  }

  async getOperation(operationId: string): Promise<Operation> {
    const response = await this.client.get<Operation>(`/system/operations/${operationId}`)
    return response.data
  }

  async cancelOperation(operationId: string): Promise<ApiResponse> {
    const response = await this.client.post<ApiResponse>(`/system/operations/${operationId}/cancel`)
    return response.data
  }

  // ===== Templates =====

  async getTemplates(): Promise<TemplateInfo[]> {
    const response = await this.client.get<TemplateInfo[]>('/templates')
    return response.data
  }

  async createFromTemplate(data: {
    template_name: string
    project_name: string
    author?: string
    email?: string
    version?: string
    python_version?: string
    backend?: string
    output_path?: string
    variables?: Record<string, string>
  }): Promise<ApiResponse> {
    const response = await this.client.post<ApiResponse>('/templates/create', data)
    return response.data
  }

  // ===== Health Check =====

  async healthCheck(): Promise<{ status: string; version: string; service: string }> {
    const response = await this.client.get('/health')
    return response.data
  }
}

// Instance exportée
export const api = new ApiService()
export default api