/**
 * PDF Parser using pdfjs-dist
 * Extracts text content from PDF files, with OCR fallback for image-based PDFs
 */

import * as pdfjsLib from 'pdfjs-dist'
import { extractTextFromImage } from './ocrParser'

// Configure worker with proper path
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.js',
  import.meta.url
).href

/**
 * Extract text from a PDF File object
 * First tries native text extraction, then falls back to OCR for image-based PDFs
 * @param {File} file - PDF file
 * @param {Function} onProgress - Progress callback (optional)
 * @returns {Promise<string>} Extracted text
 */
export async function extractTextFromPdf(file, onProgress) {
  try {
    const arrayBuffer = await file.arrayBuffer()
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise

    let fullText = ''
    let hasText = false

    // First pass: try native text extraction
    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i)
      const textContent = await page.getTextContent()
      const pageText = textContent.items.map(item => item.str).join(' ').trim()

      if (pageText.length > 0) {
        hasText = true
        fullText += pageText + '\n'
      }
    }

    // If we got enough text, return it
    if (hasText && fullText.trim().length > 100) {
      return fullText.trim()
    }

    // Fallback: render pages to images and use OCR
    if (onProgress) onProgress({ status: 'recognizing', progress: 0 })

    const scale = 2.0 // Higher scale for better OCR
    let ocrText = ''

    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i)
      const viewport = page.getViewport({ scale })

      // Create canvas
      const canvas = document.createElement('canvas')
      const context = canvas.getContext('2d')
      canvas.height = viewport.height
      canvas.width = viewport.width

      // Render page to canvas
      await page.render({
        canvasContext: context,
        viewport: viewport
      }).promise

      // Convert canvas to blob and OCR
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'))
      const pageOcrText = await extractTextFromImage(blob)
      ocrText += pageOcrText + '\n'

      if (onProgress) {
        onProgress({ status: 'recognizing', progress: (i / pdf.numPages) * 100 })
      }
    }

    if (ocrText.trim().length > 0) {
      return ocrText.trim()
    }

    // Both methods failed
    throw new Error('无法从PDF中提取文字，请尝试上传Word格式简历')

  } catch (error) {
    console.error('PDF parsing error:', error)
    if (error.message.includes('无法从PDF')) {
      throw error
    }
    throw new Error('PDF解析失败，请确保文件是有效的PDF文档')
  }
}

/**
 * Check if file is a valid PDF
 * @param {File} file
 * @returns {boolean}
 */
export function isPdfFile(file) {
  return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
}
