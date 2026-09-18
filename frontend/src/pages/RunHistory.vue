<script setup>
import { computed, onMounted, ref } from 'vue'
import { getJSON } from '../api'

const raw = ref([])
onMounted(async () => { raw.value = (await getJSON('/api/history')).items })

const KIND_LABEL = { bill: '计费', compare: '尖峰对比', rerun: '重测' }
const summary = (row) => {
  try {
    const r = JSON.parse(row.result_json)
    return r.total != null ? `¥${r.total}` : `平${r.plain_total}/尖${r.peak_total}`
  } catch { return '—' }
}

// 同一抄表的旧运行与重测运行相邻并列：按引用抄表分组排序，组间以组内最新运行为准倒序；
// 未引用抄表的手工运行排在最后。
const items = computed(() => {
  const rows = [...raw.value]
  const latestByReading = new Map()
  for (const r of rows) {
    if (r.reading_id != null) {
      latestByReading.set(r.reading_id, Math.max(latestByReading.get(r.reading_id) ?? 0, r.id))
    }
  }
  return rows.sort((a, b) => {
    const ga = a.reading_id == null ? -1 : latestByReading.get(a.reading_id)
    const gb = b.reading_id == null ? -1 : latestByReading.get(b.reading_id)
    if (ga !== gb) return gb - ga
    return b.id - a.id
  })
})

// 渲染用：同一抄表分组只在首行画一条分组色条
const groupFirst = computed(() => {
  const seen = new Set()
  const first = new Set()
  for (const r of items.value) {
    if (r.reading_id != null && !seen.has(r.reading_id)) {
      seen.add(r.reading_id)
      first.add(r.id)
    }
  }
  return first
})
</script>

<template>
  <div class="page">
    <h1>测算记录</h1>
    <p class="muted">重测会生成新运行并引用对应抄表，旧运行保留不覆盖；同一抄表的运行相邻并列展示。</p>
    <table>
      <thead>
        <tr><th>#</th><th>类型</th><th>户号</th><th>引用抄表</th><th>结果摘要</th><th>时间</th></tr>
      </thead>
      <tbody>
        <tr v-for="h in items" :key="h.id" :class="{ 'group-first': groupFirst.has(h.id) }">
          <td>{{ h.id }}</td>
          <td>
            {{ KIND_LABEL[h.kind] ?? h.kind }}
            <span v-if="h.kind === 'rerun'" class="tag rerun">重测</span>
          </td>
          <td>{{ h.account_id ?? '—' }}</td>
          <td>
            <span v-if="h.reading_id != null" class="tag reading">抄表 #{{ h.reading_id }}</span>
            <span v-else class="muted">手工录入</span>
          </td>
          <td>{{ summary(h) }}</td>
          <td class="muted">{{ h.created_at }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.tag { padding: 0.1rem 0.45rem; border-radius: 999px; font-size: 0.75rem; margin-left: 0.3rem; }
.tag.rerun { background: color-mix(in srgb, #e6a817 22%, transparent); color: #e6b84d; }
.tag.reading { background: color-mix(in srgb, var(--accent) 20%, transparent); color: var(--accent); }
tr.group-first td { border-top: 2px solid color-mix(in srgb, var(--accent) 45%, transparent); }
</style>
