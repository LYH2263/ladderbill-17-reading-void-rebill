<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'
const items = ref([])
onMounted(async () => { items.value = (await getJSON('/api/history')).items })
const summary = (row) => {
  try { const r = JSON.parse(row.result_json); return r.total != null ? `¥${r.total}` : `平${r.plain_total}/尖${r.peak_total}` } catch { return '—' }
}
const kindLabel = (kind) => ({ bill: '电费测算', compare: '尖峰对比', retest: '重测' }[kind] || kind)
</script>
<template>
  <div class="page">
    <h1>测算记录</h1>
    <p class="muted">重测会生成一条新运行并保留旧运行；同一抄表的原运行与重测运行并列展示。</p>
    <table>
      <thead><tr><th>#</th><th>类型</th><th>户号</th><th>来源抄表</th><th>结果摘要</th><th>时间</th></tr></thead>
      <tbody>
        <tr v-for="h in items" :key="h.id" :class="{ retest: h.kind === 'retest' }">
          <td>{{ h.id }}</td>
          <td>
            {{ kindLabel(h.kind) }}
            <span v-if="h.kind === 'retest'" class="tag">重测</span>
          </td>
          <td>{{ h.account_id ?? '—' }}</td>
          <td>{{ h.reading_id ?? '—' }}</td>
          <td>{{ summary(h) }}</td>
          <td class="muted">{{ h.created_at }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<style scoped>
tr.retest { background: color-mix(in srgb, var(--accent) 8%, transparent); }
.tag { margin-left: 0.35rem; padding: 0.05rem 0.45rem; border-radius: 999px; font-size: 0.75rem;
  background: color-mix(in srgb, var(--accent) 22%, transparent); color: var(--accent); }
</style>
