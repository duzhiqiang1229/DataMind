<template>
  <div class="login-container">
    <div class="login-bg-shapes">
      <div class="shape shape-1"></div>
      <div class="shape shape-2"></div>
      <div class="shape shape-3"></div>
    </div>
    <div class="login-card">
      <div class="login-header">
        <div class="logo-icon">
          <el-icon size="28"><DataLine /></el-icon>
        </div>
        <h2>DataMind</h2>
        <p>企业智能数据平台</p>
      </div>
      <el-form ref="loginFormRef" :model="loginForm" :rules="rules" @keyup.enter="handleLogin">
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" class="login-btn" :loading="loading" @click="handleLogin">
            登 录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="login-footer">
        <span>admin / admin123</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, type FormInstance } from "element-plus";
import { User, Lock } from "@element-plus/icons-vue";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const authStore = useAuthStore();

const loginFormRef = ref<FormInstance>();
const loading = ref(false);

const loginForm = reactive({
  username: "",
  password: "",
});

const rules = {
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

async function handleLogin() {
  if (!loginFormRef.value) return;
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return;
    loading.value = true;
    try {
      await authStore.login(loginForm.username, loginForm.password);
      await authStore.fetchCurrentUser();
      ElMessage.success("登录成功");
      router.push("/dashboard");
    } catch {
      // Error handled by axios interceptor
    } finally {
      loading.value = false;
    }
  });
}
</script>

<style lang="scss" scoped>
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 40%, #312e81 100%);
  position: relative;
  overflow: hidden;
}

.login-bg-shapes {
  position: absolute;
  width: 100%;
  height: 100%;
  pointer-events: none;

  .shape {
    position: absolute;
    border-radius: 50%;
    filter: blur(80px);
    opacity: 0.4;
  }

  .shape-1 {
    width: 400px;
    height: 400px;
    background: #4366e5;
    top: -100px;
    right: -100px;
    animation: float 8s ease-in-out infinite;
  }

  .shape-2 {
    width: 300px;
    height: 300px;
    background: #7c3aed;
    bottom: -80px;
    left: -80px;
    animation: float 10s ease-in-out infinite reverse;
  }

  .shape-3 {
    width: 200px;
    height: 200px;
    background: #06b6d4;
    top: 40%;
    left: 60%;
    animation: float 12s ease-in-out infinite;
  }
}

@keyframes float {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-30px) scale(1.05); }
}

.login-card {
  width: 400px;
  padding: 40px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  position: relative;
  z-index: 1;
  animation: cardAppear 0.6s ease-out;
}

@keyframes cardAppear {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.login-header {
  text-align: center;
  margin-bottom: 32px;

  .logo-icon {
    width: 56px;
    height: 56px;
    margin: 0 auto 12px;
    border-radius: 14px;
    background: linear-gradient(135deg, #4366e5, #6c8aff);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    box-shadow: 0 4px 16px rgba(67, 102, 229, 0.4);
  }

  h2 {
    margin: 0 0 4px;
    color: #1e293b;
    font-size: 24px;
    font-weight: 700;
    letter-spacing: 0.5px;
  }

  p {
    color: #94a3b8;
    font-size: 14px;
  }
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 4px;
}

.login-footer {
  text-align: center;
  margin-top: 16px;
  font-size: 12px;
  color: #cbd5e1;
}
</style>
