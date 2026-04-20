<template>
  <div class="live-log">
    <div class="log-header">
      <span class="status-dot" :class="connectionStatus"></span>
      <span>实时日志</span>
      <span class="log-count" v-if="logs.length > 0">{{ logs.length }} 条</span>
    </div>
    <div class="log-entries" ref="logContainer">
      <div
        v-for="(log, i) in logs"
        :key="i"
        class="log-entry"
        :class="log.level"
      >
        <span class="log-time">{{ log.time }}</span>
        <span class="log-message">{{ log.message }}</span>
      </div>
      <div v-if="logs.length === 0 && !isConnected" class="log-empty">
        等待连接...
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'

const props = defineProps({
  /**
   * 任务ID，用于WebSocket连接
   * @type {string|number}
   */
  taskId: {
    type: [String, Number],
    required: true
  },
  /**
   * 是否自动滚动到底部
   * @type {boolean}
   */
  autoScroll: {
    type: Boolean,
    default: true
  },
  /**
   * 最大保留日志条数
   * @type {number}
   */
  maxLogs: {
    type: Number,
    default: 500
  }
})

const emit = defineEmits(['connected', 'disconnected', 'error', 'log'])

const logs = ref([])
const logContainer = ref(null)
const connectionStatus = ref('disconnected')
const isConnected = ref(false)
let ws = null
let reconnectTimer = null
let reconnectAttempts = 0
const maxReconnectAttempts = 5

/**
 * 格式化时间戳
 */
function formatTime(date) {
  const d = new Date(date)
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  const seconds = String(d.getSeconds()).padStart(2, '0')
  const ms = String(d.getMilliseconds()).padStart(3, '0')
  return `${hours}:${minutes}:${seconds}.${ms}`
}

/**
 * 添加日志条目
 */
function addLog(message, level = 'info') {
  const entry = {
    time: formatTime(new Date()),
    message,
    level
  }

  logs.value.push(entry)

  // 限制日志数量
  if (logs.value.length > props.maxLogs) {
    logs.value = logs.value.slice(-props.maxLogs)
  }

  emit('log', entry)

  // 自动滚动
  if (props.autoScroll) {
    nextTick(() => scrollToBottom())
  }
}

/**
 * 滚动到底部
 */
function scrollToBottom() {
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}

/**
 * 连接到WebSocket
 */
function connect() {
  if (!props.taskId) return

  const wsUrl = `/api/events/live/${props.taskId}`

  try {
    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      isConnected.value = true
      connectionStatus.value = 'connected'
      reconnectAttempts = 0
      emit('connected')
      addLog('WebSocket 连接已建立', 'info')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        const level = data.level || 'info'
        addLog(data.message || data.event || String(data), level)
      } catch {
        addLog(String(event.data), 'info')
      }
    }

    ws.onerror = (error) => {
      connectionStatus.value = 'error'
      emit('error', error)
      addLog('WebSocket 连接错误', 'error')
    }

    ws.onclose = () => {
      isConnected.value = false
      connectionStatus.value = 'disconnected'
      emit('disconnected')
      addLog('WebSocket 连接已关闭', 'warn')

      // 尝试重连
      if (reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++
        addLog(`将在 3 秒后尝试重连 (${reconnectAttempts}/${maxReconnectAttempts})`, 'warn')
        reconnectTimer = setTimeout(connect, 3000)
      }
    }
  } catch (error) {
    connectionStatus.value = 'error'
    emit('error', error)
    addLog(`连接失败: ${error.message}`, 'error')
  }
}

/**
 * 断开连接
 */
function disconnect() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }

  if (ws) {
    ws.close()
    ws = null
  }
}

/**
 * 清空日志
 */
function clearLogs() {
  logs.value = []
}

// 监听 autoScroll 变化
watch(
  () => props.autoScroll,
  (newVal) => {
    if (newVal) {
      nextTick(() => scrollToBottom())
    }
  }
)

// 监听 logs 变化以支持外部滚动
watch(
  () => props.taskId,
  () => {
    logs.value = []
    disconnect()
    connect()
  }
)

onMounted(() => {
  connect()
})

onUnmounted(() => {
  disconnect()
})

// 暴露方法给父组件
defineExpose({
  addLog,
  clearLogs,
  scrollToBottom,
  disconnect,
  connect
})
</script>

<style scoped>
.live-log {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.log-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #fafafa;
  border-bottom: 1px solid #eee;
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #8c8c8c;
}

.status-dot.connected {
  background: #52c41a;
  animation: pulse 2s infinite;
}

.status-dot.disconnected {
  background: #8c8c8c;
}

.status-dot.error {
  background: #ff4d4f;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.log-count {
  margin-left: auto;
  font-size: 12px;
  color: #999;
  font-weight: normal;
}

.log-entries {
  max-height: 300px;
  overflow-y: auto;
  padding: 8px 0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
}

.log-entries::-webkit-scrollbar {
  width: 6px;
}

.log-entries::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.log-entries::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}

.log-entries::-webkit-scrollbar-thumb:hover {
  background: #999;
}

.log-entry {
  display: flex;
  gap: 12px;
  padding: 4px 16px;
  line-height: 1.6;
}

.log-entry:hover {
  background: #f5f5f5;
}

.log-entry.info {
  color: #333;
}

.log-entry.warn {
  color: #faad14;
  background: #fffbe6;
}

.log-entry.error {
  color: #ff4d4f;
  background: #fff2f0;
}

.log-entry.success {
  color: #52c41a;
  background: #f6ffed;
}

.log-time {
  color: #999;
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}

.log-message {
  word-break: break-all;
}

.log-empty {
  padding: 20px;
  text-align: center;
  color: #999;
}
</style>
