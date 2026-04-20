<template>
  <div class="risk-gauge" :class="riskLevel">
    <div class="gauge-header">
      <span class="gauge-title">RiskScore 风险评估</span>
      <span class="consecutive-info">
        连续成功: <strong>{{ consecutiveSuccess }}</strong> 次
      </span>
    </div>

    <div class="gauge-container">
      <div class="gauge-bar-wrapper">
        <div class="gauge-bar">
          <div
            class="gauge-fill"
            :style="{ width: `${score * 100}%` }"
            :class="riskLevel"
          ></div>
          <div
            class="threshold-marker"
            :style="{ left: `${threshold * 100}%` }"
            :title="`阈值: ${(threshold * 100).toFixed(0)}%`"
          ></div>
        </div>
        <div class="gauge-value" :class="riskLevel">
          {{ (score * 100).toFixed(0) }}%
        </div>
      </div>

      <div class="gauge-labels">
        <span class="threshold-label">阈值: {{ (threshold * 100).toFixed(0) }}%</span>
        <span class="level-badge" :class="riskLevel">
          {{ riskLabel }}
        </span>
      </div>
    </div>

    <div v-if="factors.length > 0" class="risk-factors">
      <div class="factors-title">风险因素:</div>
      <div class="factors-list">
        <span
          v-for="(factor, index) in factors"
          :key="index"
          class="factor-tag"
          :class="factor.type"
        >
          {{ getFactorLabel(factor.type) }}: +{{ (factor.weight * 100).toFixed(0) }}%
        </span>
      </div>
    </div>

    <div class="gauge-footer">
      <div class="action-hint" :class="actionClass">
        {{ actionHint }}
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RiskScoreGauge',
  props: {
    score: {
      type: Number,
      default: 0
    },
    threshold: {
      type: Number,
      default: 0.7
    },
    consecutiveSuccess: {
      type: Number,
      default: 0
    },
    factors: {
      type: Array,
      default: () => []
    }
  },
  computed: {
    riskLevel() {
      if (this.score > this.threshold) return 'high'
      if (this.score > this.threshold * 0.6) return 'medium'
      return 'low'
    },
    riskLabel() {
      const labels = {
        low: '低风险',
        medium: '中风险',
        high: '高风险'
      }
      return labels[this.riskLevel] || '未知'
    },
    actionHint() {
      if (this.riskLevel === 'high') return '⚠️ 等待人工确认'
      if (this.riskLevel === 'medium') return '🔧 自动尝试恢复'
      return '✅ 自动继续'
    },
    actionClass() {
      return {
        'action-high': this.riskLevel === 'high',
        'action-medium': this.riskLevel === 'medium',
        'action-low': this.riskLevel === 'low'
      }
    }
  },
  methods: {
    getFactorLabel(type) {
      const labels = {
        login_required: '需要登录',
        captcha: '验证码',
        popup: '弹窗',
        job_detail: '职位详情',
        consecutive_fail: '连续失败',
        high_frequency: '高频操作',
        medium_frequency: '中频操作',
        error_keywords: '错误关键词',
        captcha_detected: '验证码检测',
        url_redirect: 'URL跳转'
      }
      return labels[type] || type
    }
  }
}
</script>

<style scoped>
.risk-gauge {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.3s ease;
}

.risk-gauge.high {
  background: linear-gradient(135deg, #fff5f5 0%, #ffe0e0 100%);
  border: 2px solid #dc3545;
}
.risk-gauge.medium {
  background: linear-gradient(135deg, #fffbf0 0%, #fff3d6 100%);
  border: 2px solid #ffc107;
}
.risk-gauge.low {
  background: linear-gradient(135deg, #f0fff4 0%, #d4edda 100%);
  border: 2px solid #28a745;
}

.gauge-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.gauge-title {
  font-weight: 600;
  font-size: 14px;
  color: #343a40;
}

.consecutive-info {
  font-size: 12px;
  color: #6c757d;
}

.gauge-container {
  margin-bottom: 12px;
}

.gauge-bar-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.gauge-bar {
  flex: 1;
  height: 24px;
  background: #dee2e6;
  border-radius: 12px;
  position: relative;
  overflow: hidden;
}

.gauge-fill {
  height: 100%;
  border-radius: 12px;
  transition: width 0.5s ease;
}
.gauge-fill.low { background: linear-gradient(90deg, #28a745, #20c997); }
.gauge-fill.medium { background: linear-gradient(90deg, #ffc107, #fd7e14); }
.gauge-fill.high { background: linear-gradient(90deg, #dc3545, #c82333); }

.threshold-marker {
  position: absolute;
  top: 0;
  width: 3px;
  height: 100%;
  background: #343a40;
  border-radius: 2px;
}

.gauge-value {
  font-size: 18px;
  font-weight: 700;
  min-width: 50px;
  text-align: right;
}
.gauge-value.low { color: #28a745; }
.gauge-value.medium { color: #ffc107; }
.gauge-value.high { color: #dc3545; }

.gauge-labels {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}

.threshold-label {
  font-size: 12px;
  color: #6c757d;
}

.level-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}
.level-badge.low { background: #28a745; color: white; }
.level-badge.medium { background: #ffc107; color: #343a40; }
.level-badge.high { background: #dc3545; color: white; }

.risk-factors {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #dee2e6;
}

.factors-title {
  font-size: 12px;
  color: #6c757d;
  margin-bottom: 8px;
}

.factors-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.factor-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  background: #e9ecef;
  color: #495057;
}

.factor-tag.captcha,
.factor-tag.captcha_detected {
  background: #fff3cd;
  color: #856404;
}

.factor-tag.consecutive_fail {
  background: #f8d7da;
  color: #721c24;
}

.gauge-footer {
  margin-top: 12px;
}

.action-hint {
  font-size: 12px;
  text-align: center;
  padding: 6px 12px;
  border-radius: 6px;
}
.action-hint.action-low { background: #d4edda; color: #155724; }
.action-hint.action-medium { background: #fff3cd; color: #856404; }
.action-hint.action-high { background: #f8d7da; color: #721c24; }
</style>
