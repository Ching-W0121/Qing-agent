<template>
  <div class="analytics-view">
    <header class="page-header">
      <h2>数据分析</h2>
    </header>

    <!-- Success Rate Overview -->
    <section class="stats-overview">
      <div class="stat-card">
        <span class="stat-value">{{ totalApplies }}</span>
        <span class="stat-label">总投递数</span>
      </div>
      <div class="stat-card success">
        <span class="stat-value">{{ successRate }}%</span>
        <span class="stat-label">成功率</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ totalCompanies }}</span>
        <span class="stat-label">投递公司数</span>
      </div>
    </section>

    <!-- Charts Row -->
    <section class="charts-row">
      <div class="chart-card">
        <SuccessRateChart :data="successTrendData" />
      </div>
      <div class="chart-card">
        <FailureReasonChart :data="failureReasonsData" />
      </div>
    </section>

    <!-- High Success Companies -->
    <section class="companies-section">
      <h3>成功率最高的 TOP 公司</h3>
      <HighSuccessCompanies :companies="topCompanies" />
    </section>

    <!-- Engine Status -->
    <section class="engine-status-section">
      <h3>引擎状态</h3>
      <EngineStatus
        :visionStatus="engineStatus.vision"
        :embeddingStatus="engineStatus.embedding"
        :recoveryStatus="engineStatus.recovery"
        :learningStatus="engineStatus.learning"
      />
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import SuccessRateChart from '@/components/SuccessRateChart.vue'
import FailureReasonChart from '@/components/FailureReasonChart.vue'
import EngineStatus from '@/components/EngineStatus.vue'
import HighSuccessCompanies from '@/components/HighSuccessCompanies.vue'
import api from '@/api'

const router = useRouter()

// Loading state
const loading = ref(false)
const error = ref(null)

// Analytics data
const analyticsData = ref({
  total_applies: 0,
  success_rate: 0,
  total_companies: 0,
  success_trend: [],
  failure_reasons: [],
  top_companies: []
})

// Computed properties for display
const totalApplies = computed(() => analyticsData.value.total_applies || 0)
const successRate = computed(() => {
  const rate = analyticsData.value.success_rate
  return typeof rate === 'number' ? rate.toFixed(1) : '0.0'
})
const totalCompanies = computed(() => analyticsData.value.total_companies || 0)

// Chart data - transform API response to chart component format
const successTrendData = computed(() => {
  return analyticsData.value.success_trend.map(item => ({
    date: formatDate(item.date),
    rate: item.rate
  }))
})

const failureReasonsData = computed(() => {
  return analyticsData.value.failure_reasons.map(item => ({
    name: item.name,
    count: item.count,
    color: item.color || getDefaultColor(item.name)
  }))
})

// Top companies - limit to top 10
const topCompanies = computed(() => {
  return (analyticsData.value.top_companies || [])
    .slice(0, 10)
    .map(company => ({
      name: company.name,
      applyCount: company.apply_count,
      successRate: company.success_rate
    }))
})

// Engine status - mock data, should come from backend
const engineStatus = ref({
  vision: 'STANDBY',
  embedding: 'STANDBY',
  recovery: 'STANDBY',
  learning: 'STANDBY'
})

/**
 * Format date string for display
 * @param {string} dateStr - ISO date string
 * @returns {string} Formatted date (MM-DD)
 */
function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${month}-${day}`
}

/**
 * Get default color for failure reason
 * @param {string} reasonName - Failure reason name
 * @returns {string} Hex color code
 */
function getDefaultColor(reasonName) {
  const colorMap = {
    '登录失效': '#ff4d4f',
    '弹窗拦截': '#faad14',
    '验证码': '#1677ff',
    '未知错误': '#999'
  }
  return colorMap[reasonName] || '#999'
}

/**
 * Fetch analytics data from backend
 */
async function fetchAnalyticsData() {
  loading.value = true
  error.value = null

  try {
    const userId = localStorage.getItem('user_id') || 1

    // Fetch analytics data
    const data = await api.get(`/api/applications/user/${userId}/analytics`)
    analyticsData.value = {
      total_applies: data.total_applies || 0,
      success_rate: data.success_rate || 0,
      total_companies: data.total_companies || 0,
      success_trend: data.success_trend || [],
      failure_reasons: data.failure_reasons || [],
      top_companies: data.top_companies || []
    }

    // Fetch engine status if available
    try {
      const statusRes = await api.get('/api/engine/status')
      if (statusRes) {
        engineStatus.value = {
          vision: statusRes.vision || 'STANDBY',
          embedding: statusRes.embedding || 'STANDBY',
          recovery: statusRes.recovery || 'STANDBY',
          learning: statusRes.learning || 'STANDBY'
        }
      }
    } catch (statusError) {
      console.log('Engine status not available, using default:', statusError)
    }
  } catch (err) {
    console.error('Failed to fetch analytics data:', err)

    // Handle 404 - show empty state gracefully
    if (err.response?.status === 404) {
      error.value = '暂无数据'
      analyticsData.value = {
        total_applies: 0,
        success_rate: 0,
        total_companies: 0,
        success_trend: [],
        failure_reasons: [],
        top_companies: []
      }
    } else {
      error.value = '获取数据失败'
    }
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  const token = localStorage.getItem('token')
  if (!token) {
    router.push('/login')
    return
  }

  await fetchAnalyticsData()
})
</script>

<style scoped>
.analytics-view {
  min-height: 100vh;
  background: #f5f5f5;
  padding: 24px;
}

.page-header {
  margin-bottom: 32px;
}

.page-header h2 {
  font-size: 28px;
  color: #333;
  margin: 0;
}

/* Stats Overview */
.stats-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-card.success {
  background: linear-gradient(135deg, #52c41a 0%, #73d13d 100%);
}

.stat-card.success .stat-value,
.stat-card.success .stat-label {
  color: white;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  color: #333;
}

.stat-label {
  font-size: 14px;
  color: #666;
}

/* Charts Row */
.charts-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}

.chart-card {
  min-width: 0;
}

.chart-card :deep(.chart-container) {
  height: 300px;
}

/* Companies Section */
.companies-section {
  margin-bottom: 32px;
}

.companies-section h3 {
  font-size: 18px;
  color: #333;
  margin-bottom: 16px;
  font-weight: 500;
}

/* Engine Status Section */
.engine-status-section {
  margin-bottom: 24px;
}

.engine-status-section h3 {
  font-size: 18px;
  color: #333;
  margin-bottom: 16px;
  font-weight: 500;
}

/* Responsive */
@media (max-width: 900px) {
  .charts-row {
    grid-template-columns: 1fr;
  }

  .chart-card :deep(.chart-container) {
    height: 280px;
  }
}

@media (max-width: 640px) {
  .analytics-view {
    padding: 16px;
  }

  .page-header h2 {
    font-size: 24px;
  }

  .stats-overview {
    grid-template-columns: 1fr;
  }

  .stat-card {
    padding: 20px;
  }

  .stat-value {
    font-size: 32px;
  }

  .chart-card :deep(.chart-container) {
    height: 250px;
  }
}
</style>
