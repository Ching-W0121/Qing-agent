<template>
  <div class="chart-container">
    <h4>失败原因分布</h4>
    <RechartsPieChart>
      <Pie
        dataKey="count"
        :data="data"
        cx="50%"
        cy="50%"
        :outerRadius="80"
        :innerRadius="40"
        :paddingAngle="2"
        :label="labelFormatter"
      />
      <Tooltip />
      <Legend iconType="circle" />
    </RechartsPieChart>
  </div>
</template>

<script setup>
import {
  PieChart as RechartsPieChart,
  Pie,
  Tooltip,
  Legend,
} from 'recharts'

defineProps({
  data: {
    type: Array,
    default: () => []
  }
})

function labelFormatter({ name, percent }) {
  return `${name} ${(percent * 100).toFixed(0)}%`
}
</script>

<style scoped>
.chart-container {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}
.chart-container h4 {
  font-size: 16px;
  color: #333;
  margin-bottom: 16px;
  font-weight: 500;
}
</style>
