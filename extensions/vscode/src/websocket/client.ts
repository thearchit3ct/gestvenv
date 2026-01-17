import * as vscode from 'vscode';
import { EventEmitter } from 'events';
import WebSocket from 'ws';

export interface WebSocketMessage {
    type: string;
    data?: any;
    timestamp?: string;
    error?: string;
}

export interface WebSocketOptions {
    autoReconnect?: boolean;
    reconnectInterval?: number;
    maxReconnectAttempts?: number;
}

export class WebSocketClient extends EventEmitter {
    private ws: WebSocket | null = null;
    private url: string;
    private clientId: string;
    private options: WebSocketOptions;
    private reconnectAttempts = 0;
    private reconnectTimer: NodeJS.Timeout | null = null;
    private pingTimer: NodeJS.Timeout | null = null;
    private isConnected = false;
    private messageQueue: WebSocketMessage[] = [];

    constructor(url: string, clientId: string, options: WebSocketOptions = {}) {
        super();
        this.url = url;
        this.clientId = clientId;
        this.options = {
            autoReconnect: true,
            reconnectInterval: 5000,
            maxReconnectAttempts: 10,
            ...options
        };
    }

    connect(): Promise<void> {
        return new Promise((resolve, reject) => {
            try {
                // Add client ID and metadata to URL
                const urlWithParams = new URL(this.url);
                urlWithParams.pathname = `/ws/ide/${this.clientId}`;
                urlWithParams.searchParams.set('vscode_version', vscode.version);
                urlWithParams.searchParams.set('extension_version', this.getExtensionVersion());
                
                const workspace = vscode.workspace.workspaceFolders?.[0];
                if (workspace) {
                    urlWithParams.searchParams.set('workspace', workspace.uri.fsPath);
                }

                this.ws = new WebSocket(urlWithParams.toString());

                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    this.isConnected = true;
                    this.reconnectAttempts = 0;
                    this.emit('connected');
                    this.startPing();
                    this.flushMessageQueue();
                    resolve();
                };

                this.ws.onmessage = (event: WebSocket.MessageEvent) => {
                    try {
                        const message: WebSocketMessage = JSON.parse(event.data.toString());
                        this.handleMessage(message);
                    } catch (error) {
                        console.error('Failed to parse WebSocket message:', error);
                    }
                };

                this.ws.onerror = (error: WebSocket.ErrorEvent) => {
                    console.error('WebSocket error:', error);
                    this.emit('error', error);
                };

                this.ws.onclose = (event: WebSocket.CloseEvent) => {
                    console.log('WebSocket disconnected:', event.code, event.reason);
                    this.isConnected = false;
                    this.stopPing();
                    this.emit('disconnected', event);
                    
                    if (this.options.autoReconnect && 
                        this.reconnectAttempts < this.options.maxReconnectAttempts!) {
                        this.scheduleReconnect();
                    }
                };

            } catch (error) {
                reject(error);
            }
        });
    }

    disconnect() {
        this.options.autoReconnect = false;
        
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        
        this.stopPing();
        
        if (this.ws) {
            this.ws.close(1000, 'Client disconnect');
            this.ws = null;
        }
        
        this.isConnected = false;
    }

    send(message: WebSocketMessage): void {
        if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            // Queue message for later
            this.messageQueue.push(message);
        }
    }

    subscribe(environmentId: string): void {
        this.send({
            type: 'subscribe',
            data: { environment_id: environmentId }
        });
    }

    unsubscribe(environmentId: string): void {
        this.send({
            type: 'unsubscribe',
            data: { environment_id: environmentId }
        });
    }

    private handleMessage(message: WebSocketMessage) {
        // Emit specific events based on message type
        this.emit('message', message);
        
        // Handle specific message types
        switch (message.type) {
            case 'connection':
                this.emit('connection', message.data);
                break;
            
            case 'environment:updated':
            case 'environment:created':
            case 'environment:deleted':
                this.emit('environment-change', message);
                break;
                
            case 'package:installed':
            case 'package:uninstalled':
            case 'package:updated':
                this.emit('package-change', message);
                break;
                
            case 'task:started':
            case 'task:completed':
            case 'task:failed':
                this.emit('task-update', message);
                break;
                
            case 'error':
                this.emit('error', new Error(message.error || 'Unknown error'));
                break;
                
            case 'pong':
                // Heartbeat response
                break;
        }
    }

    private scheduleReconnect() {
        if (this.reconnectTimer) {
            return;
        }
        
        this.reconnectAttempts++;
        const delay = this.options.reconnectInterval! * Math.min(this.reconnectAttempts, 5);
        
        console.log(`Scheduling reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
        
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.connect().catch(error => {
                console.error('Reconnect failed:', error);
            });
        }, delay);
    }

    private startPing() {
        this.pingTimer = setInterval(() => {
            if (this.isConnected) {
                this.send({ type: 'ping' });
            }
        }, 30000); // Ping every 30 seconds
    }

    private stopPing() {
        if (this.pingTimer) {
            clearInterval(this.pingTimer);
            this.pingTimer = null;
        }
    }

    private flushMessageQueue() {
        while (this.messageQueue.length > 0 && this.isConnected) {
            const message = this.messageQueue.shift()!;
            this.send(message);
        }
    }

    private getExtensionVersion(): string {
        const extension = vscode.extensions.getExtension('gestvenv.gestvenv-vscode');
        return extension?.packageJSON.version || 'unknown';
    }

    // Task-specific methods
    async installPackage(environmentId: string, packageName: string, version?: string): Promise<void> {
        return new Promise((resolve, reject) => {
            const taskId = `install_${packageName}_${Date.now()}`;
            
            const handler = (message: WebSocketMessage) => {
                if (message.data?.task_id === taskId) {
                    if (message.type === 'task:completed') {
                        this.removeListener('task-update', handler);
                        resolve();
                    } else if (message.type === 'task:failed') {
                        this.removeListener('task-update', handler);
                        reject(new Error(message.data.error || 'Installation failed'));
                    }
                }
            };
            
            this.on('task-update', handler);
            
            this.send({
                type: 'package:install',
                data: {
                    environment_id: environmentId,
                    package_name: packageName,
                    version
                }
            });
        });
    }

    async uninstallPackage(environmentId: string, packageName: string): Promise<void> {
        return new Promise((resolve, reject) => {
            const taskId = `uninstall_${packageName}_${Date.now()}`;
            
            const handler = (message: WebSocketMessage) => {
                if (message.data?.task_id === taskId) {
                    if (message.type === 'task:completed') {
                        this.removeListener('task-update', handler);
                        resolve();
                    } else if (message.type === 'task:failed') {
                        this.removeListener('task-update', handler);
                        reject(new Error(message.data.error || 'Uninstallation failed'));
                    }
                }
            };
            
            this.on('task-update', handler);
            
            this.send({
                type: 'package:uninstall',
                data: {
                    environment_id: environmentId,
                    package_name: packageName
                }
            });
        });
    }

    async analyzeCode(code: string, filePath: string, environmentId?: string): Promise<any> {
        return new Promise((resolve, reject) => {
            const handler = (message: WebSocketMessage) => {
                if (message.type === 'code:analysis') {
                    this.removeListener('message', handler);
                    resolve(message.data.analysis);
                }
            };
            
            this.on('message', handler);
            
            this.send({
                type: 'code:analyze',
                data: {
                    code,
                    file_path: filePath,
                    environment_id: environmentId
                }
            });
            
            // Timeout after 5 seconds
            setTimeout(() => {
                this.removeListener('message', handler);
                reject(new Error('Code analysis timeout'));
            }, 5000);
        });
    }
}