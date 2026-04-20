# 简历解析功能设计

**日期:** 2026-03-31
**功能:** 简历上传与自动填充 Profile 表单

---

## 1. 功能概述

用户可以上传 PDF 或 Word 格式的简历，前端解析文件内容，提取关键信息（求职方向、关键词、公司/行业偏好、基本信息等）并自动填充到 Profile 表单的各个字段中。

---

## 2. 技术方案

### 2.1 文件解析库

| 文件格式 | 解析库 | 用途 |
|---------|--------|------|
| PDF (.pdf) | pdfjs-dist | 文字提取 |
| Word (.docx) | mammoth.js + docx-preview | 文字提取 + 预览 |

### 2.2 前端依赖

```json
{
  "pdfjs-dist": "^3.x",
  "mammoth": "^1.6.x",
  "docx-preview": "^0.1.x"
}
```

### 2.3 文件上传方式

- 使用 HTML5 File API (`<input type="file">`)
- 支持拖拽上传 (drag & drop)
- 仅接受 `.pdf` 和 `.docx` 文件

---

## 3. 交互流程

1. 用户进入 Profile 页面
2. 页面顶部显示简历上传区域（拖拽区 + 点击上传按钮）
3. 用户上传文件
4. 前端自动识别文件类型（PDF/DOCX）
5. 调用对应解析库提取文字内容
6. 解析成功 → 自动填充所有表单字段
7. 解析失败 → 显示友好错误提示，用户可重新上传或手动填写
8. 用户可修改任意字段或点击「清除」按钮重置单个区块
9. 用户点击「保存完整画像」提交

---

## 4. 表单区块与清除按钮

每个表单区块底部添加「清除」按钮：

| 表单区块 | 清除字段 |
|---------|---------|
| 求职方向 | direction |
| 可投职位关键词 | include_keywords |
| 加分关键词 | prefer_keywords |
| 排除职位关键词 | exclude_keywords |
| 公司边界 | prefer_companies, exclude_companies |
| 行业边界 | prefer_industries, exclude_industries |
| 模糊岗位二次打分 | fuzzy_keywords, scoring_threshold |
| 基本信息 | target_cities, exclude_areas, salary_min, salary_max, experience_min, experience_max |

---

## 5. 简历解析规则

### 5.1 关键词提取逻辑

从简历文本中识别并分类：

| 字段 | 提取规则 |
|------|---------|
| include_keywords | 职位相关词：品牌策划、市场营销、活动策划、内容策划、CPM、整合营销... |
| prefer_keywords | 高价值词：品牌升级、Campaign、用户洞察、全案、整合营销、战略... |
| exclude_keywords | 排除词：新媒体运营、直播运营、电商运营、销售、BD... |
| prefer_companies | 公司类型：广告公司、甲方品牌、互联网公司、咨询公司... |
| prefer_industries | 行业：互联网、快消品、新消费、文化创意... |

### 5.2 基本信息提取

| 字段 | 提取规则 |
|------|---------|
| target_cities | 简历中提及的工作地点 |
| salary_min | 如简历中有薪资期望，提取最低值 |
| experience_min | 从工作经历年限推算 |
| experience_max | 同上 |

### 5.3 求职方向判断

根据关键词判断：
- 含「设计」「视觉」「VI」「品牌表达」→ design
- 含「策划」「策略」「创意」「Campaign」→ planning
- 其他 → 保持当前值

---

## 6. 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| 文件格式不支持 | 显示提示："仅支持 PDF 和 Word (.docx) 文件" |
| 文件读取失败 | 显示提示："文件读取失败，请尝试重新上传" |
| 解析失败 | 显示提示："简历解析失败，请手动填写" |
| 文件过大 (>10MB) | 显示提示："文件过大，请上传小于 10MB 的文件" |

---

## 7. UI 布局

### 7.1 上传区域（Profile 页面顶部）

```
┌─────────────────────────────────────────────────────┐
│  📄 上传简历                                         │
│  ┌───────────────────────────────────────────────┐  │
│  │     拖拽简历到这里 或 点击上传                   │  │
│  │     支持 PDF、Word (.docx)                    │  │
│  │                                               │  │
│  │     [选择文件]                                 │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  ✅ 解析成功！已自动填充表单                          │
└─────────────────────────────────────────────────────┘
```

### 7.2 清除按钮位置

每个 `.form-card` 底部右侧添加：

```html
<div class="card-footer">
  <button class="clear-btn" @click="clearSection('direction')">清除</button>
</div>
```

---

## 8. 文件结构

```
frontend/
├── src/
│   ├── components/
│   │   └── ResumeUploader.vue    # 新增：简历上传组件
│   ├── utils/
│   │   ├── pdfParser.js          # 新增：PDF 解析工具
│   │   ├── docxParser.js         # 新增：Word 解析工具
│   │   └── resumeAnalyzer.js     # 新增：简历内容分析工具
│   └── views/
│       └── Profile.vue           # 修改：集成上传和清除功能
```

---

## 9. 实施步骤

1. 安装前端依赖
2. 创建 ResumeUploader.vue 组件
3. 创建 pdfParser.js 工具
4. 创建 docxParser.js 工具
5. 创建 resumeAnalyzer.js 分析工具
6. 修改 Profile.vue 添加上传区域
7. 为每个表单区块添加清除按钮
8. 测试完整流程
