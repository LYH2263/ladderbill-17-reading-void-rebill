<script setup>
import { computed, onMounted, ref } from 'vue'
import { getJSON, postJSON } from '../api'

const items = ref([])
const activeOnly = ref(true)
const loading = ref(false)
const error = ref('')
const voidingId = ref(null)
const voidReason = ref('')
const notice = ref('')

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const data = await getJSON(`/api/readings?include_voided=${!activeOnly.value}`)
    items.value = data.items
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

const validItems = computed(() => items.value.filter((r) => !r.voided))
const validTotal = computed(() => validItems.value.reduce((s, r) => s + r.kwh, 0).toFixed(1))

const startVoid = (r) => {
  voidingId.value = r.id
  voidReason.value = ''
}
const cancelVoid = () => {
  voidingId.value = null
  voidReason.value = ''
}
const confirmVoid = async (r) => {
  const reason = voidReason.value.trim()
  if (!reason) {
    error.value = '作废原因必填'
    return
  }
  error.value = ''
  try {
    await postJSON(`/api/readings/${r.id}/void`, { reason })
    notice.value = `抄表 #${r.id} 已作废`
    cancelVoid()
    await load()
  } catch (e) {
    error.value = String(e.message || e)
  }
}

const retest = async (r) => {
  error.value = ''
  try {
    const out = await postJSON(`/api/readings/${r.id}/retest`, {})
    notice.value = `已基于抄表 #${r.id} 生成重测运行 #${out.run_id}（合计 ¥${out.total}），旧运行保留`
  } catch (e) {
    error.value = String(e.message || e)
  }
}
</script>
<template>
  <div class="page">
    <h1>抄表记录</h1>
    <div class="toolbar">
      <label class="switch">
        <input type="checkbox" v-model="activeOnly" @change="load" />
        仅看有效抄表
      </label>
      <button class="ghost" @click="load">刷新</button>
      <span class="muted">有效合计：<strong>{{ validTotal }}</strong> kWh（已作废不计入）</span>
    </div>
    <p v-if="notice" class="notice">{{ notice }}</p>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="loading" class="muted">加载中…</p>
    <table>
      <thead>
        <tr><th>#</th><th>户号</th><th>电量(kWh)</th><th>尖峰</th><th>状态</th><th>作废原因/时间</th><th>操作</th></tr>
      </thead>
      <tbody>
        <tr v-for="r in items" :key="r.id" :class="{ voided: r.voided }">
          <td>{{ r.id }}</td>
          <td>{{ r.account_id ?? '—' }}</td>
          <td>{{ r.kwh }}</td>
          <td>{{ r.peak ? '是' : '否' }}</td>
          <td>
            <span v-if="r.voided" class="tag tag-void">已作废</span>
            <span v-else class="tag tag-ok">有效</span>
          </td>
          <td class="muted">
            <template v-if="r.voided">
              {{ r.void_reason }}<br /><span class="ts">{{ r.voided_at }}</span>
            </template>
            —
          </td>
          <td>
            <template v-if="!r.voided">
              <button class="ghost" :disabled="voidingId === r.id" @click="startVoid(r)">作废</button>
              <button @click="retest(r)">重测</button>
              <div v-if="voidingId === r.id" class="void-form">
                <input
                  v-model="voidReason"
                  type="text"
                  placeholder="必填：作废原因"
                  @keyup.enter="confirmVoid(r)"
                />
                <button @click="confirmVoid(r)">确认作废</button>
                <button class="ghost" @click="cancelVoid">取消</button>
              </div>
            </template>
            <span v-else class="muted">禁止重测</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<style scoped>
.toolbar { display: flex; gap: 1rem; align-items: center; margin-bottom: 0.75rem; flex-wrap: wrap; }
.switch { user-select: none; }
.void-form { display: flex; gap: 0.4rem; margin-top: 0.4rem; flex-wrap: wrap; }
.void-form input { min-width: 12rem; }
tr.voided { opacity: 0.55; }
tr.voided td { text-decoration: line-through; }
tr.voided td:last-child, tr.voided .tag, tr.voided .ts { text-decoration: none; }
.tag { padding: 0.1rem 0.5rem; border-radius: 999px; font-size: 0.8rem; }
.tag-ok { background: color-mix(in srgb, var(--accent) 22%, transparent); color: var(--accent); }
.tag-void { background: color-mix(in srgb, #e56b6b 22%, transparent); color: #e58b8b; }
button.ghost { background: transparent; border: 1px solid var(--muted); color: var(--text); }
.notice { color: var(--accent); }
.error { color: #e58b8b; }
.ts { font-size: 0.78rem; }
</style>
