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
