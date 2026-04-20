<template>
  <div class="chart-container">
    <h4>投递成功率趋势</h4>
    <RechartsLineChart :data="data" :margin="{ top: 10, right: 20, left: 0, bottom: 0 }">
      <XAxis dataKey="date" />
      <YAxis :domain="[0, 100]" />
      <Tooltip />
      <Line
        type="monotone"
        dataKey="rate"
        stroke="#52c41a"
        :strokeWidth="2"
      />
    </RechartsLineChart>
  </div>
</template>

<script setup>
import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts'

defineProps({
  data: {
    type: Array,
    default: () => []
  }
})
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
