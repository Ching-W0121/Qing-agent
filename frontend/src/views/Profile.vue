<template>
  <div class="profile-page">
    <Navbar />

    <main class="content">
      <header class="page-header">
        <h2>求职画像</h2>
        <p>精准投递，而非乱投</p>
      </header>

      <section class="profile-form">
        <ResumeUploader @parsed="applyParsedData" />

        <!-- 求职方向 -->
        <div class="form-card">
          <h3>求职方向</h3>
          <p class="helper-text">选择你的求职方向（可多选）</p>

          <div class="direction-selector">
            <label class="direction-option" :class="{ active: profile.directions.includes('planning') }">
              <input type="checkbox" v-model="profile.directions" value="planning" />
              <span class="direction-title">品牌策划</span>
              <span class="direction-desc">策略、创意、Campaign、全案</span>
            </label>
            <label class="direction-option" :class="{ active: profile.directions.includes('design') }">
              <input type="checkbox" v-model="profile.directions" value="design" />
              <span class="direction-title">品牌设计</span>
              <span class="direction-desc">VI、视觉、品牌表达、创意</span>
            </label>
          </div>

          <!-- 投递设置 - 每个方向独立设置 -->
          <div class="apply-limits-section" v-if="profile.directions.length > 0">
            <h4>投递数量设置</h4>
            <p class="helper-text">为每个求职方向设置每日投递上限</p>

            <div class="direction-apply-limits">
              <div class="direction-limit-item" v-if="profile.directions.includes('planning')">
                <label>品牌策划 每日上限</label>
                <input v-model.number="profile.planning_daily_limit" type="number" min="1" max="100" placeholder="10" />
              </div>
              <div class="direction-limit-item" v-if="profile.directions.includes('design')">
                <label>品牌设计 每日上限</label>
                <input v-model.number="profile.design_daily_limit" type="number" min="1" max="100" placeholder="10" />
              </div>
            </div>

            <div class="total-limit" v-if="profile.directions.length > 1">
              <label>总计每日上限</label>
              <input v-model.number="profile.total_daily_limit" type="number" min="1" max="200" placeholder="20" />
              <span class="helper-text">两个方向合计投递的最大职位数量</span>
            </div>
          </div>

          <div class="card-footer">
            <button class="clear-btn" @click="clearSection('direction')">清除</button>
          </div>
        </div>

        <!-- 可投职位 -->
        <div class="form-card">
          <h3>可投职位关键词</h3>
          <p class="helper-text">包含这些关键词的职位优先投递</p>

          <div class="keyword-section">
            <label class="section-label">包含关键词 (include)</label>
            <div class="keyword-tags">
              <span
                v-for="(tag, index) in profile.include_keywords"
                :key="index"
                class="keyword-tag include"
              >
                {{ tag }}
                <button @click="removeIncludeKeyword(index)" class="remove-btn">x</button>
              </span>
            </div>
            <div class="keyword-input-row">
              <input
                v-model="newIncludeKeyword"
                type="text"
                placeholder="输入关键词后按回车添加"
                @keyup.enter="addIncludeKeyword"
              />
              <button @click="addIncludeKeyword" class="add-btn">+ 添加</button>
            </div>
          </div>

          <div class="keyword-section">
            <label class="section-label">加分关键词（优先投递）</label>
            <div class="keyword-tags">
              <span
                v-for="(tag, index) in profile.prefer_keywords"
                :key="index"
                class="keyword-tag prefer"
              >
                {{ tag }}
                <button @click="removePreferKeyword(index)" class="remove-btn">x</button>
              </span>
            </div>
            <div class="keyword-input-row">
              <input
                v-model="newPreferKeyword"
                type="text"
                placeholder="品牌升级/campaign/用户洞察/创意/全案"
                @keyup.enter="addPreferKeyword"
              />
              <button @click="addPreferKeyword" class="add-btn">+ 添加</button>
            </div>
          </div>

          <div class="card-footer">
            <button class="clear-btn" @click="clearSection('include')">清除可投</button>
            <button class="clear-btn" @click="clearSection('prefer')">清除加分</button>
          </div>
        </div>

        <!-- 排除职位 -->
        <div class="form-card exclude-card">
          <h3>排除职位关键词</h3>
          <p class="helper-text">包含这些关键词的职位直接过滤掉</p>

          <div class="keyword-section">
            <label class="section-label">排除关键词 (exclude)</label>
            <div class="keyword-tags">
              <span
                v-for="(tag, index) in profile.exclude_keywords"
                :key="index"
                class="keyword-tag exclude"
              >
                {{ tag }}
                <button @click="removeExcludeKeyword(index)" class="remove-btn">x</button>
              </span>
            </div>
            <div class="keyword-input-row">
              <input
                v-model="newExcludeKeyword"
                type="text"
                placeholder="新媒体运营/直播运营/销售/电商运营..."
                @keyup.enter="addExcludeKeyword"
              />
              <button @click="addExcludeKeyword" class="add-btn danger">+ 添加</button>
            </div>
          </div>

          <div class="exclude-rule">
            <p class="rule-title">核心排除逻辑：</p>
            <p class="rule-text">不参与"策略制定"的岗位，一律降权或剔除</p>
          </div>

          <div class="card-footer">
            <button class="clear-btn" @click="clearSection('exclude')">清除</button>
          </div>
        </div>

        <!-- 公司边界 -->
        <div class="form-card">
          <h3>公司边界</h3>

          <div class="company-section">
            <div class="company-type priority">
              <label class="type-label">✅ 优先公司类型</label>
              <div class="keyword-tags">
                <span
                  v-for="(tag, index) in profile.prefer_companies"
                  :key="index"
                  class="keyword-tag company-priority"
                >
                  {{ tag }}
                  <button @click="removePreferCompany(index)" class="remove-btn">x</button>
                </span>
              </div>
              <div class="keyword-input-row">
                <input
                  v-model="newPreferCompany"
                  type="text"
                  placeholder="广告公司/品牌咨询/新消费品牌..."
                  @keyup.enter="addPreferCompany"
                />
                <button @click="addPreferCompany" class="add-btn">+ 添加</button>
              </div>
            </div>

            <div class="company-type exclude">
              <label class="type-label">❌ 排除公司类型</label>
              <div class="keyword-tags">
                <span
                  v-for="(tag, index) in profile.exclude_companies"
                  :key="index"
                  class="keyword-tag company-exclude"
                >
                  {{ tag }}
                  <button @click="removeExcludeCompany(index)" class="remove-btn">x</button>
                </span>
              </div>
              <div class="keyword-input-row">
                <input
                  v-model="newExcludeCompany"
                  type="text"
                  placeholder="纯外包/代运营/传统制造业..."
                  @keyup.enter="addExcludeCompany"
                />
                <button @click="addExcludeCompany" class="add-btn danger">+ 添加</button>
              </div>
            </div>
          </div>

          <div class="card-footer">
            <button class="clear-btn" @click="clearSection('companies')">清除</button>
          </div>
        </div>

        <!-- 行业边界 -->
        <div class="form-card">
          <h3>行业边界</h3>

          <div class="company-section">
            <div class="company-type priority">
              <label class="type-label">✅ 优先行业</label>
              <div class="keyword-tags">
                <span
                  v-for="(tag, index) in profile.prefer_industries"
                  :key="index"
                  class="keyword-tag company-priority"
                >
                  {{ tag }}
                  <button @click="removePreferIndustry(index)" class="remove-btn">x</button>
                </span>
              </div>
              <div class="keyword-input-row">
                <input
                  v-model="newPreferIndustry"
                  type="text"
                  placeholder="新消费/互联网产品/快消品..."
                  @keyup.enter="addPreferIndustry"
                />
                <button @click="addPreferIndustry" class="add-btn">+ 添加</button>
              </div>
            </div>

            <div class="company-type exclude">
              <label class="type-label">❌ 排除行业</label>
              <div class="keyword-tags">
                <span
                  v-for="(tag, index) in profile.exclude_industries"
                  :key="index"
                  class="keyword-tag company-exclude"
                >
                  {{ tag }}
                  <button @click="removeExcludeIndustry(index)" class="remove-btn">x</button>
                </span>
              </div>
              <div class="keyword-input-row">
                <input
                  v-model="newExcludeIndustry"
                  type="text"
                  placeholder="纯ToB制造/传统批发/金融销售..."
                  @keyup.enter="addExcludeIndustry"
                />
                <button @click="addExcludeIndustry" class="add-btn danger">+ 添加</button>
              </div>
            </div>
          </div>

          <div class="card-footer">
            <button class="clear-btn" @click="clearSection('industries')">清除</button>
          </div>
        </div>

        <!-- 模糊岗位二次打分 -->
        <div class="form-card scoring-card">
          <h3>模糊岗位二次打分</h3>
          <p class="helper-text">这些岗位不能直接过滤，需要 Agent 分析打分</p>

          <div class="scoring-rules">
            <div class="rule-item">
              <span class="rule-name">涉及品牌 (Brand)</span>
              <span class="rule-score">+0.4</span>
            </div>
            <div class="rule-item">
              <span class="rule-name">涉及策略 (Strategy)</span>
              <span class="rule-score">+0.3</span>
            </div>
            <div class="rule-item">
              <span class="rule-name">涉及创意 (Creative)</span>
              <span class="rule-score">+0.2</span>
            </div>
            <div class="rule-item negative">
              <span class="rule-name">仅执行 (Execution)</span>
              <span class="rule-score">-0.5</span>
            </div>
          </div>

          <div class="scoring-threshold">
            <span>最终规则：score ≥</span>
            <input v-model.number="profile.scoring_threshold" type="number" step="0.1" min="0" max="1" />
            <span>→ 保留 | 否则排除</span>
          </div>

          <div class="fuzzy-keywords">
            <label class="section-label">需要二次打分的模糊岗位</label>
            <div class="keyword-tags">
              <span
                v-for="(tag, index) in profile.fuzzy_keywords"
                :key="index"
                class="keyword-tag fuzzy"
              >
                {{ tag }}
                <button @click="removeFuzzyKeyword(index)" class="remove-btn">x</button>
              </span>
            </div>
            <div class="keyword-input-row">
              <input
                v-model="newFuzzyKeyword"
                type="text"
                placeholder="品牌运营/内容策划/市场专员..."
                @keyup.enter="addFuzzyKeyword"
              />
              <button @click="addFuzzyKeyword" class="add-btn">+ 添加</button>
            </div>
          </div>

          <div class="card-footer">
            <button class="clear-btn" @click="clearSection('fuzzy')">清除</button>
          </div>
        </div>

        <!-- 基本信息 -->
        <div class="form-card">
          <h3>基本信息</h3>

          <div class="form-row">
            <div class="form-group">
              <label>目标城市</label>
              <input v-model="profile.target_cities" type="text" placeholder="深圳" />
            </div>
            <div class="form-group">
              <label>排除区域</label>
              <input v-model="profile.exclude_areas" type="text" placeholder="宝安区 (逗号分隔)" />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>薪资下限 (元)</label>
              <input v-model.number="profile.salary_min" type="number" />
            </div>
            <div class="form-group">
              <label>薪资上限 (元)</label>
              <input v-model.number="profile.salary_max" type="number" />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>经验下限 (年)</label>
              <input v-model.number="profile.experience_min" type="number" />
            </div>
            <div class="form-group">
              <label>经验上限 (年)</label>
              <input v-model.number="profile.experience_max" type="number" />
            </div>
          </div>

          <div class="card-footer">
            <button class="clear-btn" @click="clearSection('basic')">清除</button>
          </div>
        </div>

        <button class="save-btn" @click="saveProfile">保存完整画像</button>

      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Navbar from '@/components/Navbar.vue'
import ResumeUploader from '@/components/ResumeUploader.vue'
import api from '@/api'

const router = useRouter()

// 求职方向
const profile = ref({
  directions: ['planning'], // 支持多选: 'planning', 'design'

  // 每个方向的投递上限
  planning_daily_limit: 10,
  design_daily_limit: 10,
  total_daily_limit: 20,

  // 关键词
  include_keywords: ['品牌策划', '品牌专员', '市场策划', '营销策划', '活动策划', '内容策划', 'Campaign策划', '品牌运营'],
  prefer_keywords: ['品牌升级', 'campaign', '用户洞察', '创意', '全案', '整合营销', '战略'],
  exclude_keywords: ['新媒体运营', '短视频运营', '直播运营', '电商运营', '销售', 'BD', '客户经理', '招商', '客服', '用户运营', '数据分析', '文案编辑'],

  // 公司边界
  prefer_companies: ['广告公司', '品牌咨询公司', '整合营销公司', '新消费品牌', '互联网品牌部'],
  exclude_companies: ['纯外包公司', '代运营公司', '传统制造业', '门店连锁'],

  // 行业边界
  prefer_industries: ['新消费', '互联网产品', '快消品', '内容平台', '文化创意'],
  exclude_industries: ['纯ToB制造', '传统批发零售', '金融销售', '地产中介'],

  // 模糊岗位二次打分
  fuzzy_keywords: ['品牌运营', '内容策划', '市场专员', '活动策划'],
  scoring_threshold: 0.5,

  // 基本信息
  target_cities: '深圳',
  exclude_areas: '宝安区',
  salary_min: 6000,
  salary_max: 15000,
  experience_min: 1,
  experience_max: 5
})

// 输入框绑定
const newIncludeKeyword = ref('')
const newPreferKeyword = ref('')
const newExcludeKeyword = ref('')
const newPreferCompany = ref('')
const newExcludeCompany = ref('')
const newPreferIndustry = ref('')
const newExcludeIndustry = ref('')
const newFuzzyKeyword = ref('')

// 添加关键词方法
const addIncludeKeyword = () => {
  if (newIncludeKeyword.value.trim() && !profile.value.include_keywords.includes(newIncludeKeyword.value.trim())) {
    profile.value.include_keywords.push(newIncludeKeyword.value.trim())
    newIncludeKeyword.value = ''
  }
}
const removeIncludeKeyword = (index) => profile.value.include_keywords.splice(index, 1)

const addPreferKeyword = () => {
  if (newPreferKeyword.value.trim() && !profile.value.prefer_keywords.includes(newPreferKeyword.value.trim())) {
    profile.value.prefer_keywords.push(newPreferKeyword.value.trim())
    newPreferKeyword.value = ''
  }
}
const removePreferKeyword = (index) => profile.value.prefer_keywords.splice(index, 1)

const addExcludeKeyword = () => {
  if (newExcludeKeyword.value.trim() && !profile.value.exclude_keywords.includes(newExcludeKeyword.value.trim())) {
    profile.value.exclude_keywords.push(newExcludeKeyword.value.trim())
    newExcludeKeyword.value = ''
  }
}
const removeExcludeKeyword = (index) => profile.value.exclude_keywords.splice(index, 1)

const addPreferCompany = () => {
  if (newPreferCompany.value.trim() && !profile.value.prefer_companies.includes(newPreferCompany.value.trim())) {
    profile.value.prefer_companies.push(newPreferCompany.value.trim())
    newPreferCompany.value = ''
  }
}
const removePreferCompany = (index) => profile.value.prefer_companies.splice(index, 1)

const addExcludeCompany = () => {
  if (newExcludeCompany.value.trim() && !profile.value.exclude_companies.includes(newExcludeCompany.value.trim())) {
    profile.value.exclude_companies.push(newExcludeCompany.value.trim())
    newExcludeCompany.value = ''
  }
}
const removeExcludeCompany = (index) => profile.value.exclude_companies.splice(index, 1)

const addPreferIndustry = () => {
  if (newPreferIndustry.value.trim() && !profile.value.prefer_industries.includes(newPreferIndustry.value.trim())) {
    profile.value.prefer_industries.push(newPreferIndustry.value.trim())
    newPreferIndustry.value = ''
  }
}
const removePreferIndustry = (index) => profile.value.prefer_industries.splice(index, 1)

const addExcludeIndustry = () => {
  if (newExcludeIndustry.value.trim() && !profile.value.exclude_industries.includes(newExcludeIndustry.value.trim())) {
    profile.value.exclude_industries.push(newExcludeIndustry.value.trim())
    newExcludeIndustry.value = ''
  }
}
const removeExcludeIndustry = (index) => profile.value.exclude_industries.splice(index, 1)

const addFuzzyKeyword = () => {
  if (newFuzzyKeyword.value.trim() && !profile.value.fuzzy_keywords.includes(newFuzzyKeyword.value.trim())) {
    profile.value.fuzzy_keywords.push(newFuzzyKeyword.value.trim())
    newFuzzyKeyword.value = ''
  }
}
const removeFuzzyKeyword = (index) => profile.value.fuzzy_keywords.splice(index, 1)

// Handle resume parsed data
const applyParsedData = (data) => {
  if (!data) return

  if (data.direction) {
    // 支持单个方向或多个方向
    if (Array.isArray(data.direction)) {
      profile.value.directions = data.direction
    } else {
      profile.value.directions = [data.direction]
    }
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

// Clear section data
const clearSection = (section) => {
  switch (section) {
    case 'direction':
      profile.value.directions = []
      profile.value.planning_daily_limit = 10
      profile.value.design_daily_limit = 10
      profile.value.total_daily_limit = 20
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

onMounted(async () => {
  const token = localStorage.getItem('token')
  if (!token) {
    router.push('/login')
    return
  }
  // 获取现有画像数据
  await fetchProfile()
})

const fetchProfile = async () => {
  try {
    const userId = localStorage.getItem('user_id') || 1
    const userRes = await api.get(`/api/users/${userId}`)
    if (userRes?.profile) {
      const p = userRes.profile
      if (p.directions) profile.value.directions = p.directions
      if (p.planning_daily_limit) profile.value.planning_daily_limit = p.planning_daily_limit
      if (p.design_daily_limit) profile.value.design_daily_limit = p.design_daily_limit
      if (p.total_daily_limit) profile.value.total_daily_limit = p.total_daily_limit
      if (p.include_keywords) profile.value.include_keywords = p.include_keywords
      if (p.prefer_keywords) profile.value.prefer_keywords = p.prefer_keywords
      if (p.exclude_keywords) profile.value.exclude_keywords = p.exclude_keywords
      if (p.prefer_companies) profile.value.prefer_companies = p.prefer_companies
      if (p.exclude_companies) profile.value.exclude_companies = p.exclude_companies
      if (p.prefer_industries) profile.value.prefer_industries = p.prefer_industries
      if (p.exclude_industries) profile.value.exclude_industries = p.exclude_industries
      if (p.fuzzy_keywords) profile.value.fuzzy_keywords = p.fuzzy_keywords
      if (p.scoring_threshold) profile.value.scoring_threshold = p.scoring_threshold
      if (p.target_cities) profile.value.target_cities = Array.isArray(p.target_cities) ? p.target_cities.join(',') : p.target_cities
      if (p.exclude_areas) profile.value.exclude_areas = Array.isArray(p.exclude_areas) ? p.exclude_areas.join(',') : p.exclude_areas
      if (p.salary_min) profile.value.salary_min = p.salary_min
      if (p.salary_max) profile.value.salary_max = p.salary_max
      if (p.experience_min) profile.value.experience_min = p.experience_min
      if (p.experience_max) profile.value.experience_max = p.experience_max
    }
  } catch (error) {
    console.error('获取画像失败:', error)
  }
}

const saveProfile = async () => {
  try {
    const userId = localStorage.getItem('user_id') || 1
    console.log('Saving profile for user:', userId)
    const result = await api.put(`/api/users/${userId}/profile`, {
      directions: profile.value.directions,
      planning_daily_limit: profile.value.planning_daily_limit,
      design_daily_limit: profile.value.design_daily_limit,
      total_daily_limit: profile.value.total_daily_limit,
      include_keywords: profile.value.include_keywords,
      prefer_keywords: profile.value.prefer_keywords,
      exclude_keywords: profile.value.exclude_keywords,
      prefer_companies: profile.value.prefer_companies,
      exclude_companies: profile.value.exclude_companies,
      prefer_industries: profile.value.prefer_industries,
      exclude_industries: profile.value.exclude_industries,
      fuzzy_keywords: profile.value.fuzzy_keywords,
      scoring_threshold: profile.value.scoring_threshold,
      target_cities: profile.value.target_cities.split(',').map(s => s.trim()),
      exclude_areas: profile.value.exclude_areas.split(',').map(s => s.trim()),
      salary_min: profile.value.salary_min,
      salary_max: profile.value.salary_max,
      experience_min: profile.value.experience_min,
      experience_max: profile.value.experience_max
    })
    console.log('Save result:', result)
    alert('画像保存成功')
  } catch (error) {
    console.error('Save error:', error)
    alert('保存失败: ' + (error.message || error))
  }
}
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.content {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  margin-bottom: 32px;
}

.page-header h2 {
  font-size: 28px;
  color: #333;
  margin-bottom: 4px;
}

.page-header p {
  color: #666;
}

.profile-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.form-card h3 {
  font-size: 18px;
  color: #333;
  margin-bottom: 8px;
}

.helper-text {
  font-size: 14px;
  color: #666;
  margin-bottom: 16px;
}

/* 求职方向选择 */
.direction-selector {
  display: flex;
  gap: 16px;
}

.direction-option {
  flex: 1;
  padding: 16px;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.direction-option:hover {
  border-color: #007bff;
}

.direction-option.active {
  border-color: #007bff;
  background: #f0f7ff;
}

.direction-option input[type="checkbox"] {
  display: none;
}

.direction-title {
  display: block;
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.direction-desc {
  display: block;
  font-size: 12px;
  color: #666;
}

/* 关键词标签 */
.keyword-section {
  margin-bottom: 20px;
}

.section-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
}

.keyword-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

/* 投递数量设置 */
.apply-limits-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px dashed #e0e0e0;
}

.apply-limits-section h4 {
  font-size: 16px;
  color: #333;
  margin-bottom: 8px;
}

.direction-apply-limits {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
}

.direction-limit-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.direction-limit-item label {
  font-size: 14px;
  color: #666;
}

.direction-limit-item input {
  width: 80px;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  text-align: center;
}

.total-limit {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 8px;
}

.total-limit label {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.total-limit input {
  width: 80px;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  text-align: center;
}

.total-limit .helper-text {
  margin-bottom: 0;
}

.keyword-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 13px;
}

.keyword-tag.include {
  background: #e3f2fd;
  color: #1565c0;
}

.keyword-tag.prefer {
  background: #e8f5e9;
  color: #2e7d32;
}

.keyword-tag.exclude {
  background: #ffebee;
  color: #c62828;
}

.keyword-tag.company-priority {
  background: #e3f2fd;
  color: #1565c0;
}

.keyword-tag.company-exclude {
  background: #ffebee;
  color: #c62828;
}

.keyword-tag.fuzzy {
  background: #fff3e0;
  color: #e65100;
}

.remove-btn {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 0;
  font-size: 12px;
  opacity: 0.7;
}

.remove-btn:hover {
  opacity: 1;
}

.keyword-input-row {
  display: flex;
  gap: 8px;
}

.keyword-input-row input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
}

.add-btn {
  padding: 10px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.add-btn.danger {
  background: #dc3545;
}

.add-btn:hover {
  opacity: 0.9;
}

/* 排除规则 */
.exclude-rule {
  margin-top: 16px;
  padding: 12px;
  background: #fff3e0;
  border-radius: 8px;
}

.rule-title {
  font-size: 13px;
  font-weight: 600;
  color: #e65100;
  margin-bottom: 4px;
}

.rule-text {
  font-size: 13px;
  color: #666;
}

/* 公司边界 */
.company-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.company-type {
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
}

.type-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 12px;
}

/* 打分卡片 */
.scoring-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.scoring-card h3 {
  color: white;
}

.scoring-card .helper-text {
  color: rgba(255, 255, 255, 0.8);
}

.scoring-rules {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 16px;
}

.rule-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 8px;
}

.rule-item.negative {
  background: rgba(0, 0, 0, 0.2);
}

.rule-name {
  font-size: 14px;
}

.rule-score {
  font-weight: 600;
}

.scoring-threshold {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 14px;
}

.scoring-threshold input {
  width: 60px;
  padding: 6px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  text-align: center;
}

.fuzzy-keywords .section-label {
  color: rgba(255, 255, 255, 0.9);
}

/* 基本信息 */
.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
}

.form-group input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
}

.form-group input:focus {
  outline: none;
  border-color: #007bff;
}

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

.save-btn {
  width: 100%;
  padding: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s;
}

.save-btn:hover {
  transform: translateY(-2px);
}
</style>
