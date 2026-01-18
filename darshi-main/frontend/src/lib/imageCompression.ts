/**
 * Lightweight client-side image resizing for faster uploads
 * Strategy: Only resize if needed (max 1920px), keep original quality
 * Server handles heavy optimization (WebP/JPEG conversion) in background
 */

/**
 * Resize image if dimensions exceed max size
 * Uses canvas API - fast and reliable across all browsers
 */
export async function resizeImage(file: File, maxDimension: number = 1920): Promise<File> {
	return new Promise((resolve, reject) => {
		// Only process images
		if (!file.type.startsWith('image/')) {
			resolve(file);
			return;
		}

		const reader = new FileReader();
		reader.onerror = () => reject(new Error('Failed to read file'));

		reader.onload = (e) => {
			const img = new Image();
			img.onerror = () => reject(new Error('Failed to load image'));

			img.onload = () => {
				const { width, height } = img;

				// Check if resize needed
				if (width <= maxDimension && height <= maxDimension) {
					// No resize needed - return original file
					resolve(file);
					return;
				}

				// Calculate new dimensions (maintain aspect ratio)
				let newWidth = width;
				let newHeight = height;

				if (width > height) {
					if (width > maxDimension) {
						newWidth = maxDimension;
						newHeight = (height * maxDimension) / width;
					}
				} else {
					if (height > maxDimension) {
						newHeight = maxDimension;
						newWidth = (width * maxDimension) / height;
					}
				}

				// Create canvas and resize
				const canvas = document.createElement('canvas');
				canvas.width = newWidth;
				canvas.height = newHeight;

				const ctx = canvas.getContext('2d');
				if (!ctx) {
					reject(new Error('Failed to get canvas context'));
					return;
				}

				// Draw resized image (high quality)
				ctx.imageSmoothingEnabled = true;
				ctx.imageSmoothingQuality = 'high';
				ctx.drawImage(img, 0, 0, newWidth, newHeight);

				// Convert to blob (keep original format, 95% quality)
				canvas.toBlob(
					(blob) => {
						if (!blob) {
							reject(new Error('Failed to create blob'));
							return;
						}

						// Create new file with same name and type
						const resizedFile = new File([blob], file.name, {
							type: file.type,
							lastModified: Date.now(),
						});

						const originalMB = (file.size / 1024 / 1024).toFixed(2);
						const resizedMB = (resizedFile.size / 1024 / 1024).toFixed(2);
						const saved = ((1 - resizedFile.size / file.size) * 100).toFixed(0);

						console.log(
							`[Resize] ${file.name}: ${width}x${height} (${originalMB}MB) → ` +
							`${Math.round(newWidth)}x${Math.round(newHeight)} (${resizedMB}MB) - ${saved}% smaller`
						);

						resolve(resizedFile);
					},
					file.type,
					0.95 // High quality
				);
			};

			img.src = e.target?.result as string;
		};

		reader.readAsDataURL(file);
	});
}

/**
 * Resize multiple images in parallel
 */
export async function resizeImages(files: File[]): Promise<File[]> {
	try {
		const resizePromises = files.map(file => resizeImage(file));
		return await Promise.all(resizePromises);
	} catch (error) {
		console.error('[Resize] Batch resize failed:', error);
		// Return originals on error
		return files;
	}
}
