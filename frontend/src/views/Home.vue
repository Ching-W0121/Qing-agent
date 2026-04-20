<template>
  <div class="home">
    <header class="hero">
      <h1>求职 Agent</h1>
      <p class="tagline">精准投递，而非乱投</p>
    </header>

    <section class="features">
      <div class="feature-card">
        <div class="icon">🌐</div>
        <h3>多平台支持</h3>
        <p>智联招聘、前程无忧、猎聘</p>
      </div>

      <div class="feature-card">
        <div class="icon">🎯</div>
        <h3>智能筛选</h3>
        <p>硬过滤 + 动态评分，只投真正匹配的岗位</p>
      </div>

      <div class="feature-card">
        <div class="icon">📊</div>
        <h3>实时跟踪</h3>
        <p>投递状态实时查看，掌控求职进度</p>
      </div>
    </section>

    <section class="actions">
      <button class="primary-btn" @click="$router.push('/login')">
        开始使用
      </button>
    </section>
  </div>
</template>

<script setup>
</script>

<style scoped>
.home {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 0;
}

.hero {
  text-align: center;
  padding: 80px 20px 40px;
}

.hero h1 {
  font-size: 48px;
  margin-bottom: 16px;
}

.tagline {
  font-size: 24px;
  opacity: 0.9;
}

.features {
  display: flex;
  gap: 30px;
  justify-content: center;
  padding: 60px 20px;
  flex-wrap: wrap;
}

.feature-card {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 30px;
  width: 280px;
  text-align: center;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.feature-card .icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.feature-card h3 {
  font-size: 20px;
  margin-bottom: 12px;
}

.feature-card p {
  font-size: 14px;
  opacity: 0.8;
}

.actions {
  text-align: center;
  padding: 40px 20px 80px;
}

.primary-btn {
  padding: 16px 48px;
  font-size: 18px;
  background: white;
  color: #667eea;
  border: none;
  border-radius: 30px;
  cursor: pointer;
  font-weight: 600;
  transition: transform 0.2s, box-shadow 0.2s;
}

.primary-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}
</style>
