<template>
  <div class="high-success-companies">
    <div v-if="companies.length === 0" class="empty-state">
      暂无数据
    </div>
    <div v-else class="company-list">
      <div
        v-for="(company, index) in companies"
        :key="company.name"
        class="company-item"
      >
        <div class="rank">{{ index + 1 }}</div>
        <div class="company-info">
          <span class="company-name">{{ company.name }}</span>
          <span class="company-stats">{{ company.applyCount }} 次投递</span>
        </div>
        <div class="success-rate-bar">
          <div
            class="bar-fill"
            :style="{ width: company.successRate + '%' }"
            :class="getRateClass(company.successRate)"
          ></div>
        </div>
        <span class="success-rate-value">{{ company.successRate }}%</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /**
   * 公司列表数据
   * @type {Array<{name: string, applyCount: number, successRate: number}>}
   * @description 按成功率降序排列的公司列表
   */
  companies: {
    type: Array,
    default: () => [],
    required: true
  }
})

/**
 * 根据成功率返回对应的样式类
 * @param {number} rate - 成功率 (0-100)
 * @returns {string} 样式类名
 */
function getRateClass(rate) {
  if (rate > 50) {
    return 'rate-high'
  } else if (rate >= 30) {
    return 'rate-medium'
  } else {
    return 'rate-low'
  }
}
</script>

<style scoped>
.high-success-companies {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.empty-state {
  text-align: center;
  padding: 32px;
  color: #999;
  font-size: 14px;
}

.company-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.company-item {
  display: grid;
  grid-template-columns: 32px 1fr 120px 60px;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
  transition: background 0.2s ease;
}

.company-item:hover {
  background: #f5f5f5;
}

.rank {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 600;
}

.company-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.company-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.company-stats {
  font-size: 12px;
  color: #999;
}

.success-rate-bar {
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.rate-high {
  background: linear-gradient(90deg, #52c41a, #73d13d);
}

.rate-medium {
  background: linear-gradient(90deg, #faad14, #ffc53d);
}

.rate-low {
  background: linear-gradient(90deg, #ff4d4f, #ff7875);
}

.success-rate-value {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  text-align: right;
  min-width: 48px;
}

/* Responsive adjustments */
@media (max-width: 640px) {
  .company-item {
    grid-template-columns: 28px 1fr 80px 48px;
    gap: 8px;
    padding: 10px;
  }

  .rank {
    width: 24px;
    height: 24px;
    font-size: 11px;
  }

  .company-name {
    font-size: 13px;
  }

  .company-stats {
    font-size: 11px;
  }

  .success-rate-bar {
    height: 6px;
  }

  .success-rate-value {
    font-size: 12px;
  }
}
</style>
