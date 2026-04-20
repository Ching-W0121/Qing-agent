<template>
  <div class="resume-uploader">
    <div class="upload-header">
      <h3>📄 上传简历</h3>
      <p class="helper-text">支持 PDF、Word (.docx) 文件，自动解析并填充表单</p>
    </div>

    <div
      class="drop-zone"
      :class="{ 'drag-over': isDragOver, 'has-file': selectedFile }"
      @dragover.prevent="isDragOver = true"
      @dragleave="isDragOver = false"
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        @change="handleFileSelect"
        style="display: none"
      />

      <div v-if="!selectedFile && !parsing" class="upload-placeholder">
        <span class="upload-icon">📎</span>
        <p>拖拽简历到这里 或 <span class="link">点击上传</span></p>
        <p class="file-types">支持 PDF、Word (.docx)</p>
      </div>

      <div v-if="selectedFile && !parsing" class="file-selected">
        <span class="file-icon">📄</span>
        <span class="file-name">{{ selectedFile.name }}</span>
        <button class="remove-btn" @click.stop="clearFile">×</button>
      </div>

      <div v-if="parsing" class="parsing">
        <span class="spinner">⏳</span>
        <p v-if="!isOcr">正在解析简历...</p>
        <p v-else>正在OCR识别图片中的文字... {{ Math.round(ocrProgress) }}%</p>
      </div>
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <div v-if="success" class="success-message">
      ✅ 解析成功！已自动填充表单，请检查并修改
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { extractTextFromPdf, isPdfFile } from '@/utils/pdfParser'
import { extractTextFromDocx, isDocxFile } from '@/utils/docxParser'
import { analyzeResume } from '@/utils/resumeAnalyzer'

const emit = defineEmits(['parsed'])

const fileInput = ref(null)
const isDragOver = ref(false)
const selectedFile = ref(null)
const parsing = ref(false)
const isOcr = ref(false)
const ocrProgress = ref(0)
const error = ref('')
const success = ref(false)

function triggerFileInput() {
  fileInput.value?.click()
}

function handleDrop(e) {
  isDragOver.value = false
  const files = e.dataTransfer.files
  if (files.length > 0) {
    processFile(files[0])
  }
}

function handleFileSelect(e) {
  const files = e.target.files
  if (files.length > 0) {
    processFile(files[0])
  }
}

async function processFile(file) {
  error.value = ''
  success.value = false
  isOcr.value = false
  ocrProgress.value = 0

  // Validate file type
  if (!isPdfFile(file) && !isDocxFile(file)) {
    error.value = '仅支持 PDF 和 Word (.docx) 文件'
    return
  }

  // Validate file size (10MB)
  if (file.size > 10 * 1024 * 1024) {
    error.value = '文件过大，请上传小于 10MB 的文件'
    return
  }

  selectedFile.value = file
  parsing.value = true

  try {
    let text = ''

    if (isPdfFile(file)) {
      // Pass progress callback for OCR fallback
      text = await extractTextFromPdf(file, (progress) => {
        if (progress.status === 'recognizing') {
          isOcr.value = true
          ocrProgress.value = progress.progress
        }
      })
    } else {
      text = await extractTextFromDocx(file)
    }

    if (!text || text.length < 50) {
      throw new Error('简历内容过少，无法解析')
    }

    const profileData = analyzeResume(text)
    success.value = true
    emit('parsed', profileData)

    // Clear success message after 5 seconds
    setTimeout(() => {
      success.value = false
    }, 5000)

  } catch (err) {
    error.value = err.message || '简历解析失败，请尝试重新上传'
    selectedFile.value = null
  } finally {
    parsing.value = false
    isOcr.value = false
    ocrProgress.value = 0
  }
}

function clearFile() {
  selectedFile.value = null
  error.value = ''
  success.value = false
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}
</script>

<style scoped>
.resume-uploader {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  margin-bottom: 20px;
}

.upload-header {
  margin-bottom: 16px;
}

.upload-header h3 {
  font-size: 18px;
  color: #333;
  margin-bottom: 4px;
}

.helper-text {
  font-size: 14px;
  color: #666;
}

.drop-zone {
  border: 2px dashed #ddd;
  border-radius: 12px;
  padding: 40px 24px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.drop-zone:hover,
.drop-zone.drag-over {
  border-color: #007bff;
  background: #f0f7ff;
}

.drop-zone.has-file {
  border-style: solid;
  border-color: #28a745;
  background: #f0fff4;
}

.upload-placeholder {
  color: #666;
}

.upload-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
}

.link {
  color: #007bff;
  text-decoration: underline;
}

.file-types {
  font-size: 12px;
  color: #999;
  margin-top: 8px;
}

.file-selected {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.file-icon {
  font-size: 32px;
}

.file-name {
  font-size: 16px;
  color: #333;
  font-weight: 500;
}

.remove-btn {
  background: #dc3545;
  color: white;
  border: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
}

.remove-btn:hover {
  background: #c82333;
}

.parsing {
  color: #666;
}

.spinner {
  font-size: 32px;
  display: block;
  margin-bottom: 8px;
}

.error-message {
  margin-top: 12px;
  padding: 12px;
  background: #ffebee;
  color: #c62828;
  border-radius: 8px;
  font-size: 14px;
}

.success-message {
  margin-top: 12px;
  padding: 12px;
  background: #e8f5e9;
  color: #2e7d32;
  border-radius: 8px;
  font-size: 14px;
}
</style>
