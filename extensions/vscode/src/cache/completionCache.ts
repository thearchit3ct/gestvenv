export interface CacheEntry<T> {
    value: T;
    timestamp: number;
    ttl: number;
}

export class CompletionCache {
    private cache: Map<string, CacheEntry<any>> = new Map();
    private defaultTTL = 300000; // 5 minutes
    private maxSize = 100;

    constructor(ttl?: number) {
        if (ttl !== undefined) {
            this.defaultTTL = ttl;
        }
    }

    get<T>(key: string): T | null {
        const entry = this.cache.get(key);
        if (!entry) {
            return null;
        }

        if (Date.now() - entry.timestamp > entry.ttl) {
            this.cache.delete(key);
            return null;
        }

        return entry.value;
    }

    set<T>(key: string, value: T, ttl?: number): void {
        // Check size limit
        if (this.cache.size >= this.maxSize && !this.cache.has(key)) {
            // Remove oldest entry
            const firstKey = this.cache.keys().next().value;
            if (firstKey) {
                this.cache.delete(firstKey);
            }
        }

        this.cache.set(key, {
            value,
            timestamp: Date.now(),
            ttl: ttl || this.defaultTTL
        });
    }

    has(key: string): boolean {
        const value = this.get(key);
        return value !== null;
    }

    delete(key: string): void {
        this.cache.delete(key);
    }

    clear(): void {
        this.cache.clear();
    }

    size(): number {
        return this.cache.size;
    }

    // Clean up expired entries
    cleanup(): void {
        const now = Date.now();
        for (const [key, entry] of this.cache.entries()) {
            if (now - entry.timestamp > entry.ttl) {
                this.cache.delete(key);
            }
        }
    }
}