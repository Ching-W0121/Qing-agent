<template>
  <div class="engine-status">
    <div class="status-item" :class="visionStatusClass">
      <span class="status-label">Vision</span>
      <span class="status-value">{{ visionStatus }}</span>
    </div>
    <div class="status-item" :class="embeddingStatusClass">
      <span class="status-label">Embedding</span>
      <span class="status-value">{{ embeddingStatus }}</span>
    </div>
    <div class="status-item" :class="recoveryStatusClass">
      <span class="status-label">Recovery</span>
      <span class="status-value">{{ recoveryStatus }}</span>
    </div>
    <div class="status-item" :class="learningStatusClass">
      <span class="status-label">Success Learning</span>
      <span class="status-value">{{ learningStatus }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /**
   * Vision 引擎状态
   * @type {string}
   * @description ACTIVE | STANDBY | TRAINING | ERROR
   */
  visionStatus: {
    type: String,
    default: 'STANDBY',
    validator: (v) => ['ACTIVE', 'STANDBY', 'TRAINING', 'ERROR'].includes(v)
  },
  /**
   * Embedding 引擎状态
   * @type {string}
   * @description ACTIVE | STANDBY | TRAINING | ERROR
   */
  embeddingStatus: {
    type: String,
    default: 'STANDBY',
    validator: (v) => ['ACTIVE', 'STANDBY', 'TRAINING', 'ERROR'].includes(v)
  },
  /**
   * Recovery 引擎状态
   * @type {string}
   * @description ACTIVE | STANDBY | TRAINING | ERROR
   */
  recoveryStatus: {
    type: String,
    default: 'STANDBY',
    validator: (v) => ['ACTIVE', 'STANDBY', 'TRAINING', 'ERROR'].includes(v)
  },
  /**
   * Success Learning 引擎状态
   * @type {string}
   * @description ACTIVE | STANDBY | TRAINING | ERROR
   */
  learningStatus: {
    type: String,
    default: 'STANDBY',
    validator: (v) => ['ACTIVE', 'STANDBY', 'TRAINING', 'ERROR'].includes(v)
  }
})

/**
 * 状态对应的样式类
 */
const statusClassMap = {
  ACTIVE: 'status-active',
  STANDBY: 'status-standby',
  TRAINING: 'status-training',
  ERROR: 'status-error'
}

const visionStatusClass = computed(() => statusClassMap[props.visionStatus] || 'status-standby')
const embeddingStatusClass = computed(() => statusClassMap[props.embeddingStatus] || 'status-standby')
const recoveryStatusClass = computed(() => statusClassMap[props.recoveryStatus] || 'status-standby')
const learningStatusClass = computed(() => statusClassMap[props.learningStatus] || 'status-standby')
</script>

<style scoped>
.engine-status {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

@media (min-width: 768px) {
  .engine-status {
    grid-template-columns: repeat(4, 1fr);
  }
}

.status-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 12px;
  border-radius: 8px;
  text-align: center;
  transition: all 0.3s ease;
}

.status-label {
  font-size: 12px;
  color: #666;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-value {
  font-size: 14px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 12px;
  min-width: 80px;
}

/* Active 状态 - 绿色 */
.status-active .status-value {
  background: #f6ffed;
  color: #52c41a;
  border: 1px solid #b7eb8f;
}

.status-active {
  background: #fafff0;
}

/* Standby 状态 - 灰色 */
.status-standby .status-value {
  background: #fafafa;
  color: #8c8c8c;
  border: 1px solid #d9d9d9;
}

.status-standby {
  background: #fafafa;
}

/* Training 状态 - 蓝色 */
.status-training .status-value {
  background: #f0f5ff;
  color: #1677ff;
  border: 1px solid #91caff;
  animation: pulse-training 2s infinite;
}

.status-training {
  background: #f5f8ff;
}

@keyframes pulse-training {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

/* Error 状态 - 红色 */
.status-error .status-value {
  background: #fff2f0;
  color: #ff4d4f;
  border: 1px solid #ffccc7;
}

.status-error {
  background: #fff7f6;
}
</style>
