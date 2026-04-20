<template>
  <nav class="navbar">
    <div class="nav-brand">
      <span class="logo">🎯</span>
      <span class="brand-name">求职 Agent</span>
    </div>

    <div class="nav-links">
      <router-link to="/dashboard" class="nav-link">控制台</router-link>
      <router-link to="/profile" class="nav-link">画像</router-link>
    </div>

    <div class="nav-actions">
      <button class="logout-btn" @click="logout">退出</button>
    </div>
  </nav>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user_id')
  router.push('/login')
}
</script>

<style scoped>
.navbar {
  background: white;
  padding: 0 24px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo {
  font-size: 24px;
}

.brand-name {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.nav-links {
  display: flex;
  gap: 8px;
}

.nav-link {
  padding: 8px 16px;
  color: #666;
  text-decoration: none;
  border-radius: 6px;
  transition: all 0.2s;
}

.nav-link:hover,
.nav-link.router-link-active {
  background: #f5f5f5;
  color: #007bff;
}

.nav-actions {
  display: flex;
  align-items: center;
}

.logout-btn {
  padding: 8px 16px;
  background: transparent;
  color: #666;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.logout-btn:hover {
  background: #f5f5f5;
  color: #333;
}
</style>
