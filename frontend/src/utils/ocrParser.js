/**
 * OCR Parser using Tesseract.js
 * Extracts text from images (for image-based PDFs or scanned documents)
 */

import Tesseract from 'tesseract.js'

/**
 * Extract text from an image File/Blob using OCR
 * @param {File|Blob} image - Image file
 * @param {Function} onProgress - Progress callback (optional)
 * @returns {Promise<string>} Extracted text
 */
export async function extractTextFromImage(image, onProgress) {
  try {
    const result = await Tesseract.recognize(image, 'eng+chi_sim', {
      logger: onProgress || (() => {})
    })
    return result.data.text.trim()
  } catch (error) {
    console.error('OCR error:', error)
    throw new Error('OCR识别失败，无法从图片中提取文字')
  }
}

/**
 * Check if Tesseract.js worker is ready
 * @returns {Promise<boolean>}
 */
export async function isOcrReady() {
  try {
    await Tesseract.recognize('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', 'eng', {
      logger: () => {}
    })
    return true
  } catch {
    return false
  }
}
