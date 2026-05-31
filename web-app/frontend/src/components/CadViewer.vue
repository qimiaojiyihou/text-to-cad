<template>
  <div ref="container" class="viewer">
    <div v-if="!modelId && !error" class="placeholder">
      <div class="placeholder-text">在左侧输入描述并点击"生成 CAD"<br>模型将在此预览</div>
    </div>
    <div v-if="loading" class="loading">加载模型中…</div>
    <div v-if="error" class="error-msg">{{ error }}</div>
    <div v-if="currentModel" class="viewer-toolbar">
      <button class="toolbar-btn" @click="toggleWireframe">
        {{ wireframe ? '实体' : '线框' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import authStore from '../stores/auth.js'

const props = defineProps({
  modelId: { type: String, default: '' }
})

const container = ref(null)
const loading = ref(false)
const error = ref('')
const wireframe = ref(false)

let scene, camera, renderer, controls, currentModel
let objectUrl = null

function toggleWireframe() {
  wireframe.value = !wireframe.value
  if (!currentModel) return
  currentModel.traverse((child) => {
    if (child.isMesh && child.material) {
      const mats = Array.isArray(child.material) ? child.material : [child.material]
      mats.forEach((m) => {
        m.wireframe = wireframe.value
      })
    }
  })
}

function initScene() {
  const el = container.value
  const w = el.clientWidth
  const h = el.clientHeight

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0d1117)

  camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 10000)
  camera.position.set(200, 150, 200)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(w, h)
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.shadowMap.enabled = true
  el.appendChild(renderer.domElement)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  controls.target.set(0, 10, 0)

  // Lights
  const ambient = new THREE.AmbientLight(0xffffff, 0.6)
  scene.add(ambient)

  const dir = new THREE.DirectionalLight(0xffffff, 1.2)
  dir.position.set(100, 200, 100)
  dir.castShadow = true
  scene.add(dir)

  const dir2 = new THREE.DirectionalLight(0xffffff, 0.4)
  dir2.position.set(-100, 50, -100)
  scene.add(dir2)

  // Grid
  const grid = new THREE.GridHelper(500, 50, 0x30363d, 0x21262d)
  scene.add(grid)

  animate()
}

function animate() {
  requestAnimationFrame(animate)
  controls.update()
  renderer.render(scene, camera)
}

function clearModel() {
  if (currentModel) {
    scene.remove(currentModel)
    currentModel.traverse((child) => {
      if (child.geometry) child.geometry.dispose()
      if (child.material) {
        if (Array.isArray(child.material)) {
          child.material.forEach((m) => m.dispose())
        } else {
          child.material.dispose()
        }
      }
    })
    currentModel = null
  }
  if (objectUrl) {
    URL.revokeObjectURL(objectUrl)
    objectUrl = null
  }
}

async function loadModel(modelId) {
  if (!modelId || !scene) return
  loading.value = true
  error.value = ''
  clearModel()

  try {
    const res = await authStore.fetchWithAuth(`/api/models/${modelId}/glb`)
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${await res.text()}`)
    }
    const blob = await res.blob()
    objectUrl = URL.createObjectURL(blob)

    const loader = new GLTFLoader()
    loader.load(
      objectUrl,
      (gltf) => {
        currentModel = gltf.scene

        const box = new THREE.Box3().setFromObject(currentModel)
        const size = box.getSize(new THREE.Vector3())
        const center = box.getCenter(new THREE.Vector3())

        const maxDim = Math.max(size.x, size.y, size.z)
        const scale = maxDim > 0 ? 100 / maxDim : 1
        if (scale >= 0.001 && scale <= 1000 && (maxDim < 10 || maxDim > 500)) {
          currentModel.scale.setScalar(scale)
          box.setFromObject(currentModel)
          box.getCenter(center)
        }

        currentModel.position.sub(center)
        currentModel.position.y += size.y / 2

        scene.add(currentModel)

        controls.target.copy(new THREE.Vector3(0, size.y / 2, 0))
        const dist = maxDim * 1.8
        camera.position.set(dist, dist * 0.8, dist)
        controls.update()

        loading.value = false
      },
      undefined,
      (err) => {
        console.error('GLB parse error', err)
        error.value = '模型解析失败'
        loading.value = false
      }
    )
  } catch (err) {
    console.error('GLB fetch error', err)
    error.value = `加载失败: ${err.message}`
    loading.value = false
  }
}

function onResize() {
  if (!container.value || !camera || !renderer) return
  const w = container.value.clientWidth
  const h = container.value.clientHeight
  camera.aspect = w / h
  camera.updateProjectionMatrix()
  renderer.setSize(w, h)
}

onMounted(() => {
  initScene()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  if (renderer) {
    renderer.dispose()
    renderer.domElement.remove()
  }
})

watch(() => props.modelId, (id) => {
  if (id) loadModel(id)
})

defineExpose({ loadModel })
</script>

<style scoped>
.viewer {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.placeholder-text {
  text-align: center;
  color: #484f58;
  font-size: 16px;
  line-height: 1.6;
}

.loading {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  padding: 8px 16px;
  background: #1f6feb;
  color: #fff;
  border-radius: 20px;
  font-size: 13px;
  pointer-events: none;
}

.error-msg {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  padding: 12px 20px;
  background: #ff444433;
  color: #ff6b6b;
  border-radius: 8px;
  font-size: 14px;
  max-width: 80%;
  text-align: center;
}

.viewer-toolbar {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  gap: 8px;
  z-index: 10;
}

.toolbar-btn {
  padding: 6px 12px;
  background: #21262d;
  border: 1px solid #30363d;
  color: #c9d1d9;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.toolbar-btn:hover {
  background: #30363d;
}
</style>
