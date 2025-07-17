import * as assert from 'assert';
import { CompletionCache } from '../../cache/completionCache';
import * as vscode from 'vscode';

suite('Completion Cache Tests', () => {
    let cache: CompletionCache;

    setup(() => {
        cache = new CompletionCache();
    });

    test('Should store and retrieve items', () => {
        const items: vscode.CompletionItem[] = [
            new vscode.CompletionItem('requests', vscode.CompletionItemKind.Module),
            new vscode.CompletionItem('numpy', vscode.CompletionItemKind.Module)
        ];
        
        cache.set('test-key', items);
        const retrieved = cache.get<vscode.CompletionItem[]>('test-key');
        
        assert.strictEqual(retrieved?.length, 2);
        assert.strictEqual(retrieved?.[0].label, 'requests');
        assert.strictEqual(retrieved?.[1].label, 'numpy');
    });

    test('Should return null for non-existent key', () => {
        const result = cache.get('non-existent');
        assert.strictEqual(result, null);
    });

    test('Should respect TTL', (done) => {
        const items: vscode.CompletionItem[] = [
            new vscode.CompletionItem('test', vscode.CompletionItemKind.Module)
        ];
        
        // Create cache with 100ms TTL
        cache = new CompletionCache(100);
        cache.set('test-key', items);
        
        // Should exist immediately
        assert.notStrictEqual(cache.get('test-key'), null);
        
        // Should expire after TTL
        setTimeout(() => {
            assert.strictEqual(cache.get('test-key'), null);
            done();
        }, 150);
    });

    test('Should clear all items', () => {
        cache.set('key1', []);
        cache.set('key2', []);
        cache.set('key3', []);
        
        cache.clear();
        
        assert.strictEqual(cache.get('key1'), null);
        assert.strictEqual(cache.get('key2'), null);
        assert.strictEqual(cache.get('key3'), null);
    });

    test('Should delete specific key', () => {
        cache.set('key1', []);
        cache.set('key2', []);
        
        cache.delete('key1');
        
        assert.strictEqual(cache.get('key1'), null);
        assert.notStrictEqual(cache.get('key2'), null);
    });

    test('Should handle large cache correctly', () => {
        // Add items up to max size
        for (let i = 0; i < 100; i++) {
            cache.set(`key${i}`, []);
        }
        
        // Add one more item (should evict oldest)
        cache.set('key100', []);
        
        // Oldest item should be evicted
        assert.strictEqual(cache.get('key0'), null);
        // Newest item should exist
        assert.notStrictEqual(cache.get('key100'), null);
    });
});