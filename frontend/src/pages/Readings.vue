<script setup>
import { computed, onMounted, ref } from 'vue'
import { getJSON, postJSON } from '../api'

const items = ref([])
const accounts = ref([])
const filter = ref('valid') // valid | all | voided
const loading = ref(false)
const notice = ref('')
const error = ref('')

// 作废弹层
const voidTarget = ref(null)
const voidReason = ref('')

const accountName = (id) => accounts.value.find((a) => a.id === id)?.name ?? `户号${id}`

const filtered = computed(() => {
  if (filter.value === 'valid') return items.value.filter((r) => !r.voided)
  if (filter.value === 'voided') return items.value.filter((r) => r.voided)
  return items.value
})

// 默认合计只统计有效抄表，作废抄表不参与
const validTotal = computed(() =>
  items.value.filter((r) => !r.voided).reduce((s, r) => s + r.kwh, 0),
)
const validPeak = computed(() => items.value.filter((r) => !r.voided && r.peak).length)

const load = async () => {
  // 一次拉全量（含作废），过滤在前端切换；详情里作废原因同样可见
  const [rs, as] = await Promise.all([
    getJSON('/api/readings?include_voided=true'),
    getJSON('/api/accounts'),
  ])
  items.value = rs.items
  accounts.value = as.items
}
onMounted(load)

const openVoid = (row) => {
  voidTarget.value = row
  voidReason.value = ''
  error.value = ''
}
const closeVoid = () => {
  voidTarget.value = null
  voidReason.value = ''
}
const confirmVoid = async () => {
  if (!voidReason.value.trim()) {
    error.value = '作废原因必填'
    return
  }
  try {
    await postJSON(`/api/readings/${voidTarget.value.id}/void`, {
      reason: voidReason.value.trim(),
    })
    notice.value = `抄表 #${voidTarget.value.id} 已作废`
    closeVoid()
    await load()
  } catch (e) {
    error.value = String(e.message || e)
  }
}

const rerun = async (row) => {
  loading.value = true
  error.value = ''
  try {
    const r = await postJSON(`/api/readings/${row.id}/rerun`, {})
    notice.value = `已基于抄表 #${row.id} 生成重测运行 #${r.run_id}，合计 ¥${r.total}；原运行保留`
  } catch (e) {
    error.value = String(e.message || e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page">
    <h1>抄表记录</h1>

    <div class="panel toolbar">
      <div class="filters">
        <button
          v-for="f in [['valid','有效'],['all','全部'],['voided','已作废']]"
          :key="f[0]"
          :class="{ active: filter === f[0] }"
          @click="filter = f[0]"
        >{{ f[1] }}</button>
      </div>
      <div class="sum muted">
        有效合计 <strong class="hero-num" style="font-size:1.4rem">{{ validTotal }}</strong> kWh
        · 尖峰 {{ validPeak }} 条
        <span class="hint">（已作废抄表不计入合计与重测候选）</span>
      </div>
    </div>

    <p v-if="notice" class="notice" @click="notice = ''">{{ notice }} ✕</p>
    <p v-if="error" class="error" @click="error = ''">{{ error }} ✕</p>

    <table>
      <thead>
        <tr><th>#</th><th>户号</th><th>电量(kWh)</th><th>尖峰</th><th>状态</th><th>操作</th></tr>
      </thead>
      <tbody>
        <tr v-for="r in filtered" :key="r.id" :class="{ voidrow: r.voided }">
          <td>{{ r.id }}</td>
          <td>{{ accountName(r.account_id) }}</td>
          <td>{{ r.kwh }}</td>
          <td>{{ r.peak ? '是' : '否' }}</td>
          <td>
            <span v-if="!r.voided" class="tag ok">有效</span>
            <template v-else>
              <span class="tag void">已作废</span>
              <span class="muted reason">原因：{{ r.void_reason }}</span>
            </template>
          </td>
          <td>
            <template v-if="!r.voided">
              <button class="btn-rerun" :disabled="loading" @click="rerun(r)">重测</button>
              <button class="btn-void" @click="openVoid(r)">作废</button>
            </template>
            <span v-else class="muted">禁止重测</span>
          </td>
        </tr>
        <tr v-if="!filtered.length"><td colspan="6" class="muted">暂无数据</td></tr>
      </tbody>
    </table>

    <div v-if="voidTarget" class="modal-mask" @click.self="closeVoid">
      <div class="modal panel">
        <h3>作废抄表 #{{ voidTarget.id }}</h3>
        <p class="muted">
          {{ accountName(voidTarget.account_id) }} · {{ voidTarget.kwh }} kWh ·
          {{ voidTarget.peak ? '尖峰' : '普通' }}
        </p>
        <label>作废原因（必填）
          <input
            v-model="voidReason"
            type="text"
            placeholder="例如：表计故障 / 录入错误"
            @keyup.enter="confirmVoid"
          />
        </label>
        <p v-if="error" class="error">{{ error }}</p>
        <div class="modal-actions">
          <button class="btn-void" @click="confirmVoid">确认作废</button>
          <button class="btn-cancel" @click="closeVoid">取消</button>
        </div>
        <p class="muted hint">作废后该抄表不参与列表合计与测算，详情仍可查询。</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; justify-content: space-between; }
.filters { display: flex; gap: 0.4rem; }
.filters button { background: transparent; color: var(--muted); border: 1px solid var(--muted); }
.filters button.active { background: var(--accent); color: #111; border-color: var(--accent); }
.sum { font-size: 0.95rem; }
.hint { font-size: 0.8rem; margin-left: 0.35rem; }
.tag { padding: 0.1rem 0.5rem; border-radius: 999px; font-size: 0.78rem; }
.tag.ok { background: color-mix(in srgb, var(--accent) 20%, transparent); color: var(--accent); }
.tag.void { background: color-mix(in srgb, #e56b6b 22%, transparent); color: #e58b8b; }
.reason { margin-left: 0.4rem; font-size: 0.85rem; }
.voidrow td { opacity: 0.55; }
.btn-rerun { margin-right: 0.4rem; }
.btn-void { background: #b44b4b; color: #fff; }
.btn-cancel { background: transparent; color: var(--text); border: 1px solid var(--muted); }
.notice { background: color-mix(in srgb, var(--accent) 16%, transparent); border: 1px solid var(--accent); padding: 0.5rem 0.75rem; border-radius: 8px; cursor: pointer; }
.error { background: color-mix(in srgb, #e56b6b 16%, transparent); border: 1px solid #e56b6b; padding: 0.5rem 0.75rem; border-radius: 8px; }
.modal-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,0.55);
  display: flex; align-items: center; justify-content: center;
}
.modal { width: min(26rem, 92vw); margin: 0; }
.modal label { display: block; margin: 0.6rem 0; }
.modal input { width: 100%; margin-top: 0.35rem; }
.modal-actions { display: flex; gap: 0.5rem; margin-top: 0.75rem; }
</style>
