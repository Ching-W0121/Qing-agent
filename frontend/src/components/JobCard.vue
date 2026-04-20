<template>
  <div class="job-card" :class="{ 'is-applied': job.is_applied }">
    <!-- 新职位标记 -->
    <div v-if="job.is_new" class="new-badge">新</div>

    <div class="job-header">
      <h3 class="job-title">{{ job.title }}</h3>
      <div class="match-score-wrapper">
        <span class="match-score" :class="scoreClass">{{ job.match_score }}%</span>
        <span class="match-label">匹配度</span>
      </div>
    </div>

    <div class="company-name">
      <span class="company-icon">🏢</span>
      {{ job.company }}
    </div>

    <div class="job-info">
      <span class="salary">
        <span class="icon">💰</span>
        {{ job.salary }}
      </span>
      <span class="location">
        <span class="icon">📍</span>
        {{ job.city }} {{ job.area || '' }}
      </span>
      <span v-if="job.publish_time" class="publish-time">
        <span class="icon">⏰</span>
        {{ formatPublishTime(job.publish_time) }}
      </span>
    </div>

    <!-- V3.1: 推荐理由展示 -->
    <div class="match-reasons" v-if="job.match_reasons?.length">
      <div class="reasons-header">推荐理由</div>
      <div class="reason-tags">
        <span class="reason-tag" v-for="reason in job.match_reasons" :key="reason">
          {{ reason }}
        </span>
      </div>
    </div>

    <!-- V3.1: 分数构成详情 -->
    <div v-if="showScoreBreakdown && job.score_breakdown" class="score-breakdown">
      <div class="breakdown-header">评分构成</div>
      <div class="breakdown-bars">
        <div class="breakdown-item" v-for="(value, key) in job.score_breakdown" :key="key">
          <span class="breakdown-label">{{ scoreLabels[key] || key }}</span>
          <div class="breakdown-bar">
            <div class="breakdown-fill" :style="{ width: (value * 100) + '%' }"></div>
          </div>
          <span class="breakdown-value">{{ (value * 100).toFixed(0) }}%</span>
        </div>
      </div>
    </div>

    <!-- V3.1: 操作按钮 -->
    <div class="job-actions">
      <!-- 查看详情 - 记录click行为 -->
      <a
        :href="job.source_url"
        target="_blank"
        class="btn-detail"
        @click="handleAction('click')"
      >
        查看详情
      </a>

      <!-- 感兴趣 -->
      <button
        @click="handleAction('like')"
        class="btn-action btn-like"
        :class="{ active: job.is_liked }"
      >
        {{ job.is_liked ? '❤️ 已感兴趣' : '🤍 感兴趣' }}
      </button>

      <!-- 不感兴趣 -->
      <button
        @click="handleAction('dislike')"
        class="btn-action btn-dislike"
        :class="{ active: job.is_disliked }"
      >
        {{ job.is_disliked ? '💔 不感兴趣' : '👎 不感兴趣' }}
      </button>

      <!-- 投递按钮 -->
      <button
        @click="handleAction('apply')"
        class="btn-apply"
        :class="{ 'is-applied': job.is_applied }"
        :disabled="job.is_applied"
      >
        <span v-if="job.is_applied">✅ 已投递</span>
        <span v-else>📌 投递</span>
      </button>

      <!-- 查看推荐解释 -->
      <button
        v-if="showExplain"
        @click="showExplanation"
        class="btn-explain"
      >
        💡 为什么推荐
      </button>
    </div>

    <!-- V3.1: 推荐解释弹窗 -->
    <div v-if="explanation" class="explanation-popup">
      <div class="explanation-header">
        <h4>推荐理由</h4>
        <button @click="explanation = null" class="close-btn">×</button>
      </div>
      <div class="explanation-content">
        <div class="explanation-score">
          匹配度: <strong>{{ explanation.match_score }}%</strong>
        </div>
        <div class="explanation-reasons">
          <div v-for="reason in explanation.match_reasons" :key="reason" class="reason-item">
            ✓ {{ reason }}
          </div>
        </div>
        <div class="explanation-tip">
          <span class="tip-icon">💡</span>
          {{ explanation.recommendation_tip }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import api from '@/api'

const props = defineProps({
  job: Object,
  showScoreBreakdown: {
    type: Boolean,
    default: false
  },
  showExplain: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['action'])

const explanation = ref(null)

// V3.1: 分数标签映射
const scoreLabels = {
  'keyword': '关键词',
  'prefer_keyword': '加分词',
  'salary': '薪资',
  'city': '城市',
  'area': '区域',
  'industry': '行业',
  'time_decay': '新鲜度',
  'behavior': '行为反馈'
}

const scoreClass = computed(() => {
  if (props.job.match_score >= 80) return 'high'
  if (props.job.match_score >= 60) return 'medium'
  if (props.job.match_score >= 40) return 'low'
  return 'very-low'
})

const formatPublishTime = (publishTime) => {
  if (!publishTime) return ''
  const date = new Date(publishTime)
  const now = new Date()
  const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return '今天发布'
  if (diffDays === 1) return '昨天发布'
  if (diffDays < 7) return `${diffDays}天前发布`
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) + '发布'
}

const handleAction = (action) => {
  emit('action', { job_id: props.job.job_id, action })
}

const showExplanation = async () => {
  if (explanation.value) {
    explanation.value = null
    return
  }

  try {
    const res = await api.get(`/api/jobs/recommend/1/explain/${props.job.job_id}`)
    explanation.value = res
  } catch (e) {
    console.error('获取推荐解释失败:', e)
  }
}
</script>

<style scoped>
.job-card {
  background: white;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  position: relative;
  transition: all 0.3s ease;
}

.job-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
}

.job-card.is-applied {
  border-left: 4px solid #52c41a;
}

/* 新职位标记 */
.new-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  background: linear-gradient(135deg, #ff6b6b, #ee5a24);
  color: white;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: bold;
}

.job-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.job-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin: 0;
  flex: 1;
  padding-right: 60px;
}

.match-score-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 50px;
}

.match-score {
  padding: 4px 10px;
  border-radius: 16px;
  font-weight: bold;
  font-size: 14px;
}

.match-score.high { background: linear-gradient(135deg, #e6f7e6, #d4edda); color: #52c41a; }
.match-score.medium { background: linear-gradient(135deg, #fffbe6, #fff3cd); color: #faad14; }
.match-score.low { background: linear-gradient(135deg, #fff1f0, #ffccc7); color: #ff4d4f; }
.match-score.very-low { background: #f5f5f5; color: #999; }

.match-label {
  font-size: 10px;
  color: #999;
  margin-top: 2px;
}

.company-name {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.company-icon {
  font-size: 14px;
}

.job-info {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #666;
}

.job-info span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.icon {
  font-size: 12px;
}

.salary {
  color: #e65100;
  font-weight: 500;
}

/* 推荐理由 */
.match-reasons {
  margin-bottom: 12px;
}

.reasons-header {
  font-size: 12px;
  color: #999;
  margin-bottom: 6px;
}

.reason-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.reason-tag {
  background: linear-gradient(135deg, #e6f7ff, #bae7ff);
  color: #1890ff;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
  border: 1px solid #91d5ff;
}

/* 分数构成详情 */
.score-breakdown {
  background: #fafafa;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}

.breakdown-header {
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
}

.breakdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
}

.breakdown-label {
  min-width: 50px;
  color: #666;
}

.breakdown-bar {
  flex: 1;
  height: 6px;
  background: #e8e8e8;
  border-radius: 3px;
  overflow: hidden;
}

.breakdown-fill {
  height: 100%;
  background: linear-gradient(90deg, #1890ff, #52c41a);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.breakdown-value {
  min-width: 30px;
  color: #999;
  text-align: right;
}

/* 操作按钮 */
.job-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.job-actions a,
.job-actions button {
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
  border: none;
}

.btn-detail {
  background: #f0f5ff;
  color: #1890ff;
  border: 1px solid #91d5ff;
}

.btn-detail:hover {
  background: #e6f0ff;
}

.btn-action {
  background: #f5f5f5;
  color: #666;
}

.btn-action:hover {
  background: #eee;
}

.btn-like.active,
.btn-like:hover {
  background: #fff1f0;
  color: #ff4d4f;
}

.btn-dislike.active,
.btn-dislike:hover {
  background: #f5f5f5;
  color: #999;
}

.btn-apply {
  background: linear-gradient(135deg, #1890ff, #096dd9);
  color: white;
  font-weight: 500;
}

.btn-apply:hover:not(:disabled) {
  background: linear-gradient(135deg, #096dd9, #0050b3);
}

.btn-apply.is-applied,
.btn-apply:disabled {
  background: #d9d9d9;
  cursor: not-allowed;
}

.btn-explain {
  background: #fff7e6;
  color: #fa8c16;
  border: 1px solid #ffbb6b;
}

.btn-explain:hover {
  background: #fff1db;
}

/* 推荐解释弹窗 */
.explanation-popup {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.15);
  padding: 16px;
  margin-top: 8px;
  z-index: 100;
}

.explanation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.explanation-header h4 {
  margin: 0;
  font-size: 14px;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #999;
  cursor: pointer;
  line-height: 1;
}

.explanation-score {
  font-size: 14px;
  color: #666;
  margin-bottom: 12px;
}

.explanation-reasons {
  margin-bottom: 12px;
}

.reason-item {
  font-size: 13px;
  color: #52c41a;
  padding: 4px 0;
}

.explanation-tip {
  background: #f6ffed;
  border-radius: 8px;
  padding: 10px;
  font-size: 13px;
  color: #52c41a;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.tip-icon {
  flex-shrink: 0;
}
</style>
