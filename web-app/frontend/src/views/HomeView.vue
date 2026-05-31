<template>
  <div class="home">
    <PromptPanel
      :model-id="modelId"
      :status="status"
      :message="message"
      :is-logged-in="!!authStore.state.user"
      @generate="onGenerate"
      @show-auth="showAuth = true"
    />
    <div class="main-area">
      <header class="top-bar">
        <UserMenu @show-auth="showAuth = true" />
      </header>
      <CadViewer ref="viewer" :model-id="modelId" />
    </div>
    <AuthModal v-if="showAuth" @close="showAuth = false" @success="onAuthSuccess" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import PromptPanel from '../components/PromptPanel.vue'
import CadViewer from '../components/CadViewer.vue'
import AuthModal from '../components/AuthModal.vue'
import UserMenu from '../components/UserMenu.vue'
import authStore from '../stores/auth.js'

const route = useRoute()
const modelId = ref('')
const status = ref('idle')
const message = ref('')
const viewer = ref(null)
const showAuth = ref(false)

const POLL_INTERVAL_MS = 2000
const STATUS_TEXT = {
  pending: '任务已创建，等待处理…',
  llm_running: 'LLM 正在生成 Python 代码…',
  cad_running: 'build123d 正在计算几何…',
  completed: '生成完成！',
  cached: '模型已存在（缓存）。',
  failed: '生成失败',
}

function onAuthSuccess() {
  showAuth.value = false
}

onMounted(() => {
  const previewId = route.query.preview
  if (previewId && typeof previewId === 'string') {
    modelId.value = previewId
    setTimeout(() => {
      viewer.value?.loadModel(previewId)
    }, 500)
  }
})

async function onGenerate(prompt) {
  if (!authStore.state.user) {
    showAuth.value = true
    return
  }

  status.value = 'generating'
  message.value = '提交任务中…'
  modelId.value = ''

  let taskId = ''
  try {
    const res = await authStore.fetchWithAuth('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt })
    })
    const data = await res.json()

    if (!res.ok) {
      status.value = 'error'
      message.value = `提交失败 (${res.status}): ${data.detail || JSON.stringify(data)}`
      return
    }

    taskId = data.task_id
    status.value = 'generating'
    message.value = STATUS_TEXT['pending'] || '处理中…'
  } catch (err) {
    status.value = 'error'
    message.value = `网络错误: ${err.message}`
    return
  }

  const interval = setInterval(async () => {
    try {
      const res = await authStore.fetchWithAuth(`/api/tasks/${taskId}`)

      let data
      const contentType = res.headers.get('content-type') || ''
      if (contentType.includes('application/json')) {
        data = await res.json()
      } else {
        const text = await res.text()
        clearInterval(interval)
        status.value = 'error'
        message.value = `轮询失败 (${res.status}): 服务器返回了无效的响应`
        console.error('Non-JSON poll response:', res.status, text.slice(0, 200))
        return
      }

      if (!res.ok) {
        clearInterval(interval)
        status.value = 'error'
        message.value = `轮询失败 (${res.status}): ${data.detail || 'Unknown error'}`
        return
      }

      const taskStatus = data.status
      status.value = taskStatus === 'completed' || taskStatus === 'cached' ? 'success' : 'generating'
      message.value = data.message || STATUS_TEXT[taskStatus] || `状态: ${taskStatus}`

      if (taskStatus === 'completed' || taskStatus === 'cached') {
        clearInterval(interval)
        modelId.value = data.model_id
        setTimeout(() => {
          viewer.value?.loadModel(data.model_id)
        }, 500)
      } else if (taskStatus === 'failed') {
        clearInterval(interval)
        status.value = 'error'
      }
    } catch (err) {
      clearInterval(interval)
      status.value = 'error'
      message.value = `轮询异常: ${err.message}`
    }
  }, POLL_INTERVAL_MS)
}
</script>

<style scoped>
.home {
  display: flex;
  width: 100vw;
  height: 100vh;
  background: #0d1117;
  color: #c9d1d9;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.top-bar {
  height: 48px;
  background: #161b22;
  border-bottom: 1px solid #30363d;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 20px;
  flex-shrink: 0;
}
</style>
