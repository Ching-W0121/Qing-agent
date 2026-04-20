<template>
  <div class="log-panel">
    <div class="log-header">
      <span class="log-title">📋 执行日志</span>
      <div class="log-controls">
        <select v-model="logLevel" class="level-select">
          <option value="simple">简化</option>
          <option value="detailed">详细</option>
        </select>
        <input
          v-model="logFilter"
          type="text"
          placeholder="筛选日志..."
          class="filter-input"
          @keyup.enter="applyFilter"
        />
        <button class="clear-btn" @click="clearLogs">清空</button>
      </div>
    </div>

    <div class="log-content" ref="logContent">
      <div v-if="filteredLogs.length === 0" class="empty-state">
        暂无日志
      </div>

      <div
        v-for="(log, index) in filteredLogs"
        :key="index"
        class="log-entry"
        :class="[log.level, { expanded: expandedLogs.has(index) }]"
        @click="toggleExpand(index)"
      >
        <div class="log-main">
          <span class="log-time">{{ formatTime(log.timestamp) }}</span>
          <span class="log-icon">{{ getLogIcon(log.level) }}</span>
          <span class="log-message">{{ log.message }}</span>
          <span v-if="logLevel === 'detailed' && log.details" class="expand-hint">
            {{ expandedLogs.has(index) ? '▲' : '▼' }}
          </span>
        </div>

        <!-- 详细模式下的额外信息 -->
        <div v-if="logLevel === 'detailed' && log.details && expandedLogs.has(index)" class="log-details">
          <div class="details-section" v-if="log.details.url">
            <span class="details-label">URL:</span>
            <span class="details-value">{{ log.details.url }}</span>
          </div>
          <div class="details-section" v-if="log.details.duration">
            <span class="details-label">耗时:</span>
            <span class="details-value">{{ log.details.duration }}ms</span>
          </div>
          <div class="details-section" v-if="log.details.score !== undefined">
            <span class="details-label">评分:</span>
            <span class="details-value">{{ log.details.score }}</span>
          </div>
          <div class="details-section" v-if="log.details.factors">
            <span class="details-label">因素:</span>
            <span class="details-value">{{ JSON.stringify(log.details.factors) }}</span>
          </div>
          <div class="details-section" v-if="log.details.button">
            <span class="details-label">按钮:</span>
            <span class="details-value">{{ log.details.button }}</span>
          </div>
          <div class="details-section" v-if="log.details.error">
            <span class="details-label">错误:</span>
            <span class="details-value error">{{ log.details.error }}</span>
          </div>
          <div class="details-section" v-if="log.details.riskScore">
            <span class="details-label">RiskScore:</span>
            <span class="details-value" :class="getRiskClass(log.details.riskScore)">
              {{ (log.details.riskScore * 100).toFixed(0) }}%
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="log-footer">
      <span class="log-count">共 {{ filteredLogs.length }} 条日志</span>
      <button v-if="filteredLogs.length > 0" class="scroll-bottom" @click="scrollToBottom">
        跳转底部
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LogPanel',
  props: {
    initialLogs: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      logs: [],
      logLevel: 'simple',  // simple | detailed
      logFilter: '',
      expandedLogs: new Set()
    }
  },
  computed: {
    filteredLogs() {
      if (!this.logFilter) return this.logs
      const filter = this.logFilter.toLowerCase()
      return this.logs.filter(log =>
        log.message.toLowerCase().includes(filter) ||
        (log.details && JSON.stringify(log.details).toLowerCase().includes(filter))
      )
    }
  },
  watch: {
    initialLogs: {
      immediate: true,
      handler(newLogs) {
        if (newLogs && newLogs.length > 0) {
          this.logs = [...newLogs]
        }
      }
    }
  },
  methods: {
    addLog(log) {
      const entry = {
        timestamp: log.timestamp || new Date().toISOString(),
        level: log.level || 'info',
        message: log.message || '',
        details: log.details || null
      }
      this.logs.push(entry)

      // 自动滚动到底部
      this.$nextTick(() => {
        this.scrollToBottom()
      })
    },

    clearLogs() {
      this.logs = []
      this.expandedLogs.clear()
    },

    toggleExpand(index) {
      if (this.expandedLogs.has(index)) {
        this.expandedLogs.delete(index)
      } else {
        this.expandedLogs.add(index)
      }
    },

    scrollToBottom() {
      if (this.$refs.logContent) {
        this.$refs.logContent.scrollTop = this.$refs.logContent.scrollHeight
      }
    },

    applyFilter() {
      // Filter is applied via computed property
    },

    getLogIcon(level) {
      const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️',
        debug: '🔍',
        risk_high: '🔴',
        risk_medium: '🟡',
        risk_low: '🟢'
      }
      return icons[level] || '•'
    },

    formatTime(timestamp) {
      if (!timestamp) return ''
      const date = new Date(timestamp)
      return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      })
    },

    getRiskClass(score) {
      if (score > 0.7) return 'risk-high'
      if (score > 0.4) return 'risk-medium'
      return 'risk-low'
    }
  },
  mounted() {
    // 监听SSE日志事件
    if (window.EventSource) {
      this.eventSource = new EventSource('/api/events/sse')
      this.eventSource.addEventListener('log', (e) => {
        try {
          const data = JSON.parse(e.data)
          this.addLog(data)
        } catch (err) {
          console.error('Failed to parse log event:', err)
        }
      })
    }
  },
  beforeDestroy() {
    if (this.eventSource) {
      this.eventSource.close()
    }
  }
}
</script>

<style scoped>
.log-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #1e1e1e;
  border-radius: 8px;
  overflow: hidden;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #2d2d2d;
  border-bottom: 1px solid #3d3d3d;
}

.log-title {
  color: #e0e0e0;
  font-weight: 600;
}

.log-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.level-select {
  padding: 4px 8px;
  background: #3d3d3d;
  color: #e0e0e0;
  border: 1px solid #4d4d4d;
  border-radius: 4px;
  font-size: 12px;
}

.filter-input {
  padding: 4px 8px;
  background: #3d3d3d;
  color: #e0e0e0;
  border: 1px solid #4d4d4d;
  border-radius: 4px;
  font-size: 12px;
  width: 150px;
}

.filter-input::placeholder {
  color: #888;
}

.clear-btn {
  padding: 4px 8px;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
}

.clear-btn:hover {
  background: #c82333;
}

.log-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
}

.empty-state {
  color: #666;
  text-align: center;
  padding: 20px;
}

.log-entry {
  padding: 4px 8px;
  border-radius: 4px;
  margin-bottom: 2px;
  cursor: pointer;
  transition: background 0.2s;
}

.log-entry:hover {
  background: #2d2d2d;
}

.log-entry.success { color: #4caf50; }
.log-entry.error { color: #f44336; }
.log-entry.warning { color: #ff9800; }
.log-entry.info { color: #2196f3; }
.log-entry.debug { color: #9e9e9e; }
.log-entry.risk_high { color: #f44336; background: rgba(244, 67, 54, 0.1); }
.log-entry.risk_medium { color: #ff9800; background: rgba(255, 152, 0, 0.1); }
.log-entry.risk_low { color: #4caf50; background: rgba(76, 175, 80, 0.1); }

.log-main {
  display: flex;
  align-items: center;
  gap: 8px;
}

.log-time {
  color: #666;
  font-size: 11px;
}

.log-icon {
  font-size: 12px;
}

.log-message {
  flex: 1;
  color: #e0e0e0;
  word-break: break-all;
}

.expand-hint {
  color: #666;
  font-size: 10px;
}

.log-details {
  margin-top: 8px;
  padding: 8px;
  background: #252525;
  border-radius: 4px;
  font-size: 11px;
}

.details-section {
  display: flex;
  gap: 8px;
  margin-bottom: 4px;
}

.details-section:last-child {
  margin-bottom: 0;
}

.details-label {
  color: #888;
  min-width: 60px;
}

.details-value {
  color: #bbb;
  word-break: break-all;
}

.details-value.error {
  color: #f44336;
}

.details-value.risk-high { color: #f44336; }
.details-value.risk-medium { color: #ff9800; }
.details-value.risk-low { color: #4caf50; }

.log-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #2d2d2d;
  border-top: 1px solid #3d3d3d;
}

.log-count {
  color: #888;
  font-size: 11px;
}

.scroll-bottom {
  padding: 4px 8px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
}

.scroll-bottom:hover {
  background: #0056b3;
}
</style>