<template>
  <Transition name="slide">
    <div v-if="visible" class="intervention-panel">
      <div class="panel-header" :class="riskLevel">
        <span class="warning-icon">⚠️</span>
        <span class="title">检测到高风险操作</span>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>

      <div class="panel-body">
        <div class="job-info">
          <div class="job-title">{{ job.title || '未知职位' }}</div>
          <div class="job-company">{{ job.company || '未知公司' }}</div>
          <div class="job-url">{{ job.url }}</div>
        </div>

        <div class="risk-summary">
          <div class="risk-score-display" :class="riskLevel">
            <span class="label">风险得分</span>
            <span class="value">{{ (riskScore * 100).toFixed(0) }}%</span>
          </div>
          <div class="risk-threshold">
            超过阈值 ({{ (threshold * 100).toFixed(0) }}%)
          </div>
          <div class="risk-reason" v-if="reason">
            {{ reason }}
          </div>
        </div>

        <div class="risk-factors" v-if="factors && factors.length > 0">
          <div class="factors-label">风险因素:</div>
          <div class="factors-tags">
            <span
              v-for="(factor, idx) in factors"
              :key="idx"
              class="factor-tag"
            >
              {{ factor.type }}: +{{ (factor.weight * 100).toFixed(0) }}%
            </span>
          </div>
        </div>

        <div class="action-buttons">
          <button class="btn btn-continue" @click="onConfirm">
            <span class="btn-icon">▶️</span>
            <span class="btn-label">继续执行</span>
            <span class="btn-desc">确认风险，继续投递</span>
          </button>

          <button class="btn btn-skip" @click="onSkip">
            <span class="btn-icon">⏭️</span>
            <span class="btn-label">跳过此职位</span>
            <span class="btn-desc">跳过并记录为已放弃</span>
          </button>

          <button class="btn btn-modify" @click="showModifyForm = !showModifyForm">
            <span class="btn-icon">⚙️</span>
            <span class="btn-label">调整参数重试</span>
            <span class="btn-desc">修改等待时间/点击方式</span>
          </button>
        </div>

        <div v-if="showModifyForm" class="modify-form">
          <div class="form-header">
            <span>调整参数</span>
            <button class="close-form" @click="showModifyForm = false">×</button>
          </div>

          <div class="form-group">
            <label>等待时间 (秒)</label>
            <input
              v-model.number="modifyParams.waitTime"
              type="number"
              min="1"
              max="10"
              class="form-input"
            />
          </div>

          <div class="form-group">
            <label>点击方式</label>
            <select v-model="modifyParams.clickMode" class="form-input">
              <option value="auto">自动选择</option>
              <option value="bbox">坐标点击</option>
              <option value="selector">Selector点击</option>
              <option value="text">文本点击</option>
            </select>
          </div>

          <div class="form-group">
            <label>重试次数</label>
            <input
              v-model.number="modifyParams.retryCount"
              type="number"
              min="1"
              max="3"
              class="form-input"
            />
          </div>

          <button class="btn btn-primary btn-full" @click="onModifyConfirm">
            确认修改并重试
          </button>
        </div>

        <div v-if="logs && logs.length > 0" class="related-logs">
          <div class="logs-header">相关日志</div>
          <div class="logs-list">
            <div
              v-for="(log, idx) in logs.slice(-3)"
              :key="idx"
              class="log-entry"
              :class="log.level"
            >
              <span class="log-time">{{ formatTime(log.timestamp) }}</span>
              <span class="log-message">{{ log.message }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script>
export default {
  name: 'HumanInterventionPanel',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    job: {
      type: Object,
      default: () => ({})
    },
    riskScore: {
      type: Number,
      default: 0
    },
    threshold: {
      type: Number,
      default: 0.7
    },
    reason: {
      type: String,
      default: ''
    },
    factors: {
      type: Array,
      default: () => []
    },
    logs: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      showModifyForm: false,
      modifyParams: {
        waitTime: 3,
        clickMode: 'auto',
        retryCount: 1
      }
    }
  },
  computed: {
    riskLevel() {
      if (this.riskScore > this.threshold) return 'high'
      if (this.riskScore > this.threshold * 0.6) return 'medium'
      return 'low'
    }
  },
  methods: {
    onConfirm() {
      this.$emit('action', { action: 'confirm' })
      this.showModifyForm = false
    },
    onSkip() {
      this.$emit('action', { action: 'skip' })
      this.showModifyForm = false
    },
    onModifyConfirm() {
      this.$emit('action', {
        action: 'modify',
        params: { ...this.modifyParams }
      })
      this.showModifyForm = false
    },
    formatTime(timestamp) {
      if (!timestamp) return ''
      const date = new Date(timestamp)
      return date.toLocaleTimeString()
    }
  }
}
</script>

<style scoped>
.intervention-panel {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 90%;
  max-width: 500px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  z-index: 1000;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  color: white;
  font-weight: 600;
}

.panel-header.high { background: linear-gradient(135deg, #dc3545, #c82333); }
.panel-header.medium { background: linear-gradient(135deg, #ffc107, #fd7e14); color: #343a40; }

.warning-icon {
  font-size: 24px;
  margin-right: 12px;
}

.title {
  flex: 1;
  font-size: 18px;
}

.close-btn {
  background: none;
  border: none;
  color: inherit;
  font-size: 24px;
  cursor: pointer;
  opacity: 0.7;
}

.close-btn:hover {
  opacity: 1;
}

.panel-body {
  padding: 20px;
}

.job-info {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #dee2e6;
}

.job-title {
  font-size: 16px;
  font-weight: 600;
  color: #343a40;
  margin-bottom: 4px;
}

.job-company {
  font-size: 14px;
  color: #6c757d;
  margin-bottom: 4px;
}

.job-url {
  font-size: 11px;
  color: #adb5bd;
  word-break: break-all;
}

.risk-summary {
  margin-bottom: 16px;
}

.risk-score-display {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 8px;
}

.risk-score-display.high { background: #f8d7da; }
.risk-score-display.medium { background: #fff3cd; }
.risk-score-display.low { background: #d4edda; }

.risk-score-display .label {
  font-size: 14px;
  color: #495057;
}

.risk-score-display .value {
  font-size: 24px;
  font-weight: 700;
}

.risk-score-display.high .value { color: #dc3545; }
.risk-score-display.medium .value { color: #ffc107; }
.risk-score-display.low .value { color: #28a745; }

.risk-threshold {
  font-size: 12px;
  color: #6c757d;
  text-align: center;
}

.risk-reason {
  margin-top: 8px;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 6px;
  font-size: 13px;
  color: #495057;
}

.risk-factors {
  margin-bottom: 16px;
}

.factors-label {
  font-size: 12px;
  color: #6c757d;
  margin-bottom: 8px;
}

.factors-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.factor-tag {
  padding: 2px 8px;
  background: #e9ecef;
  border-radius: 4px;
  font-size: 11px;
  color: #495057;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.btn {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.btn-icon {
  font-size: 20px;
  margin-right: 12px;
}

.btn-label {
  flex: 1;
  font-weight: 600;
  font-size: 14px;
}

.btn-desc {
  font-size: 11px;
  opacity: 0.8;
}

.btn-continue {
  background: linear-gradient(135deg, #28a745, #20c997);
  color: white;
}

.btn-continue:hover {
  background: linear-gradient(135deg, #218a38, #1ba97f);
}

.btn-skip {
  background: #6c757d;
  color: white;
}

.btn-skip:hover {
  background: #5a6268;
}

.btn-modify {
  background: #17a2b8;
  color: white;
}

.btn-modify:hover {
  background: #138496;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-primary:hover {
  background: #0056b3;
}

.btn-full {
  width: 100%;
  justify-content: center;
}

.modify-form {
  margin-top: 16px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.form-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-weight: 600;
  color: #343a40;
}

.close-form {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #6c757d;
}

.form-group {
  margin-bottom: 12px;
}

.form-group label {
  display: block;
  font-size: 12px;
  color: #6c757d;
  margin-bottom: 4px;
}

.form-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ced4da;
  border-radius: 6px;
  font-size: 14px;
}

.form-input:focus {
  outline: none;
  border-color: #007bff;
}

.related-logs {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #dee2e6;
}

.logs-header {
  font-size: 12px;
  color: #6c757d;
  margin-bottom: 8px;
}

.logs-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.log-entry {
  display: flex;
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 4px;
  background: #f8f9fa;
}

.log-time {
  color: #6c757d;
  margin-right: 8px;
}

.log-message {
  color: #495057;
  flex: 1;
}

/* Transition */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
}

.slide-enter,
.slide-leave-to {
  opacity: 0;
  transform: translate(-50%, -50%) scale(0.9);
}
</style>
