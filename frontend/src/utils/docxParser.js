/**
 * DOCX Parser using mammoth.js
 * Extracts text content from Word documents
 */

import mammoth from 'mammoth'
import 'docx-preview'

/**
 * Extract text from a DOCX File object
 * @param {File} file - Word file
 * @returns {Promise<string>} Extracted text
 */
export async function extractTextFromDocx(file) {
  try {
    const arrayBuffer = await file.arrayBuffer()
    const result = await mammoth.extractRawText({ arrayBuffer })
    return result.value.trim()
  } catch (error) {
    console.error('DOCX parsing error:', error)
    throw new Error('Word文档解析失败，请确保文件是有效的 .docx 文档')
  }
}

/**
 * Check if file is a valid DOCX
 * @param {File} file
 * @returns {boolean}
 */
export function isDocxFile(file) {
  return (
    file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
    file.name.toLowerCase().endsWith('.docx')
  )
}
