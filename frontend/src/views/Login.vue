<template>
  <div class="login-page">
    <div class="login-card">
      <h1>登录求职 Agent</h1>
      <p class="subtitle">开始你的精准求职之旅</p>

      <div class="auth-buttons">
        <button class="auth-btn auth0" @click="loginWithAuth0">
          <span class="icon">🔐</span>
          使用 Auth0 登录
        </button>
      </div>

      <div class="divider">
        <span>或</span>
      </div>

      <div class="demo-note">
        <p>演示模式：</p>
        <button class="demo-btn" @click="demoLogin">
          进入演示
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const loginWithAuth0 = () => {
  // TODO: 实现 Auth0 登录
  alert('Auth0 登录功能待实现')
}

const demoLogin = () => {
  // 演示模式：直接跳转到 dashboard
  localStorage.setItem('token', 'demo-token')
  localStorage.setItem('user_id', '1')
  router.push('/dashboard')
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-card {
  background: white;
  border-radius: 20px;
  padding: 48px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  text-align: center;
}

.login-card h1 {
  color: #333;
  margin-bottom: 8px;
}

.subtitle {
  color: #666;
  margin-bottom: 32px;
}

.auth-buttons {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.auth-btn {
  width: 100%;
  padding: 16px;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  transition: transform 0.2s;
}

.auth-btn:hover {
  transform: translateY(-2px);
}

.auth-btn.auth0 {
  background: #EB5424;
  color: white;
}

.auth-btn .icon {
  font-size: 20px;
}

.divider {
  margin: 24px 0;
  color: #999;
  position: relative;
}

.divider::before,
.divider::after {
  content: '';
  position: absolute;
  top: 50%;
  width: 40%;
  height: 1px;
  background: #ddd;
}

.divider::before { left: 0; }
.divider::after { right: 0; }

.demo-note {
  color: #666;
}

.demo-note p {
  margin-bottom: 12px;
}

.demo-btn {
  padding: 12px 32px;
  background: #f5f5f5;
  color: #333;
  border: 1px solid #ddd;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.demo-btn:hover {
  background: #eee;
}
</style>
