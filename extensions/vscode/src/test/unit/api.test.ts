import * as assert from 'assert';
import * as sinon from 'sinon';
import axios from 'axios';
import { GestVenvAPI } from '../../api/gestvenvClient';

suite('GestVenv API Tests', () => {
    let api: GestVenvAPI;
    let axiosStub: sinon.SinonStub;
    let mockClient: any;

    setup(() => {
        mockClient = {
            get: sinon.stub().resolves({ data: {} }),
            post: sinon.stub().resolves({ data: {} }),
            put: sinon.stub().resolves({ data: {} }),
            delete: sinon.stub().resolves({ data: {} }),
            interceptors: {
                response: {
                    use: sinon.stub()
                }
            }
        };
        
        axiosStub = sinon.stub(axios, 'create').returns(mockClient);
        api = new GestVenvAPI('http://localhost:8000');
    });

    teardown(() => {
        sinon.restore();
    });

    test('Should create API client with correct base URL', () => {
        assert.ok(axiosStub.calledOnce);
        const callArgs = axiosStub.getCall(0).args[0];
        assert.strictEqual(callArgs.baseURL, 'http://localhost:8000');
        assert.strictEqual(callArgs.timeout, 10000);
        assert.strictEqual(callArgs.headers['Content-Type'], 'application/json');
        assert.strictEqual(callArgs.headers['X-Client'], 'vscode-extension');
    });

    test('Should test connection successfully', async () => {
        mockClient.get.resolves({ data: { status: 'healthy' } });
        
        const result = await api.testConnection();
        assert.strictEqual(result, true);
        assert.ok(mockClient.get.calledWith('/health'));
    });

    test('Should return false when connection fails', async () => {
        mockClient.get.rejects(new Error('Connection failed'));
        
        const result = await api.testConnection();
        assert.strictEqual(result, false);
    });

    test('Should detect active environment', async () => {
        const mockEnv = {
            id: 'env-123',
            name: 'test-env',
            python_version: '3.11',
            is_active: true
        };
        
        mockClient.post.resolves({ data: mockEnv });
        
        const result = await api.detectActiveEnvironment('/workspace');
        assert.deepStrictEqual(result, mockEnv);
        assert.ok(mockClient.post.calledWith('/api/v1/environments/detect', {
            workspace_path: '/workspace'
        }));
    });

    test('Should get packages with caching', async () => {
        const mockPackages = [
            { name: 'requests', version: '2.31.0' },
            { name: 'numpy', version: '1.24.0' }
        ];
        
        mockClient.get.resolves({ data: mockPackages });
        
        // First call should hit the API
        const result1 = await api.getPackages('env-123');
        assert.deepStrictEqual(result1, mockPackages);
        assert.ok(mockClient.get.calledOnce);
        
        // Second call should use cache
        const result2 = await api.getPackages('env-123');
        assert.deepStrictEqual(result2, mockPackages);
        assert.ok(mockClient.get.calledOnce); // Still only called once
    });

    test('Should install package', async () => {
        const mockResult = {
            success: true,
            message: 'Package installed successfully'
        };
        
        mockClient.post.resolves({ data: mockResult });
        
        const result = await api.installPackage('env-123', 'requests', { version: '2.31.0' });
        assert.deepStrictEqual(result, mockResult);
        assert.ok(mockClient.post.calledWith('/api/v1/environments/env-123/packages/install', {
            package: 'requests',
            version: '2.31.0'
        }));
    });
});