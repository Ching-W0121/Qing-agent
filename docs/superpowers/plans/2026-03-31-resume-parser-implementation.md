# Resume Parser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add PDF/Word resume upload and auto-fill functionality to Profile page

**Architecture:** Pure frontend parsing using pdfjs-dist (PDF) and mammoth.js (Word). No backend changes required. ResumeAnalyzer utility extracts structured data from raw text.

**Tech Stack:** Vue 3, pdfjs-dist, mammoth, docx-preview

---

## File Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── ResumeUploader.vue      # NEW: Drag-drop upload component
│   ├── utils/
│   │   ├── pdfParser.js             # NEW: PDF text extraction
│   │   ├── docxParser.js            # NEW: Word text extraction
│   │   └── resumeAnalyzer.js         # NEW: Resume content → profile fields
│   └── views/
│       └── Profile.vue               # MODIFY: Add uploader + clear buttons
└── package.json                      # MODIFY: Add dependencies
```

---

## Task 1: Install Dependencies

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Add dependencies to package.json**

```json
{
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0",
    "axios": "^1.6.0",
    "pdfjs-dist": "^3.11.174",
    "mammoth": "^1.6.0",
    "docx-preview": "^0.1.20"
  }
}
```

- [ ] **Step 2: Run npm install**

Run: `cd /c/Users/TR/qing-agent/frontend && npm install`

Expected: Successfully installed all packages

- [ ] **Step 3: Commit**

```bash
cd /c/Users/TR/qing-agent/frontend
git add package.json package-lock.json
git commit -m "feat(frontend): add resume parser dependencies"
```

---

## Task 2: Create PDF Parser Utility

**Files:**
- Create: `frontend/src/utils/pdfParser.js`

- [ ] **Step 1: Write pdfParser.js**

```javascript
/**
 * PDF Parser using pdfjs-dist
 * Extracts text content from PDF files
 */

import * as pdfjsLib from 'pdfjs-dist';

// Set worker source to avoid CORS issues
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString()

/**
 * Extract text from a PDF File object
 * @param {File} file - PDF file
 * @returns {Promise<string>} Extracted text
 */
export async function extractTextFromPdf(file) {
  try {
    const arrayBuffer = await file.arrayBuffer()
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise

    let fullText = ''

    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i)
      const textContent = await page.getTextContent()
      const pageText = textContent.items.map(item => item.str).join(' ')
      fullText += pageText + '\n'
    }

    return fullText.trim()
  } catch (error) {
    console.error('PDF parsing error:', error)
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
```

- [ ] **Step 2: Test basic import**

Run: `cd /c/Users/TR/qing-agent/frontend && node -e "import('./src/utils/pdfParser.js').then(m => console.log('OK')).catch(e => console.error(e))"`

Expected: No errors (will print worker URL warning, that's fine)

- [ ] **Step 3: Commit**

```bash
cd /c/Users/TR/qing-agent
git add frontend/src/utils/pdfParser.js
git commit -m "feat(frontend): add PDF parser utility using pdfjs-dist"
```

---

## Task 3: Create Word Parser Utility

**Files:**
- Create: `frontend/src/utils/docxParser.js`

- [ ] **Step 1: Write docxParser.js**

```javascript
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
```

- [ ] **Step 2: Test basic import**

Run: `cd /c/Users/TR/qing-agent/frontend && node -e "import('./src/utils/docxParser.js').then(m => console.log('OK')).catch(e => console.error(e))"`

Expected: No errors

- [ ] **Step 3: Commit**

```bash
cd /c/Users/TR/qing-agent
git add frontend/src/utils/docxParser.js
git commit -m "feat(frontend): add DOCX parser utility using mammoth"
```

---

## Task 4: Create Resume Analyzer Utility

**Files:**
- Create: `frontend/src/utils/resumeAnalyzer.js`

- [ ] **Step 1: Write resumeAnalyzer.js**

```javascript
/**
 * Resume Analyzer
 * Extracts structured profile data from raw resume text
 */

/**
 * Keyword categories for matching
 */
const KEYWORD_PATTERNS = {
  // Planning direction keywords
  planning_keywords: [
    '品牌策划', '市场策划', '营销策划', '活动策划', '内容策划',
    'Campaign', '整合营销', '全案', '策略', '创意策划', '品牌运营',
    '市场推广', '推广策划', '策划专员', '品牌经理', '市场经理'
  ],

  // Design direction keywords
  design_keywords: [
    '品牌设计', '视觉设计', 'VI设计', '品牌表达', '创意设计',
    '平面设计', 'UI设计', '图形设计', '插画', '设计专员'
  ],

  // Prefer keywords (high value)
  prefer_keywords: [
    '品牌升级', 'campaign', '用户洞察', '全案', '整合营销',
    '战略', '品牌战略', '整合传播', '创意策略', '品牌策略'
  ],

  // Exclude keywords (filter out)
  exclude_keywords: [
    '新媒体运营', '短视频运营', '直播运营', '电商运营', '电商运营',
    '销售', 'BD', '客户经理', '招商', '客服', '用户运营',
    '数据分析', '文案编辑', '内容编辑', '编辑', '媒介', '投放',
    'SEM', 'SEO', '信息流'
  ],

  // Company types
  prefer_companies: [
    '广告公司', '品牌咨询', '整合营销公司', '咨询公司',
    '甲方品牌', '品牌方', '互联网公司', '新消费品牌', '快消品'
  ],

  // Exclude companies
  exclude_companies: [
    '纯外包', '代运营', '外包公司', '传统制造', '制造业',
    '门店连锁', '经销商'
  ],

  // Industries
  prefer_industries: [
    '互联网', '新消费', '快消品', '内容平台', '文化创意',
    '电商', '在线教育', '医疗健康', '旅游', '游戏'
  ],

  exclude_industries: [
    '纯ToB', 'B端', '传统批发', '金融销售', '地产中介',
    '保险', '证券', '银行'
  ]
}

/**
 * Extract keywords from text that match a given list
 * @param {string} text - Resume text
 * @param {string[]} keywords - Keywords to search for
 * @returns {string[]} Matched keywords
 */
function extractMatchingKeywords(text, keywords) {
  const lowerText = text.toLowerCase()
  return keywords.filter(keyword => lowerText.includes(keyword.toLowerCase()))
}

/**
 * Analyze resume text and extract profile data
 * @param {string} text - Raw resume text
 * @returns {Object} Structured profile data
 */
export function analyzeResume(text) {
  const lowerText = text.toLowerCase()

  // Determine direction
  let direction = 'planning'
  const matchedDesignKeywords = extractMatchingKeywords(text, KEYWORD_PATTERNS.design_keywords)
  const matchedPlanningKeywords = extractMatchingKeywords(text, KEYWORD_PATTERNS.planning_keywords)

  if (matchedDesignKeywords.length > matchedPlanningKeywords.length) {
    direction = 'design'
  }

  // Extract all keywords
  const include_keywords = [...new Set(extractMatchingKeywords(text, KEYWORD_PATTERNS.planning_keywords))]
  const prefer_keywords = [...new Set(extractMatchingKeywords(text, KEYWORD_PATTERNS.prefer_keywords))]
  const exclude_keywords = [...new Set(extractMatchingKeywords(text, KEYWORD_PATTERNS.exclude_keywords))]
  const prefer_companies = [...new Set(extractMatchingKeywords(text, KEYWORD_PATTERNS.prefer_companies))]
  const exclude_companies = [...new Set(extractMatchingKeywords(text, KEYWORD_PATTERNS.exclude_companies))]
  const prefer_industries = [...new Set(extractMatchingKeywords(text, KEYWORD_PATTERNS.prefer_industries))]
  const exclude_industries = [...new Set(extractMatchingKeywords(text, KEYWORD_PATTERNS.exclude_industries))]

  // Extract cities (simple pattern matching)
  const cities = extractCities(text)

  // Extract experience (look for year patterns)
  const experience = extractExperience(text)

  return {
    direction,
    include_keywords: include_keywords.length > 0 ? include_keywords : null,
    prefer_keywords: prefer_keywords.length > 0 ? prefer_keywords : null,
    exclude_keywords: exclude_keywords.length > 0 ? exclude_keywords : null,
    prefer_companies: prefer_companies.length > 0 ? prefer_companies : null,
    exclude_companies: exclude_companies.length > 0 ? exclude_companies : null,
    prefer_industries: prefer_industries.length > 0 ? prefer_industries : null,
    exclude_industries: exclude_industries.length > 0 ? exclude_industries : null,
    target_cities: cities.length > 0 ? cities : null,
    experience_min: experience.min,
    experience_max: experience.max
  }
}

/**
 * Extract city names from text
 * @param {string} text
 * @returns {string[]}
 */
function extractCities(text) {
  const commonCities = [
    '北京', '上海', '广州', '深圳', '杭州', '南京', '苏州', '成都',
    '武汉', '西安', '重庆', '天津', '长沙', '郑州', '东莞', '佛山'
  ]

  const found = commonCities.filter(city => text.includes(city))
  return [...new Set(found)]
}

/**
 * Extract experience years from text
 * @param {string} text
 * @returns {{min: number, max: number}}
 */
function extractExperience(text) {
  // Match patterns like "3年经验", "3-5年", "三年以上"
  const patterns = [
    /(\d+)\s*~?\s*(\d+)\s*年/g,           // 3-5年 or 3~5年
    /(\d+)\s*年\s*经验/g,                  // 3年经验
    /(\d+)\s*年以上/g,                     // 3年以上
    /(\d+)\s*年\s*以上?\s*经验/g           // 3年经验 or 3年以上经验
  ]

  let minYears = 1
  let maxYears = 5

  for (const pattern of patterns) {
    const matches = [...text.matchAll(pattern)]
    for (const match of matches) {
      if (match[1] && match[2]) {
        const y1 = parseInt(match[1])
        const y2 = parseInt(match[2])
        if (y1 >= 0 && y1 <= 20) minYears = Math.min(minYears, y1)
        if (y2 >= 0 && y2 <= 20) maxYears = Math.min(maxYears, y2)
      } else if (match[1]) {
        const y = parseInt(match[1])
        if (y >= 0 && y <= 20) minYears = Math.min(minYears, y)
      }
    }
  }

  return { min: minYears, max: maxYears }
}
```

- [ ] **Step 2: Test the analyzer**

Run: `cd /c/Users/TR/qing-agent/frontend && node -e "
import('./src/utils/resumeAnalyzer.js').then(m => {
  const result = m.analyzeResume('3年品牌策划经验，负责品牌升级和整合营销项目')
  console.log(JSON.stringify(result, null, 2))
})"`

Expected: Should return structured object with direction, keywords, etc.

- [ ] **Step 3: Commit**

```bash
cd /c/Users/TR/qing-agent
git add frontend/src/utils/resumeAnalyzer.js
git commit -m "feat(frontend): add resume analyzer utility"
```

---

## Task 5: Create ResumeUploader Component

**Files:**
- Create: `frontend/src/components/ResumeUploader.vue`

- [ ] **Step 1: Write ResumeUploader.vue**

```vue
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
        <p>正在解析简历...</p>
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
      text = await extractTextFromPdf(file)
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
```

- [ ] **Step 2: Verify component file exists**

Run: `ls -la /c/Users/TR/qing-agent/frontend/src/components/ResumeUploader.vue`

Expected: File exists

- [ ] **Step 3: Commit**

```bash
cd /c/Users/TR/qing-agent
git add frontend/src/components/ResumeUploader.vue
git commit -m "feat(frontend): add ResumeUploader component with drag-drop support"
```

---

## Task 6: Modify Profile.vue

**Files:**
- Modify: `frontend/src/views/Profile.vue`

**Changes needed:**
1. Import and add ResumeUploader component at top of form
2. Add `@parsed` handler to receive parsed data
3. Add `applyParsedData` method to fill form
4. Add `clearSection` method for each section
5. Add "清除" button to each `.form-card`

- [ ] **Step 1: Add imports (after existing imports)**

```javascript
import ResumeUploader from '@/components/ResumeUploader.vue'
```

Add to components array: `ResumeUploader`

- [ ] **Step 2: Add parsed data handler in script**

```javascript
// Handle resume parsed data
const applyParsedData = (data) => {
  if (!data) return

  if (data.direction) {
    profile.value.direction = data.direction
  }

  if (data.include_keywords) {
    profile.value.include_keywords = [...new Set([
      ...profile.value.include_keywords,
      ...data.include_keywords
    ])]
  }

  if (data.prefer_keywords) {
    profile.value.prefer_keywords = [...new Set([
      ...profile.value.prefer_keywords,
      ...data.prefer_keywords
    ])]
  }

  if (data.exclude_keywords) {
    profile.value.exclude_keywords = [...new Set([
      ...profile.value.exclude_keywords,
      ...data.exclude_keywords
    ])]
  }

  if (data.prefer_companies) {
    profile.value.prefer_companies = [...new Set([
      ...profile.value.prefer_companies,
      ...data.prefer_companies
    ])]
  }

  if (data.exclude_companies) {
    profile.value.exclude_companies = [...new Set([
      ...profile.value.exclude_companies,
      ...data.exclude_companies
    ])]
  }

  if (data.prefer_industries) {
    profile.value.prefer_industries = [...new Set([
      ...profile.value.prefer_industries,
      ...data.prefer_industries
    ])]
  }

  if (data.exclude_industries) {
    profile.value.exclude_industries = [...new Set([
      ...profile.value.exclude_industries,
      ...data.exclude_industries
    ])]
  }

  if (data.target_cities) {
    profile.value.target_cities = data.target_cities.join(',')
  }

  if (data.experience_min !== undefined) {
    profile.value.experience_min = data.experience_min
  }

  if (data.experience_max !== undefined) {
    profile.value.experience_max = data.experience_max
  }
}
```

- [ ] **Step 3: Add clearSection function**

```javascript
// Clear section data
const clearSection = (section) => {
  switch (section) {
    case 'direction':
      profile.value.direction = 'planning'
      break
    case 'include':
      profile.value.include_keywords = []
      break
    case 'prefer':
      profile.value.prefer_keywords = []
      break
    case 'exclude':
      profile.value.exclude_keywords = []
      break
    case 'companies':
      profile.value.prefer_companies = []
      profile.value.exclude_companies = []
      break
    case 'industries':
      profile.value.prefer_industries = []
      profile.value.exclude_industries = []
      break
    case 'fuzzy':
      profile.value.fuzzy_keywords = []
      profile.value.scoring_threshold = 0.5
      break
    case 'basic':
      profile.value.target_cities = ''
      profile.value.exclude_areas = ''
      profile.value.salary_min = 6000
      profile.value.salary_max = 15000
      profile.value.experience_min = 1
      profile.value.experience_max = 5
      break
  }
}
```

- [ ] **Step 4: Add ResumeUploader to template (after page-header, before profile-form)**

```vue
      <section class="profile-form">
        <ResumeUploader @parsed="applyParsedData" />
```

- [ ] **Step 5: Add clear button to each form-card**

Add this div at the END of each `.form-card` div (before closing `</div>`):

```vue
        <div class="card-footer">
          <button class="clear-btn" @click="clearSection('direction')">清除</button>
        </div>
```

Section mappings:
- 求职方向 card → `clearSection('direction')`
- 可投职位关键词 card → `clearSection('include')`
- 加分关键词 card → `clearSection('prefer')`
- 排除职位关键词 card → `clearSection('exclude')`
- 公司边界 card → `clearSection('companies')`
- 行业边界 card → `clearSection('industries')`
- 模糊岗位二次打分 card → `clearSection('fuzzy')`
- 基本信息 card → `clearSection('basic')`

- [ ] **Step 6: Add clear button styles**

Add before `.save-btn` style:

```css
.card-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #eee;
}

.clear-btn {
  padding: 8px 16px;
  background: #f5f5f5;
  color: #666;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

.clear-btn:hover {
  background: #eee;
  color: #333;
}
```

- [ ] **Step 7: Verify syntax**

Run: `cd /c/Users/TR/qing-agent/frontend && npm run build 2>&1 | head -50`

Expected: No errors (warnings OK)

- [ ] **Step 8: Commit**

```bash
cd /c/Users/TR/qing-agent
git add frontend/src/views/Profile.vue
git commit -m "feat(frontend): integrate resume uploader and clear buttons in Profile"
```

---

## Task 7: Integration Test

**Files:**
- Test: Manual browser testing

- [ ] **Step 1: Start frontend dev server**

Run: `cd /c/Users/TR/qing-agent/frontend && npm run dev`

- [ ] **Step 2: Test upload flow in browser**

1. Open http://localhost:5173
2. Navigate to Profile page
3. Verify ResumeUploader appears at top
4. Try uploading a PDF or DOCX file
5. Verify form fields are populated
6. Click "Clear" buttons to verify they work

---

## Verification Checklist

- [ ] Upload component renders at top of Profile page
- [ ] Drag and drop works
- [ ] File select works
- [ ] PDF parsing extracts text
- [ ] DOCX parsing extracts text
- [ ] Parsed data fills all relevant form fields
- [ ] Each "Clear" button resets its section
- [ ] Error messages show for invalid files
- [ ] Build succeeds without errors
