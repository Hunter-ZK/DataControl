<template>
  <div class="login-page">
    <div class="login-shell">
      <section class="login-brand"><span class="brand-mark">D</span><div><span class="dc-eyebrow">DATA ASSET PORTAL</span><h1>DataControl</h1><p>统一的数据资产服务入口。搜索、理解、追踪并安全使用数据资产。</p></div></section>
      <section class="login-card dc-card"><span class="dc-eyebrow">SIGN IN</span><h2>登录数据资产服务平台</h2><p>当前为开发验证登录，生产环境认证将在 P4 接入。</p><el-form label-position="top" @submit.prevent="submit"><el-form-item label="用户名"><el-input v-model="username" autocomplete="username"/></el-form-item><el-form-item label="密码"><el-input v-model="password" type="password" show-password autocomplete="current-password" @keyup.enter="submit"/></el-form-item><el-button type="primary" class="submit" :loading="loading" @click="submit">登录</el-button></el-form><div class="demo"><b>演示账号</b><span>demo / DataControl123!</span><span>admin / DataControlAdmin123!</span></div></section>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api/client'
const router=useRouter(); const username=ref('demo'); const password=ref('DataControl123!'); const loading=ref(false)
async function submit(){loading.value=true;try{const data:any=await authApi.login(username.value,password.value);localStorage.setItem('datacontrol_token',data.accessToken);localStorage.setItem('datacontrol_user',JSON.stringify(data.user));ElMessage.success('登录成功');router.push('/')}catch{ElMessage.error('用户名或密码错误')}finally{loading.value=false}}
</script>
<style scoped>
.login-page{min-height:100vh;display:grid;place-items:center;padding:30px;background:radial-gradient(circle at 16% 10%,rgba(117,202,224,.22),transparent 32%),linear-gradient(145deg,#f3faff,#fbfdff 55%,#eef8fc)}.login-shell{width:min(100%,1040px);display:grid;grid-template-columns:minmax(0,1.2fr) 390px;gap:28px;align-items:center}.login-brand{padding:30px 10px;display:flex;gap:18px;align-items:flex-start}.brand-mark{flex:0 0 58px;height:58px;border-radius:18px;display:grid;place-items:center;background:linear-gradient(135deg,#75c8df,#469fc9);color:#fff;font-size:26px;font-weight:800;box-shadow:0 16px 38px rgba(67,156,198,.22)}.login-brand h1{font-size:40px;letter-spacing:-.04em;margin:7px 0 8px}.login-brand p{max-width:520px;color:var(--dc-text-2);line-height:1.8}.login-card{padding:28px}.login-card h2{font-size:21px;margin:7px 0}.login-card>p{font-size:11px;color:var(--dc-text-2);margin:0 0 20px}.submit{width:100%;height:42px}.demo{margin-top:18px;padding:13px;border-radius:11px;background:#f5fafd;display:grid;gap:4px;color:#6e8797;font-size:10px}.demo b{color:#365e76}@media(max-width:760px){.login-shell{grid-template-columns:1fr}.login-brand{padding:10px}.login-brand h1{font-size:32px}.login-card{padding:22px}}
</style>
