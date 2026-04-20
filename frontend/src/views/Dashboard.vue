<template>
  <div class="dashboard">
    <Navbar />

    <main class="content">
      <header class="page-header">
        <h2>控制台</h2>
        <p class="welcome">欢迎回来！</p>
      </header>

      <!-- 标签页切换 -->
      <div class="tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          :class="['tab-btn', { active: currentTab === tab.key }]"
          @click="currentTab = tab.key"
        >
          {{ tab.icon }} {{ tab.label }}
        </button>
      </div>

      <!-- Tab 1: 职位推荐 -->
      <div v-show="currentTab === 'feed'" class="tab-content">
        <section class="stats-grid">
          <div class="stat-card">
            <div class="stat-icon pending">⏳</div>
            <div class="stat-info">
              <span class="stat-value">{{ stats.pending }}</span>
              <span class="stat-label">待处理</span>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon submitted">✅</div>
            <div class="stat-info">
              <span class="stat-value">{{ stats.submitted }}</span>
              <span class="stat-label">已投递</span>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon failed">❌</div>
            <div class="stat-info">
              <span class="stat-value">{{ stats.failed }}</span>
              <span class="stat-label">失败</span>
            </div>
          </div>
        </section>

        <!-- Job Feed Section -->
        <section class="job-feed-section">
          <div class="section-header">
            <h3>🎯 为您推荐</h3>
            <div class="feed-controls">
              <span class="feed-count" v-if="feedTotal > 0">共 {{ feedTotal }} 个职位</span>
              <button class="refresh-btn" @click="refreshFeed" :disabled="loading">🔄 刷新</button>
            </div>
          </div>

          <div v-if="loading && !jobFeed.length" class="loading-state">
            <div class="spinner"></div>
            <span>加载中...</span>
          </div>
          <div class="job-feed" v-else-if="jobFeed.length">
            <JobCard
              v-for="job in jobFeed"
              :key="job.job_id"
              :job="job"
              :show-score-breakdown="showScoreBreakdown"
              @action="handleJobAction"
            />
            <div v-if="feedHasMore" class="load-more">
              <button class="load-more-btn" @click="loadMore" :disabled="loadingMore">
                {{ loadingMore ? '加载中...' : '加载更多' }}
              </button>
            </div>
          </div>
          <div v-else class="empty-state">
            <div class="empty-icon">📭</div>
            <div class="empty-text">暂无推荐职位</div>
            <div class="empty-hint">请先运行数据采集任务，获取更多职位推荐</div>
            <button class="action-btn primary" @click="runNow" :disabled="running || cookieStatus !== 'valid'">
              ▶ 立即采集
            </button>
          </div>
        </section>
      </div>

      <!-- Tab 2: 投递记录 -->
      <div v-show="currentTab === 'applications'" class="tab-content">
        <section class="applications-section">
          <div class="section-header">
            <h3>📋 投递记录</h3>
            <button class="refresh-btn" @click="fetchApplications">🔄 刷新</button>
          </div>

          <div v-if="loading && !applications.length" class="loading-state">
            <div class="spinner"></div>
            <span>加载中...</span>
          </div>
          <div v-else-if="applications.length" class="applications-table">
            <table>
              <thead>
                <tr>
                  <th>职位</th>
                  <th>公司</th>
                  <th>状态</th>
                  <th>时间</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="app in paginatedApplications" :key="app.id">
                  <td>{{ app.job_title || '未知' }}</td>
                  <td>{{ app.company || '未知' }}</td>
                  <td>
                    <span :class="['status-tag', app.status]">
                      {{ statusLabels[app.status] || app.status }}
                    </span>
                  </td>
                  <td>{{ formatDate(app.created_at) }}</td>
                </tr>
              </tbody>
            </table>
            <div class="pagination" v-if="totalPages > 1">
              <button @click="currentPage--" :disabled="currentPage === 1">上一页</button>
              <span>{{ currentPage }} / {{ totalPages }}</span>
              <button @click="currentPage++" :disabled="currentPage === totalPages">下一页</button>
            </div>
          </div>
          <div v-else class="empty-state">
            <div class="empty-icon">📭</div>
            <div class="empty-text">暂无投递记录</div>
          </div>
        </section>
      </div>

      <!-- Tab 3: 数据分析 -->
      <div v-show="currentTab === 'analytics'" class="tab-content">
        <section class="analytics-section">
          <!-- V3.3 流程概览 -->
          <section class="v33-overview">
            <h3>🧠 V3.3 智能引擎分析</h3>
            <div class="v33-flow">
              <div class="flow-step">
                <div class="flow-icon vision">👁️</div>
                <div class="flow-info">
                  <span class="flow-name">Vision</span>
                  <span class="flow-desc">按钮检测模型</span>
                  <span :class="['flow-status', engineStatus.vision === 'ACTIVE' ? 'active' : 'standby']">
                    {{ engineStatus.vision === 'ACTIVE' ? '运行中' : '待机' }}
                  </span>
                </div>
              </div>
              <div class="flow-arrow">→</div>
              <div class="flow-step">
                <div class="flow-icon embedding">🔍</div>
                <div class="flow-info">
                  <span class="flow-name">Embedding</span>
                  <span class="flow-desc">相似度匹配</span>
                  <span :class="['flow-status', engineStatus.embedding === 'ACTIVE' ? 'active' : 'standby']">
                    {{ engineStatus.embedding === 'ACTIVE' ? '运行中' : '待机' }}
                  </span>
                </div>
              </div>
              <div class="flow-arrow">→</div>
              <div class="flow-step">
                <div class="flow-icon decision">🎯</div>
                <div class="flow-info">
                  <span class="flow-name">Decision</span>
                  <span class="flow-desc">智能决策</span>
                  <span :class="['flow-status', engineStatus.learning === 'ACTIVE' ? 'active' : 'standby']">
                    {{ engineStatus.learning === 'ACTIVE' ? '运行中' : '待机' }}
                  </span>
                </div>
              </div>
              <div class="flow-arrow">→</div>
              <div class="flow-step">
                <div class="flow-icon recovery">🛡️</div>
                <div class="flow-info">
                  <span class="flow-name">Recovery</span>
                  <span class="flow-desc">异常恢复</span>
                  <span :class="['flow-status', engineStatus.recovery === 'ACTIVE' ? 'active' : 'standby']">
                    {{ engineStatus.recovery === 'ACTIVE' ? '运行中' : '待机' }}
                  </span>
                </div>
              </div>
            </div>
          </section>

          <!-- Stats Overview -->
          <section class="stats-overview">
            <div class="stat-card">
              <div class="stat-icon total">📋</div>
              <div class="stat-info">
                <span class="stat-value">{{ analyticsData.total_applies }}</span>
                <span class="stat-label">总投递数</span>
              </div>
            </div>
            <div class="stat-card success">
              <div class="stat-icon success-icon">✅</div>
              <div class="stat-info">
                <span class="stat-value">{{ analyticsData.success_rate }}%</span>
                <span class="stat-label">成功率</span>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon companies">🏢</div>
              <div class="stat-info">
                <span class="stat-value">{{ analyticsData.total_companies }}</span>
                <span class="stat-label">学习公司数</span>
              </div>
            </div>
          </section>

          <!-- V3.3 任务执行历史 -->
          <section class="task-history-section" v-if="recentTasks.length > 0">
            <h3>📜 最近任务执行</h3>
            <div class="task-history-list">
              <div v-for="task in recentTasks" :key="task.id" class="task-history-item">
                <div class="task-id">#{{ task.id }}</div>
                <div class="task-status">
                  <span :class="['status-badge', task.status.toLowerCase()]">
                    {{ task.status === 'COMPLETED' ? '完成' : task.status === 'FAILED' ? '失败' : task.status === 'RUNNING' ? '运行中' : '待处理' }}
                  </span>
                </div>
                <div class="task-stats">
                  <span class="task-stat">搜索: {{ task.jobs_found || 0 }}</span>
                  <span class="task-stat">匹配: {{ task.jobs_filtered || 0 }}</span>
                  <span class="task-stat success">投递: {{ task.applications_submitted || 0 }}</span>
                  <span class="task-stat failed" v-if="task.applications_failed > 0">失败: {{ task.applications_failed }}</span>
                </div>
                <div class="task-time">{{ formatDate(task.created_at) }}</div>
              </div>
            </div>
          </section>

          <!-- Empty State -->
          <section v-else class="empty-analytics">
            <div class="empty-icon">📊</div>
            <div class="empty-text">暂无分析数据</div>
            <div class="empty-hint">运行V3.3任务后，这里将显示详细的执行分析</div>
            <button class="action-btn primary" @click="currentTab = 'platform'">
              🔐 去配置Cookie并运行
            </button>
          </section>

          <!-- High Success Companies -->
          <section class="companies-section" v-if="topCompanies.length > 0">
            <h3>🏆 成功学习记录</h3>
            <div class="companies-list">
              <div v-for="company in topCompanies" :key="company.name" class="company-item">
                <div class="company-name">{{ company.name }}</div>
                <div class="company-stats">
                  <span class="company-count">投递 {{ company.applyCount }} 次</span>
                  <span class="company-rate success">{{ company.successRate }}%</span>
                </div>
              </div>
            </div>
          </section>

          <!-- Engine Models Info -->
          <section class="engine-models-section">
            <h3>⚙️ V3.3 模型配置</h3>
            <div class="models-grid">
              <div class="model-card">
                <div class="model-name">Vision 模型</div>
                <div class="model-value">doubao-seed-2-0-code-preview-260215</div>
                <div class="model-desc">按钮检测与界面分析</div>
              </div>
              <div class="model-card">
                <div class="model-name">Embedding 模型</div>
                <div class="model-value">doubao-embedding-vision-251215</div>
                <div class="model-desc">职位相似度匹配</div>
              </div>
              <div class="model-card">
                <div class="model-name">决策引擎</div>
                <div class="model-value">V3.3 Decision Engine</div>
                <div class="model-desc">智能投递决策</div>
              </div>
              <div class="model-card">
                <div class="model-name">学习引擎</div>
                <div class="model-value">Success Learning v1.0</div>
                <div class="model-desc">从成功案例学习</div>
              </div>
            </div>
          </section>
        </section>
      </div>

      <!-- Tab 4: 平台Cookie -->
      <div v-show="currentTab === 'platform'" class="tab-content">
        <!-- 凭证配置 -->
        <section class="credentials-section">
          <div class="credentials-card">
            <div class="credentials-header">
              <h3>🔐 平台 Cookie</h3>
            </div>

            <!-- 平台选择标签 -->
            <div class="platform-tabs">
              <button
                v-for="platform in platforms"
                :key="platform.id"
                :class="['platform-tab', { active: currentPlatform === platform.id }]"
                @click="switchPlatform(platform.id)"
              >
                {{ platform.name }}
                <span v-if="platformStates[platform.id]?.running" class="tab-status running">🔄</span>
                <span v-else-if="getPlatformStatus(platform.id) === 'valid'" class="tab-status valid">✅</span>
                <span v-else-if="getPlatformStatus(platform.id) === 'invalid'" class="tab-status invalid">❌</span>
                <span v-else class="tab-status unknown">⚠️</span>
              </button>
            </div>

            <!-- 当前平台的Cookie配置 -->
            <div class="platform-config">
              <div class="platform-info">
                <span class="platform-name">{{ currentPlatformName }}</span>
                <span v-if="loggedInUsername" class="username-badge">👤 {{ loggedInUsername }}</span>
              </div>

              <!-- Cookie失效警告 -->
              <div v-if="getPlatformStatus(currentPlatform) !== 'valid'" class="cookie-warning">
                <p>⚠️ Cookie 未配置或已过期</p>
                <button class="phone-verify-btn" @click="showPhoneVerification">
                  📱 使用手机验证码登录
                </button>
              </div>

              <!-- 手机验证面板（可以手动触发或自动触发） -->
              <div v-if="forcePhoneLogin.required" class="force-phone-login-inline">
                <div class="force-phone-login-header">
                  <h4>🔐 需要手机验证</h4>
                  <p>{{ forcePhoneLogin.message || 'Cookie失效，请完成手机验证' }}</p>
                </div>

                <div class="phone-input-row">
                  <input
                    v-model="forcePhoneLogin.phone"
                    type="tel"
                    placeholder="输入手机号"
                    :disabled="forcePhoneLogin.code_sent"
                  />
                  <button
                    class="send-code-btn"
                    @click="forceSendCode"
                    :disabled="!forcePhoneLogin.phone || forcePhoneLogin.sending"
                  >
                    {{ forcePhoneLogin.sending ? '发送...' : '发送验证码' }}
                  </button>
                </div>

                <div v-if="forcePhoneLogin.code_sent && !forcePhoneLogin.verified" class="code-input-row">
                  <input
                    v-model="forcePhoneLogin.code"
                    type="text"
                    placeholder="输入验证码"
                    maxlength="6"
                  />
                  <button
                    class="verify-code-btn"
                    @click="forceVerifyCode"
                    :disabled="!forcePhoneLogin.code || forcePhoneLogin.verifying"
                  >
                    {{ forcePhoneLogin.verifying ? '验证中...' : '验证' }}
                  </button>
                </div>

                <div v-if="forcePhoneLogin.verified" class="force-phone-success">
                  ✅ 验证成功，任务继续中...
                </div>
              </div>

              <!-- Cookie 输入（可选） -->
              <div class="cookie-input">
                <textarea
                  v-model="platformCookies[currentPlatform]"
                  :placeholder="`粘贴 ${currentPlatformName} 的 Cookie...（可选）`"
                  rows="2"
                ></textarea>
                <button class="save-cookie-btn" @click="savePlatformCookie(currentPlatform)" :disabled="savingCookie">
                  {{ savingCookie ? '保存中...' : '保存 Cookie' }}
                </button>
              </div>

              <p class="helper-text">
                如何获取 Cookie？打开 {{ currentPlatformName }} 官网 → 登录 → 按 F12 打开开发者工具 → Application → Cookies → 复制 Cookie 值
              </p>
            </div>
          </div>
        </section>

        <!-- 操作按钮 -->
        <section class="actions-section">
          <button class="action-btn login-btn" @click="loginPlatform" :disabled="loggingIn || cookieStatus !== 'valid'">
            {{ loggingIn ? '登录中...' : '🔑 平台登录' }}
          </button>
          <button class="action-btn primary" @click="runNow" :disabled="running || cookieStatus !== 'valid'">
            {{ running ? '运行中...' : '▶ 开始运行' }}
          </button>
          <button v-if="running" class="action-btn danger" @click="stopNow" :disabled="!running">
            ⏹ 停止
          </button>
          <button class="action-btn secondary" @click="setSchedule">
            ⏰ 设置定时任务
          </button>
        </section>

        <!-- 运行中状态面板 -->
        <section v-if="running || executionLogs.length > 0" class="running-section">
          <div class="running-card">
            <!-- 步骤流程可视化 -->
            <div class="step-flow">
              <h4>🧠 Agent 执行流程</h4>
              <div class="step-list">
                <div
                  v-for="(step, index) in executionSteps"
                  :key="index"
                  :class="['step-item', step.status]"
                >
                  <span class="step-icon">
                    <span v-if="step.status === 'success'" class="icon-success">✅</span>
                    <span v-else-if="step.status === 'failed'" class="icon-failed">❌</span>
                    <span v-else-if="step.status === 'running'" class="icon-running">⏳</span>
                    <span v-else class="icon-pending">⭕</span>
                  </span>
                  <span class="step-name">{{ step.name }}</span>
                  <span class="step-message" v-if="step.message">{{ step.message }}</span>
                </div>
              </div>
            </div>

            <!-- 决策透明化面板 -->
            <div v-if="currentDecision" class="decision-panel">
              <h4>🎯 AI 决策过程</h4>
              <div class="decision-content">
                <div class="decision-candidates">
                  <div class="candidate-header">候选按钮:</div>
                  <div
                    v-for="(candidate, index) in currentDecision.candidates"
                    :key="index"
                    :class="['candidate-item', candidate.name === currentDecision.selected ? 'selected' : '']"
                  >
                    <span class="candidate-name">{{ candidate.name }}</span>
                    <span class="candidate-score">{{ (candidate.score * 100).toFixed(0) }}%</span>
                  </div>
                </div>
                <div class="decision-result">
                  <div class="decision-selected">
                    <span class="label">👉 选择:</span>
                    <span class="value">{{ currentDecision.selected }}</span>
                    <span class="score">({{ (currentDecision.score * 100).toFixed(0) }}%)</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 实时日志 -->
            <div class="realtime-logs">
              <h4>📜 实时日志</h4>
              <div class="log-list" :ref="el => { if (el) platformLogListRefs[currentPlatform] = el }">
                <div
                  v-for="(log, index) in executionLogs"
                  :key="index"
                  :class="['log-item', log.level]"
                >
                  <span class="log-time">{{ log.time }}</span>
                  <span class="log-step">[{{ log.step }}]</span>
                  <span class="log-message">{{ log.message }}</span>
                </div>
              </div>
            </div>

            <!-- 失败原因面板 -->
            <div v-if="failureReasons.length > 0" class="failure-panel">
              <h4>⚠️ 失败原因</h4>
              <ul class="failure-list">
                <li v-for="(reason, index) in failureReasons" :key="index">
                  {{ reason }}
                </li>
              </ul>
            </div>

            <!-- 统计信息 -->
            <div class="running-stats">
              <div class="stat-item">
                <span class="stat-label">已搜索</span>
                <span class="stat-value">{{ runningStats.jobsFound }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">已匹配</span>
                <span class="stat-value">{{ runningStats.jobsFiltered }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">已投递</span>
                <span class="stat-value">{{ runningStats.applicationsSubmitted }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">失败</span>
                <span class="stat-value failed">{{ runningStats.applicationsFailed }}</span>
              </div>
            </div>

            <!-- V3.4 RiskScore 仪表盘 -->
            <RiskScoreGauge
              v-if="showRiskGauge"
              :score="riskScore"
              :threshold="riskThreshold"
              :consecutiveSuccess="consecutiveSuccess"
              :factors="riskFactors"
            />
          </div>
        </section>
      </div>

    <!-- V3.4 人工干预面板 -->
    <HumanInterventionPanel
      :visible="humanIntervention.visible"
      :job="humanIntervention.job"
      :riskScore="humanIntervention.riskScore"
      :threshold="humanIntervention.threshold"
      :reason="humanIntervention.reason"
      :factors="humanIntervention.factors"
      :logs="humanIntervention.logs"
      @action="handleHumanIntervention"
      @close="humanIntervention.visible = false"
    />

    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import Navbar from '@/components/Navbar.vue'
import JobCard from '@/components/JobCard.vue'
import SuccessRateChart from '@/components/SuccessRateChart.vue'
import FailureReasonChart from '@/components/FailureReasonChart.vue'
import EngineStatus from '@/components/EngineStatus.vue'
import HighSuccessCompanies from '@/components/HighSuccessCompanies.vue'
import api from '@/api'
import RiskScoreGauge from '@/components/RiskScoreGauge.vue'
import HumanInterventionPanel from '@/components/HumanInterventionPanel.vue'

const router = useRouter()

// Tab system
const tabs = [
  { key: 'feed', label: '职位推荐', icon: '🎯' },
  { key: 'applications', label: '投递记录', icon: '📋' },
  { key: 'analytics', label: '数据分析', icon: '📊' },
  { key: 'platform', label: '平台Cookie', icon: '🔐' }
]
const currentTab = ref('feed')

// Stats
const stats = ref({ pending: 0, submitted: 0, failed: 0 })
const applications = ref([])

// ========== 多平台并发状态管理 ==========
// 每个平台有独立的运行状态、日志、SSE连接
const platformStates = reactive({
  zhilian: {
    running: false,
    taskId: null,
    executionSteps: [
      { name: '登录', status: 'pending', message: '' },
      { name: '搜索职位', status: 'pending', message: '' },
      { name: '过滤职位', status: 'pending', message: '' },
      { name: '智能投递', status: 'pending', message: '' },
      { name: '结果验证', status: 'pending', message: '' }
    ],
    executionLogs: [],
    failureReasons: [],
    runningStats: { jobsFound: 0, jobsFiltered: 0, applicationsSubmitted: 0, applicationsFailed: 0 },
    eventSource: null,
    riskScore: 0,
    showRiskGauge: false
  },
  job51: {
    running: false,
    taskId: null,
    executionSteps: [
      { name: '登录', status: 'pending', message: '' },
      { name: '搜索职位', status: 'pending', message: '' },
      { name: '过滤职位', status: 'pending', message: '' },
      { name: '智能投递', status: 'pending', message: '' },
      { name: '结果验证', status: 'pending', message: '' }
    ],
    executionLogs: [],
    failureReasons: [],
    runningStats: { jobsFound: 0, jobsFiltered: 0, applicationsSubmitted: 0, applicationsFailed: 0 },
    eventSource: null,
    riskScore: 0,
    showRiskGauge: false
  },
  boss: {
    running: false,
    taskId: null,
    executionSteps: [
      { name: '登录', status: 'pending', message: '' },
      { name: '搜索职位', status: 'pending', message: '' },
      { name: '过滤职位', status: 'pending', message: '' },
      { name: '智能投递', status: 'pending', message: '' },
      { name: '结果验证', status: 'pending', message: '' }
    ],
    executionLogs: [],
    failureReasons: [],
    runningStats: { jobsFound: 0, jobsFiltered: 0, applicationsSubmitted: 0, applicationsFailed: 0 },
    eventSource: null,
    riskScore: 0,
    showRiskGauge: false
  }
})

// 保持向后兼容的别名（用于当前选中的平台）
const running = computed(() => platformStates[currentPlatform.value]?.running || false)
const runningStats = computed(() => platformStates[currentPlatform.value]?.runningStats || { jobsFound: 0, jobsFiltered: 0, applicationsSubmitted: 0, applicationsFailed: 0 })
const executionSteps = computed(() => platformStates[currentPlatform.value]?.executionSteps || [])
const executionLogs = computed(() => platformStates[currentPlatform.value]?.executionLogs || [])

const currentStep = ref('正在启动任务...')
const progressPercent = ref(0)

// V3.4 RiskScore
const riskScore = ref(0)
const riskThreshold = ref(0.7)
const consecutiveSuccess = ref(0)
const riskFactors = ref([])
const showRiskGauge = ref(false)

// V3.4 Human Intervention
const humanIntervention = ref({
  visible: false,
  job: { title: '', company: '', url: '' },
  riskScore: 0,
  threshold: 0.7,
  reason: '',
  factors: [],
  logs: []
})
const cookieInput = ref('')

// Agent 执行可视化 - 使用平台状态中的步骤和日志
const failureReasons = computed(() => platformStates[currentPlatform.value]?.failureReasons || [])
const currentTaskId = ref(null)  // 当前连接的任务ID

// Application table
const showApplications = ref(false)
const currentPage = ref(1)
const pageSize = 10
const cookieStatus = ref('unknown')
const savingCookie = ref(false)
const loggingIn = ref(false)
const loggedInUsername = ref('')

// 强制手机验证（投递过程中使用）
const forcePhoneLogin = ref({
  required: false,
  phone: '',
  code: '',
  code_sent: false,
  verified: false,
  sending: false,
  verifying: false,
  message: ''
})

let forceLoginPollInterval = null

// 显示手机验证面板（手动触发）
function showPhoneVerification() {
  forcePhoneLogin.value.required = true
  forcePhoneLogin.value.phone = ''
  forcePhoneLogin.value.code = ''
  forcePhoneLogin.value.code_sent = false
  forcePhoneLogin.value.verified = false
  forcePhoneLogin.value.message = '请输入手机号完成验证'

  // 开始轮询登录状态
  if (forceLoginPollInterval) {
    clearInterval(forceLoginPollInterval)
  }
  forceLoginPollInterval = setInterval(checkForcePhoneLoginStatus, 2000)
}

async function forceSendCode() {
  if (!forcePhoneLogin.value.phone) return

  forcePhoneLogin.value.sending = true
  forcePhoneLogin.value.message = ''

  try {
    const userId = localStorage.getItem('user_id') || 1
    const res = await api.post('/api/auth/phone-login/submit-phone', {
      user_id: parseInt(userId),
      phone: forcePhoneLogin.value.phone,
      platform: currentPlatform.value
    })

    if (res.success) {
      forcePhoneLogin.value.code_sent = true
      forcePhoneLogin.value.message = res.message || '验证码已发送'
    } else {
      forcePhoneLogin.value.message = res.error || '发送失败'
    }
  } catch (e) {
    forcePhoneLogin.value.message = '发送验证码失败'
  } finally {
    forcePhoneLogin.value.sending = false
  }
}

async function forceVerifyCode() {
  if (!forcePhoneLogin.value.code) return

  forcePhoneLogin.value.verifying = true
  forcePhoneLogin.value.message = ''

  try {
    const userId = localStorage.getItem('user_id') || 1
    const res = await api.post('/api/auth/phone-login/submit-code', {
      user_id: parseInt(userId),
      code: forcePhoneLogin.value.code,
      platform: currentPlatform.value
    })

    if (res.success) {
      forcePhoneLogin.value.verified = true
      forcePhoneLogin.value.message = '验证成功！'
      cookieStatus.value = 'valid'

      // 停止轮询
      if (forceLoginPollInterval) {
        clearInterval(forceLoginPollInterval)
        forceLoginPollInterval = null
      }

      // 隐藏强制验证面板
      setTimeout(() => {
        forcePhoneLogin.value.required = false
      }, 2000)
    } else {
      forcePhoneLogin.value.message = res.error || '验证失败'
    }
  } catch (e) {
    forcePhoneLogin.value.message = '验证失败'
  } finally {
    forcePhoneLogin.value.verifying = false
  }
}

async function checkForcePhoneLoginStatus() {
  if (!forcePhoneLogin.value.required) return

  try {
    const userId = localStorage.getItem('user_id') || 1
    const res = await api.get(`/api/auth/phone-login/status/${userId}`)

    if (res.state === 'waiting_phone') {
      // 等待用户输入手机号
    } else if (res.state === 'waiting_code') {
      forcePhoneLogin.value.code_sent = true
      forcePhoneLogin.value.message = res.message || '验证码已发送，请在下方输入'
    } else if (res.state === 'completed') {
      forcePhoneLogin.value.verified = true
      cookieStatus.value = 'valid'
      forcePhoneLogin.value.message = '验证成功！'

      setTimeout(() => {
        forcePhoneLogin.value.required = false
      }, 2000)
    } else if (res.state === 'failed') {
      forcePhoneLogin.value.message = res.error || '验证失败'
    }
  } catch (e) {
    console.error('检查手机登录状态失败:', e)
  }
}

// 平台Cookie管理
const platforms = [
  { id: 'zhilian', name: '智联招聘' },
  { id: 'boss', name: 'BOSS直聘' },
  { id: 'job51', name: '前程无忧' }
]
const currentPlatform = ref('zhilian')
const platformCookies = ref({
  'zhilian': '',
  'boss': '',
  'job51': ''
})

const currentPlatformName = computed(() => {
  const p = platforms.find(p => p.id === currentPlatform.value)
  return p ? p.name : currentPlatform.value
})

function getPlatformStatus(platformId) {
  // 统一使用智联的状态作为参考
  return cookieStatus.value
}

function switchPlatform(platformId) {
  currentPlatform.value = platformId
  // 切换平台后更新cookie状态
  const cookie = platformCookies.value[platformId]
  if (cookie && cookie.length > 10) {
    cookieStatus.value = 'valid'
  } else {
    cookieStatus.value = 'unknown'
  }
}

async function savePlatformCookie(platformId) {
  const cookie = platformCookies.value[platformId]
  if (!cookie) return

  savingCookie.value = true
  try {
    const userId = localStorage.getItem('user_id') || 1

    // 获取现有凭证 (API返回结构是嵌套的)
    const userRes = await api.get(`/api/users/${userId}`)
    const existingCreds = userRes.profile?.platform_credentials || {}

    // 更新对应平台的Cookie
    existingCreds[platformId] = { cookie: cookie }

    await api.put(`/api/users/${userId}/profile`, {
      platform_credentials: existingCreds
    })

    // 如果是当前选中的平台，更新状态
    if (platformId === currentPlatform.value) {
      cookieStatus.value = 'valid'
    }

    alert(`${platforms.find(p => p.id === platformId).name} Cookie 保存成功`)
  } catch (e) {
    alert('Cookie 保存失败')
  } finally {
    savingCookie.value = false
  }
}

// Job Feed
const jobFeed = ref([])
const loading = ref(false)
const loadingMore = ref(false)
const feedOffset = ref(0)
const feedTotal = ref(0)
const feedHasMore = ref(false)
const currentWeights = ref(null)
const showScoreBreakdown = ref(false)

// Analytics data
const analyticsData = ref({
  total_applies: 0,
  success_rate: 0,
  total_companies: 0,
  success_trend: [],
  failure_reasons: [],
  top_companies: []
})
const engineStatus = ref({
  vision: 'STANDBY',
  embedding: 'STANDBY',
  recovery: 'STANDBY',
  learning: 'STANDBY'
})
const recentTasks = ref([])
const currentDecision = ref(null)  // 当前决策透明化数据

// Status labels
const statusLabels = {
  'submitted': '已投递',
  'pending': '待处理',
  'failed': '失败',
  'rejected': '已拒绝'
}

// Computed
const totalPages = computed(() => Math.ceil(applications.value.length / pageSize))
const paginatedApplications = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return applications.value.slice(start, start + pageSize)
})
const successTrendData = computed(() => analyticsData.value.success_trend.map(item => ({
  date: formatDate(item.date),
  rate: item.rate
})))
const failureReasonsData = computed(() => analyticsData.value.failure_reasons.map(item => ({
  name: item.name,
  count: item.count,
  color: item.color || '#999'
})))
const topCompanies = computed(() => analyticsData.value.top_companies.slice(0, 10).map(c => ({
  name: c.name,
  applyCount: c.apply_count,
  successRate: c.success_rate
})))

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

async function fetchStats() {
  try {
    const userId = localStorage.getItem('user_id') || 1
    const res = await api.get(`/api/applications/user/${userId}/stats`)
    stats.value = res
  } catch (e) {
    console.error('获取统计失败:', e)
  }
}

async function fetchApplications() {
  try {
    loading.value = true
    const userId = localStorage.getItem('user_id') || 1
    const res = await api.get(`/api/applications/user/${userId}`)
    applications.value = res
  } catch (e) {
    console.error('获取投递记录失败:', e)
  } finally {
    loading.value = false
  }
}

async function fetchAnalyticsData() {
  try {
    const userId = localStorage.getItem('user_id') || 1

    // 获取V3.3分析数据
    const [analyticsRes, engineRes] = await Promise.all([
      api.get(`/api/analytics/v33/${userId}`),
      api.get('/api/analytics/engine-status')
    ])

    // 转换数据格式
    const taskStats = analyticsRes.task_stats
    const enginePerf = analyticsRes.engine_performance

    analyticsData.value = {
      total_applies: taskStats.total_applications,
      success_rate: taskStats.success_rate,
      total_companies: analyticsRes.success_learning.length,
      success_trend: [],
      failure_reasons: [],
      top_companies: analyticsRes.success_learning.slice(0, 10).map(item => ({
        name: item.company,
        apply_count: item.success_count,
        success_rate: 100  // 学习记录都是成功的
      }))
    }

    // 更新引擎状态
    engineStatus.value = {
      vision: engineRes.vision.status,
      embedding: engineRes.embedding.status,
      recovery: engineRes.recovery.status,
      learning: engineRes.learning.status
    }

    // 存储最近任务用于显示
    recentTasks.value = analyticsRes.recent_tasks || []
  } catch (e) {
    console.error('获取分析数据失败:', e)
  }
}

async function fetchRecommendations() {
  loading.value = true
  try {
    const userId = localStorage.getItem('user_id') || 1
    const res = await api.get(`/api/jobs/recommend/${userId}/feed?limit=10&offset=0`)
    jobFeed.value = res.jobs || []
    feedTotal.value = res.total || 0
    feedHasMore.value = res.has_more || false
    feedOffset.value = 10
    if (res.weights) {
      currentWeights.value = res.weights
    }
  } catch (e) {
    console.error('获取推荐失败:', e)
  } finally {
    loading.value = false
  }
}

async function refreshFeed() {
  feedOffset.value = 0
  await fetchRecommendations()
}

async function loadMore() {
  loadingMore.value = true
  try {
    const userId = localStorage.getItem('user_id') || 1
    const res = await api.get(`/api/jobs/recommend/${userId}/feed?limit=10&offset=${feedOffset.value}`)
    jobFeed.value = [...jobFeed.value, ...(res.jobs || [])]
    feedHasMore.value = res.has_more || false
    feedOffset.value += 10
  } catch (e) {
    console.error('加载更多失败:', e)
  } finally {
    loadingMore.value = false
  }
}

function handleJobAction({ job, action }) {
  console.log('Job action:', job, action)
}

const loginPlatform = async () => {
  if (cookieStatus.value !== 'valid') {
    alert('请先配置有效的 Cookie 再进行登录')
    return
  }
  loggingIn.value = true
  currentStep.value = '正在登录...'
  try {
    const userId = localStorage.getItem('user_id') || 1
    const result = await api.post('/api/tasks/v3/login', { user_id: Number(userId), platform: currentPlatform.value })
    console.log('登录结果:', result)

    // 轮询任务状态获取登录结果
    if (result.task_id) {
      await pollTaskResult(result.task_id, (taskResult) => {
        if (taskResult.result_data) {
          const data = typeof taskResult.result_data === 'string'
            ? JSON.parse(taskResult.result_data)
            : taskResult.result_data
          if (data.username) {
            loggedInUsername.value = data.username
          }
        }
        if (taskResult.status === 'COMPLETED') {
          currentStep.value = '登录完成'
        }
      })
    }

    alert('登录任务已完成')
  } catch (e) {
    console.error('登录失败:', e)
    alert('登录失败')
  } finally {
    loggingIn.value = false
    currentStep.value = '正在启动任务...'
  }
}

const runNow = async () => {
  if (cookieStatus.value !== 'valid') {
    alert('请先配置有效的 Cookie')
    return
  }

  const platform = currentPlatform.value

  // 重置当前平台的执行状态
  resetExecutionState()
  platformStates[platform].running = true
  platformStates[platform].taskId = null

  try {
    const userId = localStorage.getItem('user_id') || 1
    const result = await api.post('/api/tasks/v3/full-flow', { user_id: Number(userId), platform: platform })
    console.log('运行结果:', result)

    if (result.task_id) {
      // 设置当前平台的 taskId
      platformStates[platform].taskId = result.task_id
      // 连接 SSE 获取实时步骤更新
      connectToSSE(result.task_id, platform)
    }
  } catch (e) {
    console.error('运行失败:', e)
    alert('任务启动失败')
    platformStates[platform].running = false
  }
}

const stopNow = async () => {
  if (!running.value) {
    return
  }

  const platform = currentPlatform.value
  try {
    const userId = localStorage.getItem('user_id') || 1
    // 从最近的任务中获取当前运行的任务ID
    const recentTask = recentTasks.value.find(t => t.status === 'RUNNING')
    if (!recentTask) {
      console.warn('未找到运行中的任务')
      platformStates[platform].running = false
      return
    }

    const result = await api.post(`/api/tasks/${recentTask.id}/stop`)
    console.log('停止结果:', result)

    if (result.success) {
      alert('已发送停止请求')
      // 关闭 SSE 连接
      if (platformStates[platform].eventSource) {
        platformStates[platform].eventSource.close()
        platformStates[platform].eventSource = null
      }
      platformStates[platform].running = false
    } else {
      alert(result.message || '停止失败')
    }
  } catch (e) {
    console.error('停止失败:', e)
    alert('停止任务失败')
  }
}

function resetExecutionState() {
  const platform = currentPlatform.value
  if (!platform || !platformStates[platform]) return

  // 重置当前平台的执行步骤
  platformStates[platform].executionSteps = [
    { name: '登录', status: 'pending', message: '' },
    { name: '搜索职位', status: 'pending', message: '' },
    { name: '过滤职位', status: 'pending', message: '' },
    { name: '智能投递', status: 'pending', message: '' },
    { name: '结果验证', status: 'pending', message: '' }
  ]
  platformStates[platform].executionLogs = []
  platformStates[platform].failureReasons = []
  platformStates[platform].runningStats = { jobsFound: 0, jobsFiltered: 0, applicationsSubmitted: 0, applicationsFailed: 0 }
  platformStates[platform].riskScore = 0
  platformStates[platform].showRiskGauge = false
  currentDecision.value = null
}

function connectToSSE(taskId, platform) {
  const p = platform || currentPlatform.value
  if (!p || !platformStates[p]) return

  // 关闭该平台已有的连接
  if (platformStates[p].eventSource) {
    platformStates[p].eventSource.close()
    platformStates[p].eventSource = null
  }

  const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

  // 先获取历史步骤
  fetchHistorySteps(taskId, p)

  // 连接 SSE
  const es = new EventSource(`${apiBase}/api/events/task-steps/${taskId}`)
  platformStates[p].eventSource = es

  es.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      console.log(`[${p}] SSE事件:`, data)

      // 忽略心跳
      if (data.type === 'heartbeat' || data.type === 'done') {
        return
      }

      handleSSEMessage(data, p)
    } catch (e) {
      console.error('解析SSE消息失败:', e)
    }
  }

  es.onerror = (error) => {
    console.error(`[${p}] SSE错误:`, error)
    // 5秒后重连
    setTimeout(() => {
      if (platformStates[p]?.running) {
        connectToSSE(taskId, p)
      }
    }, 5000)
  }
}

async function fetchHistorySteps(taskId, platform) {
  const p = platform || currentPlatform.value
  try {
    const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
    const response = await fetch(`${apiBase}/api/events/task-steps-history/${taskId}`)
    const data = await response.json()

    if (data.steps && data.steps.length > 0) {
      console.log(`[${p}] 获取历史步骤:`, data.steps.length)
      for (const step of data.steps) {
        handleSSEMessage(step, p)
      }
    }
  } catch (e) {
    console.error('获取历史步骤失败:', e)
  }
}

function handleSSEMessage(event, platform = null) {
  const p = platform || currentPlatform.value
  const step = event.step
  const status = event.status
  const message = event.message
  const data = event.data || {}

  // 调试日志
  console.log(`[${p}] SSE收到事件`, step, status, message)

  // 添加日志
  addExecutionLog(step, status, message, p)

  // 更新步骤状态
  updateStepStatus(step, status, message, p)

  // 更新统计数据
  updateStatsFromEvent(event, p)

  // 处理决策透明化
  if (step === 'decision' && data.selected_button) {
    currentDecision.value = {
      candidates: data.candidates || [],
      selected: data.selected_button,
      score: data.score
    }
  }

  // 处理登录失败（Cookie失效等）
  if (step === 'login' && status === 'failed') {
    const errorMsg = message || '登录失败'
    if (errorMsg.includes('Cookie') || errorMsg.includes('cookie')) {
      // Cookie失效，自动触发手机验证
      forcePhoneLogin.value.required = true
      forcePhoneLogin.value.phone = ''
      forcePhoneLogin.value.code = ''
      forcePhoneLogin.value.code_sent = false
      forcePhoneLogin.value.verified = false
      forcePhoneLogin.value.message = `Cookie失效: ${errorMsg}，请使用手机验证码登录`

      if (forceLoginPollInterval) {
        clearInterval(forceLoginPollInterval)
      }
      forceLoginPollInterval = setInterval(checkForcePhoneLoginStatus, 2000)
    }
  }

  // 处理手机登录验证
  if (step === 'phone_login_required' && status === 'running') {
    console.log('[手机验证] 设置面板显示')
    // 显示强制验证面板
    forcePhoneLogin.value.required = true
    alert('手机验证面板已显示!')
    forcePhoneLogin.value.phone = ''
    forcePhoneLogin.value.code = ''
    forcePhoneLogin.value.code_sent = false
    forcePhoneLogin.value.verified = false
    forcePhoneLogin.value.message = message || '请在下方输入手机号完成验证'

    // 开始轮询登录状态
    if (forceLoginPollInterval) {
      clearInterval(forceLoginPollInterval)
    }
    forceLoginPollInterval = setInterval(checkForcePhoneLoginStatus, 2000)
  }

  // V3.4 处理RiskScore更新
  if (step === 'risk_score' || data.riskScore !== undefined) {
    riskScore.value = data.score || data.riskScore || 0
    riskThreshold.value = data.threshold || 0.7
    consecutiveSuccess.value = data.consecutiveSuccess || 0
    riskFactors.value = data.factors || []
    showRiskGauge.value = true
  }

  // V3.4 处理人工干预请求
  if (step === 'human_intervention_required' && status === 'running') {
    humanIntervention.value = {
      visible: true,
      job: {
        title: data.job || '',
        company: data.company || '',
        url: data.job_url || ''
      },
      riskScore: data.risk_score || 0,
      threshold: data.threshold || 0.7,
      reason: data.reason || '检测到高风险操作',
      factors: data.factors || [],
      logs: platformStates[p].executionLogs.slice(-5)
    }
  }

  // V3.4 处理人工干预完成
  if (step === 'human_intervention_completed' || step === 'phone_login_completed') {
    humanIntervention.value.visible = false
  }

  // 处理手机登录完成
  if (step === 'phone_login_completed' && status === 'success') {
    // 隐藏强制验证面板
    forcePhoneLogin.value.required = false
    forcePhoneLogin.value.verified = true
    if (forceLoginPollInterval) {
      clearInterval(forceLoginPollInterval)
      forceLoginPollInterval = null
    }
  }

  // 处理手机登录失败
  if (step === 'phone_login_failed' && status === 'failed') {
    forcePhoneLogin.value.message = message || '手机验证失败'
  }

  // 处理失败
  if (status === 'failed') {
    platformStates[p].failureReasons.push(`${getStepDisplayName(step)}: ${message}`)
  }

  // 处理成功投递
  if (step === 'apply_success') {
    currentDecision.value = null  // 清除决策面板
  }

  // 检查是否完成
  if (step === 'complete') {
    platformStates[p].running = false
    if (platformStates[p].eventSource) {
      platformStates[p].eventSource.close()
      platformStates[p].eventSource = null
    }
    // 停止手机验证轮询
    if (forceLoginPollInterval) {
      clearInterval(forceLoginPollInterval)
      forceLoginPollInterval = null
    }
    forcePhoneLogin.value.required = false
    // 刷新推荐列表
    fetchRecommendations()
  }
}

function addExecutionLog(step, status, message, platform = null) {
  const p = platform || currentPlatform.value
  const now = new Date()
  const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`

  platformStates[p].executionLogs.push({
    time,
    step: getStepDisplayName(step),
    status,
    message
  })

  // 滚动到底部
  nextTick(() => {
    const logRef = platformLogListRefs[p]?.value
    if (logRef) {
      logRef.scrollTop = logRef.scrollHeight
    }
  })
}

function getStepDisplayName(step) {
  const stepNames = {
    'login': '登录',
    'search': '搜索',
    'filter': '过滤',
    'open_detail': '打开详情页',
    'vision': 'Vision分析',
    'embedding': 'Embedding匹配',
    'decision': '决策',
    'click': '点击执行',
    'verify': '验证',
    'apply_start': '开始投递',
    'apply_success': '投递成功',
    'apply_failed': '投递失败',
    'complete': '完成'
  }
  return stepNames[step] || step
}

function updateStepStatus(step, status, message, platform = null) {
  const p = platform || currentPlatform.value
  // V3.3 完整流程步骤映射
  const stepMapping = {
    // 主流程
    'login': 0,
    'search': 1,
    'filter': 2,
    // 投递子流程
    'open_detail': 3,
    'vision': 4,
    'embedding': 5,
    'decision': 5,
    'click': 6,
    'apply_start': 6,
    'apply_success': 7,
    'apply_failed': 6,
    'verify': 7,
    'complete': 7
  }

  const stepIndex = stepMapping[step]
  if (stepIndex !== undefined && platformStates[p].executionSteps[stepIndex]) {
    platformStates[p].executionSteps[stepIndex].status = status === 'success' ? 'success' : status === 'failed' ? 'failed' : status === 'running' ? 'running' : 'pending'
    platformStates[p].executionSteps[stepIndex].message = message
  }
}

function updateStatsFromEvent(event, platform = null) {
  const p = platform || currentPlatform.value
  if (event.step === 'search' && event.status === 'success') {
    if (event.data && event.data.count) {
      platformStates[p].runningStats.jobsFound = event.data.count
    }
  }
  if (event.step === 'filter' && event.status === 'success') {
    if (event.data && event.data.count) {
      platformStates[p].runningStats.jobsFiltered = event.data.count
    }
  }
  if (event.step === 'apply_success') {
    platformStates[p].runningStats.applicationsSubmitted++
    // 更新投递进度
    const total = platformStates[p].runningStats.jobsFiltered || platformStates[p].runningStats.jobsMatched || 1
    progressPercent.value = Math.round((platformStates[p].runningStats.applicationsSubmitted / total) * 100)
    currentStep.value = `已投递 ${platformStates[p].runningStats.applicationsSubmitted}/${total} 个职位`
  }
  if (event.step === 'apply_failed') {
    platformStates[p].runningStats.applicationsFailed++
  }
}

const platformLogListRefs = reactive({
  zhilian: ref(null),
  job51: ref(null),
  boss: ref(null)
})

async function pollTaskResult(taskId, callback) {
  const maxRetries = 60
  const interval = 2000

  for (let i = 0; i < maxRetries; i++) {
    try {
      const task = await api.get(`/api/tasks/${taskId}`)
      console.log(`轮询任务 ${taskId} 状态:`, task.status)

      if (callback) {
        callback(task)
      }

      if (task.status === 'COMPLETED' || task.status === 'FAILED') {
        return task
      }

      await new Promise(resolve => setTimeout(resolve, interval))
    } catch (e) {
      console.error('轮询任务状态失败:', e)
    }
  }
  return null
}

function updateRunningStats(task) {
  if (task.result_data) {
    const data = typeof task.result_data === 'string'
      ? JSON.parse(task.result_data)
      : task.result_data

    // 更新登录用户名
    if (data.username) {
      loggedInUsername.value = data.username
      currentStep.value = `登录成功: ${data.username}`
    }

    // 更新投递统计
    if (data.applied_count !== undefined) {
      runningStats.value.applicationsSubmitted = data.applied_count
      currentStep.value = `已投递 ${data.applied_count} 个职位`
    }
    if (data.jobs_found !== undefined) {
      runningStats.value.jobsFound = data.jobs_found
    }
    if (data.jobs_matched !== undefined) {
      runningStats.value.jobsFiltered = data.jobs_matched
    }
  }

  // 更新进度
  if (task.status === 'COMPLETED') {
    progressPercent.value = 100
    currentStep.value = '任务完成'
    running.value = false
    // 刷新推荐列表
    fetchRecommendations()
  } else if (task.status === 'FAILED') {
    progressPercent.value = 0
    currentStep.value = '任务失败'
    running.value = false
  }
}

function setSchedule() {
  alert('定时任务功能开发中')
}

onMounted(async () => {
  const token = localStorage.getItem('token')
  if (!token) {
    router.push('/login')
    return
  }
  await loadPlatformCookies()
  await fetchStats()
  await fetchRecommendations()
  await fetchAnalyticsData()

  // 检查是否有正在运行的任务，如果有则重新连接 SSE
  await checkAndReconnectRunningTask()
})

// 检查并重新连接正在运行的任务
async function checkAndReconnectRunningTask() {
  try {
    const userId = localStorage.getItem('user_id') || 1
    const res = await api.get(`/api/tasks/user/${userId}?limit=10`)
    if (res && res.length > 0) {
      // 找到最新且状态为 running 的任务（但必须是最近30分钟内的，防止重连到僵尸任务）
      const thirtyMinsAgo = new Date(Date.now() - 30 * 60 * 1000).toISOString()
      const runningTask = res.find(t =>
        t.status === 'running' &&
        t.created_at &&
        t.created_at > thirtyMinsAgo
      )
      if (runningTask) {
        console.log('发现正在运行的任务:', runningTask.id, '，重新连接 SSE')
        running.value = true
        currentTaskId.value = runningTask.id
        // 重新获取历史步骤和连接 SSE
        await fetchHistorySteps(runningTask.id)
        connectToSSE(runningTask.id)
        return
      }
    }
    // 如果没有运行中的任务或任务太旧，重置状态
    console.log('没有找到最近运行的任务，重置状态')
    running.value = false
    currentTaskId.value = null
    resetExecutionState()
  } catch (e) {
    console.error('检查运行任务失败:', e)
  }
}

// 组件卸载时关闭 SSE 连接，防止内存泄漏
onUnmounted(() => {
  // 关闭所有平台的 SSE 连接
  for (const platform of Object.keys(platformStates)) {
    if (platformStates[platform].eventSource) {
      platformStates[platform].eventSource.close()
      platformStates[platform].eventSource = null
    }
  }
  console.log('Dashboard unmounted, all SSE connections closed')
})

async function loadPlatformCookies() {
  try {
    const userId = localStorage.getItem('user_id') || 1
    const userRes = await api.get(`/api/users/${userId}`)
    // API返回的数据结构是嵌套的: { profile: { platform_credentials: {...} } }
    const existingCreds = userRes.profile?.platform_credentials || {}

    // 更新各平台的Cookie
    for (const platformId of ['zhilian', 'boss', 'job51']) {
      const platformCred = existingCreds[platformId] || {}
      if (platformCred.cookie) {
        // 如果cookie是JSON字符串，尝试解析；如果是数组则stringify
        let cookieValue = platformCred.cookie
        if (typeof cookieValue === 'string') {
          try {
            const parsed = JSON.parse(cookieValue)
            if (Array.isArray(parsed)) {
              // 是JSON数组字符串，保持原样显示
              cookieValue = cookieValue
            }
          } catch (e) {
            // 不是JSON，保持原样
          }
        }
        platformCookies.value[platformId] = cookieValue
      }
    }

    // 检查当前平台的Cookie是否有效
    const currentCookie = platformCookies.value[currentPlatform.value]
    if (currentCookie && currentCookie.length > 10) {
      cookieStatus.value = 'valid'
    }
  } catch (e) {
    console.error('获取平台Cookie失败:', e)
  }
}

// V3.4 人工干预处理
async function handleHumanIntervention(action) {
  const { action: act, params } = action

  try {
    if (act === 'confirm') {
      // 用户确认继续执行
      const userId = localStorage.getItem('user_id') || 1
      await api.submitHumanAction(humanIntervention.value.itemId || 0, 'confirm')
      humanIntervention.value.visible = false
    } else if (act === 'skip') {
      // 用户跳过
      await api.submitHumanAction(humanIntervention.value.itemId || 0, 'skip')
      humanIntervention.value.visible = false
    } else if (act === 'modify') {
      // 用户修改参数
      await api.submitHumanAction(humanIntervention.value.itemId || 0, 'modify', params)
      humanIntervention.value.visible = false
    }
  } catch (e) {
    console.error('人工干预处理失败:', e)
  }
}
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  background: #f5f5f5;
}

.content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: 28px;
  color: #333;
  margin: 0;
}

.welcome {
  color: #666;
  margin-top: 4px;
}

/* Tabs */
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  border-bottom: 1px solid #eee;
  padding-bottom: 12px;
}

.tab-btn {
  padding: 10px 20px;
  border: none;
  background: transparent;
  color: #666;
  font-size: 15px;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s;
}

.tab-btn:hover {
  background: #f0f0f0;
}

.tab-btn.active {
  background: #007bff;
  color: white;
}

.tab-content {
  margin-bottom: 24px;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.stat-icon {
  font-size: 32px;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #333;
}

.stat-label {
  font-size: 14px;
  color: #666;
}

/* Job Feed */
.job-feed-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h3 {
  font-size: 18px;
  margin: 0;
}

.refresh-btn {
  padding: 6px 12px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

.refresh-btn:hover {
  background: #f5f5f5;
}

/* Applications Table */
.applications-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
}

.applications-table table {
  width: 100%;
  border-collapse: collapse;
}

.applications-table th,
.applications-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.applications-table th {
  font-weight: 600;
  color: #666;
  font-size: 13px;
}

.status-tag {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.status-tag.submitted {
  background: #e6f7e6;
  color: #52c41a;
}

.status-tag.failed {
  background: #fff2f0;
  color: #ff4d4f;
}

.pagination {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
}

.pagination button {
  padding: 6px 12px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 6px;
  cursor: pointer;
}

/* Analytics */
.analytics-section {
  margin-bottom: 24px;
}

/* V3.3 Overview */
.v33-overview {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
}

.v33-overview h3 {
  font-size: 16px;
  margin: 0 0 16px 0;
  color: #333;
}

.v33-flow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.flow-step {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #f8f9fa;
  border-radius: 8px;
  flex: 1;
  min-width: 140px;
}

.flow-icon {
  font-size: 28px;
}

.flow-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.flow-name {
  font-weight: 600;
  font-size: 14px;
  color: #333;
}

.flow-desc {
  font-size: 11px;
  color: #999;
}

.flow-status {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  margin-top: 4px;
  display: inline-block;
}

.flow-status.active {
  background: #e6f7e6;
  color: #52c41a;
}

.flow-status.standby {
  background: #f5f5f5;
  color: #999;
}

.flow-arrow {
  font-size: 20px;
  color: #ccc;
}

/* Stats Overview */
.stats-overview {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.stat-card .stat-icon {
  font-size: 32px;
}

.stat-card .stat-info {
  display: flex;
  flex-direction: column;
}

.stat-card.success {
  border-left: 4px solid #52c41a;
}

/* Task History */
.task-history-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
}

.task-history-section h3 {
  font-size: 16px;
  margin: 0 0 16px 0;
  color: #333;
}

.task-history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-history-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  font-size: 13px;
}

.task-id {
  font-weight: 600;
  color: #666;
  min-width: 40px;
}

.task-status .status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.status-badge.completed {
  background: #e6f7e6;
  color: #52c41a;
}

.status-badge.failed {
  background: #fff2f0;
  color: #ff4d4f;
}

.status-badge.running {
  background: #e6f7ff;
  color: #1890ff;
}

.task-stats {
  display: flex;
  gap: 12px;
  flex: 1;
}

.task-stat {
  color: #666;
}

.task-stat.success {
  color: #52c41a;
}

.task-stat.failed {
  color: #ff4d4f;
}

.task-time {
  color: #999;
  font-size: 12px;
}

/* Empty Analytics */
.empty-analytics {
  background: white;
  border-radius: 12px;
  padding: 48px;
  text-align: center;
  margin-bottom: 24px;
}

.empty-analytics .empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-analytics .empty-text {
  font-size: 16px;
  color: #333;
  margin-bottom: 8px;
}

.empty-analytics .empty-hint {
  font-size: 14px;
  color: #999;
  margin-bottom: 20px;
}

/* Companies List */
.companies-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
}

.companies-section h3 {
  font-size: 16px;
  margin: 0 0 16px 0;
  color: #333;
}

.companies-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.company-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
}

.company-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.company-stats {
  display: flex;
  gap: 8px;
  font-size: 12px;
}

.company-count {
  color: #666;
}

.company-rate.success {
  color: #52c41a;
  font-weight: 600;
}

/* Engine Models */
.engine-models-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
}

.engine-models-section h3 {
  font-size: 16px;
  margin: 0 0 16px 0;
  color: #333;
}

.models-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.model-card {
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #1890ff;
}

.model-name {
  font-size: 13px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.model-value {
  font-size: 12px;
  color: #1890ff;
  font-family: monospace;
  margin-bottom: 4px;
}

.model-desc {
  font-size: 11px;
  color: #999;
}

.companies-section,
.engine-status-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
}

.companies-section h3,
.engine-status-section h3 {
  font-size: 16px;
  margin-bottom: 16px;
}

/* Credentials */
.credentials-section {
  margin-bottom: 24px;
}

.credentials-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
}

.credentials-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

/* Platform Tabs */
.platform-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  border-bottom: 1px solid #eee;
  padding-bottom: 12px;
}

.platform-tab {
  padding: 8px 16px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}

.platform-tab:hover {
  background: #f5f5f5;
}

.platform-tab.active {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

.platform-tab .tab-status {
  font-size: 12px;
}

.platform-tab .tab-status.running {
  color: #1890ff;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.platform-tab .tab-status.valid {
  color: #52c41a;
}

.platform-tab .tab-status.invalid {
  color: #ff4d4f;
}

.platform-tab .tab-status.unknown {
  color: #999;
}

.platform-tab.active .tab-status {
  color: white;
}

.platform-config {
  /* 平台配置区域 */
}

.platform-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.platform-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.credentials-header h3 {
  font-size: 16px;
  margin: 0;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.status-badge.valid {
  background: #e6f7e6;
  color: #52c41a;
}

.status-badge.invalid {
  background: #fff2f0;
  color: #ff4d4f;
}

.status-badge.unknown {
  background: #f5f5f5;
  color: #666;
}

.username-badge {
  padding: 4px 12px;
  background: #e6f7e6;
  color: #52c41a;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  margin-left: 12px;
}

.cookie-warning {
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}

.cookie-warning p {
  margin: 0 0 8px 0;
  color: #856404;
  font-size: 13px;
}

.phone-verify-btn {
  width: 100%;
  padding: 10px;
  background: linear-gradient(135deg, #ff6b6b 0%, #ff4757 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

.phone-verify-btn:hover {
  opacity: 0.9;
}

.cookie-input {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.cookie-input textarea {
  flex: 1;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 13px;
  font-family: monospace;
}

.save-cookie-btn {
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.save-cookie-btn:disabled {
  background: #ccc;
}

.helper-text {
  font-size: 12px;
  color: #999;
  margin-top: 8px;
}

/* 强制手机验证内联面板 */
.force-phone-login-inline {
  background: linear-gradient(135deg, #ff6b6b 0%, #ff4757 100%);
  border-radius: 8px;
  padding: 12px;
  color: white;
  margin-bottom: 12px;
}

.force-phone-login-inline .force-phone-login-header {
  margin-bottom: 10px;
}

.force-phone-login-inline .force-phone-login-header h4 {
  margin: 0 0 4px 0;
  font-size: 14px;
}

.force-phone-login-inline .force-phone-login-header p {
  margin: 0;
  font-size: 12px;
  opacity: 0.9;
}

.force-phone-login-inline .phone-input-row,
.force-phone-login-inline .code-input-row {
  display: flex;
  gap: 8px;
}

.force-phone-login-inline input {
  flex: 1;
  padding: 8px 10px;
  border: none;
  border-radius: 4px;
  font-size: 13px;
}

.force-phone-login-inline .send-code-btn {
  padding: 8px 12px;
  background: white;
  color: #ff4757;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}

.force-phone-login-inline .verify-code-btn {
  padding: 8px 12px;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}

.force-phone-login-inline .force-phone-success {
  margin-top: 8px;
  font-size: 13px;
}

/* Phone Input */
.phone-input-row {
  display: flex;
  gap: 8px;
}

.phone-input-row input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.code-input-row {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.code-input-row input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  letter-spacing: 4px;
}

.send-code-btn {
  padding: 8px 16px;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
}

.send-code-btn:disabled {
  background: #ccc;
}

.send-code-btn:hover:not(:disabled) {
  background: #218838;
}

/* Actions */
.actions-section {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.action-btn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  cursor: pointer;
}

.action-btn.primary {
  background: #007bff;
  color: white;
}

.action-btn.secondary {
  background: white;
  border: 1px solid #ddd;
}

.action-btn.login-btn {
  background: linear-gradient(135deg, #52c41a, #389e0d);
  color: white;
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Running */
.running-section {
  margin-bottom: 24px;
}

.running-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
}

.running-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.progress-bar {
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #007bff;
  transition: width 0.3s;
}

.running-stats {
  display: flex;
  gap: 24px;
  margin-top: 16px;
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 48px;
  color: #999;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-text {
  font-size: 16px;
  margin-bottom: 8px;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 32px;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .stats-grid,
  .stats-overview {
    grid-template-columns: 1fr;
  }
  .charts-row {
    grid-template-columns: 1fr;
  }
  .tabs {
    flex-wrap: wrap;
  }
}

/* Agent 执行可视化 */
.step-flow {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.step-flow h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #333;
}

.step-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: white;
  border-radius: 20px;
  font-size: 13px;
  border: 2px solid #e0e0e0;
  transition: all 0.3s;
}

.step-item.success {
  border-color: #52c41a;
  background: #f6ffed;
}

.step-item.failed {
  border-color: #ff4d4f;
  background: #fff2f0;
}

.step-item.running {
  border-color: #1890ff;
  background: #e6f7ff;
}

.step-icon {
  font-size: 14px;
}

.step-name {
  font-weight: 500;
  color: #333;
}

.step-message {
  font-size: 12px;
  color: #666;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 实时日志 */
.realtime-logs {
  background: #1a1a2e;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  max-height: 300px;
  overflow: hidden;
}

/* 决策透明化面板 */
.decision-panel {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  border-left: 4px solid #1890ff;
}

.decision-panel h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #333;
}

.decision-content {
  display: flex;
  gap: 16px;
}

.decision-candidates {
  flex: 1;
}

.candidate-header {
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
}

.candidate-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 10px;
  background: white;
  border-radius: 6px;
  margin-bottom: 4px;
  font-size: 13px;
  border: 1px solid #eee;
}

.candidate-item.selected {
  background: #e6f7ff;
  border-color: #1890ff;
  font-weight: 600;
}

.candidate-name {
  color: #333;
}

.candidate-score {
  color: #666;
}

.candidate-item.selected .candidate-score {
  color: #1890ff;
}

.decision-result {
  min-width: 200px;
  display: flex;
  align-items: center;
}

.decision-selected {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.decision-selected .label {
  font-size: 12px;
  color: #666;
}

.decision-selected .value {
  font-size: 16px;
  font-weight: 600;
  color: #52c41a;
}

.decision-selected .score {
  font-size: 12px;
  color: #52c41a;
}

.realtime-logs h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #fff;
}

.log-list {
  max-height: 240px;
  overflow-y: auto;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
}

.log-item {
  display: flex;
  gap: 8px;
  padding: 4px 0;
  color: #a0a0a0;
  border-bottom: 1px solid #2a2a3e;
}

.log-item:last-child {
  border-bottom: none;
}

.log-item.success {
  color: #52c41a;
}

.log-item.failed {
  color: #ff4d4f;
}

.log-item.running {
  color: #1890ff;
}

.log-time {
  color: #666;
  flex-shrink: 0;
}

.log-step {
  color: #8b5cf6;
  flex-shrink: 0;
  min-width: 60px;
}

.log-message {
  color: inherit;
  word-break: break-all;
}

/* 失败原因面板 */
.failure-panel {
  background: #fff2f0;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid #ffccc7;
}

.failure-panel h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #ff4d4f;
}

.failure-list {
  margin: 0;
  padding-left: 20px;
}

.failure-list li {
  color: #ff4d4f;
  font-size: 13px;
  margin-bottom: 4px;
}

/* 统计项增加失败计数 */
.running-stats .stat-item .stat-value.failed {
  color: #ff4d4f;
}
</style>
