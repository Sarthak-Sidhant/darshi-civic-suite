import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	build: {
		// Code splitting for better caching and initial load
		rollupOptions: {
			output: {
				manualChunks: (id) => {
					// Separate vendor libraries into their own chunks
					if (id.includes('node_modules')) {
						// Lucide icons in separate chunk
						if (id.includes('lucide-svelte')) {
							return 'lucide';
						}
						// Leaflet in separate chunk (lazy loaded)
						if (id.includes('leaflet')) {
							return 'leaflet';
						}
						// Other node_modules in vendor chunk
						return 'vendor';
					}
				}
			}
		},
		// Minify with terser for better compression
		minify: 'terser',
		terserOptions: {
			compress: {
				drop_console: true, // Remove console.logs in production
				drop_debugger: true,
				passes: 2, // Additional optimization pass
			},
			mangle: {
				safari10: true // Safari 10 compatibility
			}
		},
		// Target modern browsers for smaller bundles
		target: 'es2020',
		// Increase chunk size warning limit (split chunks are expected)
		chunkSizeWarningLimit: 1000,
		// Enable CSS code splitting
		cssCodeSplit: true
	}
});
