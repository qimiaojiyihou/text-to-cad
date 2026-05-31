<template>
  <aside class="panel">
    <h1>Text to CAD</h1>
    <p class="hint">用自然语言描述你想要的机械零件，AI 会自动生成 CAD 模型。</p>

    <div v-if="!isLoggedIn" class="login-hint">
      <p>请登录后使用 CAD 生成功能</p>
      <button class="login-btn" @click="emit('show-auth')">登录 / 注册</button>
    </div>

    <template v-else>
      <textarea
        v-model="prompt"
        placeholder="例如：创建一个 100x60x20 mm 的长方体，中心有四个直径 8mm 的通孔，顶部外缘倒角 2mm。"
        rows="6"
      />

      <button
        class="generate-btn"
        :disabled="!prompt.trim() || status === 'generating'"
        @click="emitGenerate"
      >
        {{ buttonText }}
      </button>
    </template>

    <div v-if="message" class="message" :class="status">
      {{ message }}
    </div>

    <div v-if="modelId && (status === 'success' || status === 'cached')" class="downloads">
      <h3>模型文件</h3>
      <a class="link" :href="`/api/models/${modelId}/step`" :download="`${modelId}.step`">
        下载 STEP
      </a>
      <a class="link" :href="`/api/models/${modelId}/glb`" :download="`${modelId}.glb`">
        下载 GLB
      </a>
      <a class="link" :href="`/api/models/${modelId}/code`" :download="`${modelId}.py`">
        查看 Python 源码
      </a>
    </div>

    <div v-if="isLoggedIn" class="history-link">
      <router-link to="/history">查看历史记录 →</router-link>
    </div>

    <footer class="footer">
      Powered by build123d + LLM
    </footer>
  </aside>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  modelId: { type: String, default: '' },
  status: { type: String, default: 'idle' },
  message: { type: String, default: '' },
  isLoggedIn: { type: Boolean, default: false },
})

const emit = defineEmits(['generate', 'show-auth'])
const prompt = ref('')

const buttonText = computed(() => {
  if (props.status === 'generating') return '生成中…'
  return '生成 CAD'
})

function emitGenerate() {
  emit('generate', prompt.value.trim())
}
</script>

<style scoped>
.panel {
  width: 360px;
  min-width: 360px;
  padding: 24px;
  background: #161b22;
  border-right: 1px solid #30363d;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-sizing: border-box;
}

h1 {
  margin: 0;
  font-size: 22px;
  color: #58a6ff;
}

.hint {
  margin: 0;
  font-size: 13px;
  color: #8b949e;
  line-height: 1.5;
}

.login-hint {
  padding: 24px 16px;
  background: #0d1117;
  border: 1px dashed #30363d;
  border-radius: 8px;
  text-align: center;
}
.login-hint p {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #8b949e;
}

.login-btn {
  padding: 10px 20px;
  border: 1px solid #58a6ff;
  border-radius: 8px;
  background: transparent;
  color: #58a6ff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.login-btn:hover {
  background: #58a6ff22;
}

textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #30363d;
  border-radius: 8px;
  background: #0d1117;
  color: #c9d1d9;
  font-size: 14px;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
}
textarea:focus {
  border-color: #58a6ff;
}

.generate-btn {
  padding: 12px;
  border: none;
  border-radius: 8px;
  background: #238636;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}
.generate-btn:hover:not(:disabled) {
  background: #2ea043;
}
.generate-btn:disabled {
  background: #30363d;
  cursor: not-allowed;
}

.message {
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.5;
  word-break: break-word;
}
.message.generating {
  background: #1f6feb22;
  border: 1px solid #1f6feb;
  color: #58a6ff;
}
.message.success,
.message.cached {
  background: #23863622;
  border: 1px solid #238636;
  color: #3fb950;
}
.message.error {
  background: #da363322;
  border: 1px solid #da3633;
  color: #f85149;
}

.downloads {
  margin-top: 8px;
}
.downloads h3 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #c9d1d9;
}
.link {
  display: block;
  margin: 6px 0;
  color: #58a6ff;
  text-decoration: none;
  font-size: 13px;
}
.link:hover {
  text-decoration: underline;
}

.history-link {
  text-align: center;
  font-size: 13px;
}
.history-link a {
  color: #58a6ff;
  text-decoration: none;
}
.history-link a:hover {
  text-decoration: underline;
}

.footer {
  margin-top: auto;
  font-size: 11px;
  color: #484f58;
  text-align: center;
}
</style>
