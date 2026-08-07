export const RELATION_MATCH_DIMENSIONS = [
  { key: 'dominance', label: '主导', hint: '推动、决策、引导倾向' },
  { key: 'care', label: '照顾', hint: '安抚、照料、承担感' },
  { key: 'dependence', label: '依赖', hint: '需要陪伴、需要回应的倾向' },
  { key: 'empathy', label: '共情', hint: '理解情绪、换位思考的倾向' },
  { key: 'romance', label: '浪漫', hint: '仪式感、亲密表达、氛围感' },
  { key: 'playfulness', label: '玩乐', hint: '幽默、轻松、一起找乐子' },
  { key: 'stability', label: '稳定', hint: '持续性、踏实感、可依赖程度' },
  { key: 'maturity', label: '成熟', hint: '沟通、边界感、处理问题能力' },
]

export const RELATION_MATCH_QUESTION_TYPES = {
  single_choice: '单选',
  scale: '量表',
  multi_select: '多选',
  either_or: '二选一',
}

export const RELATION_MATCH_TYPES = {
  bestie: '死党型',
  siblings: '兄弟/姐妹型',
  childhood_friend: '青梅竹马型',
  confidant: '知己型',
  teacher_student: '师生型',
  twin: '双胞胎型',
  frienemy: '欢喜冤家型',
  companion: '陪伴型',
  complementary: '互补型',
  mirror: '镜像型',
  contrast: '反差型',
  healing: '治愈型',
  growing: '成长型',
  adventure: '冒险型',
  harbor: '港湾型',
  parent_child: '亲子型',
}

export function getRelationMatchTypeName(type) {
  return RELATION_MATCH_TYPES[type] || type || '关系型'
}

export function getRelationMatchQuestionTypeLabel(type) {
  return RELATION_MATCH_QUESTION_TYPES[type] || '题目'
}

export function normalizeRelationMatchQueryValue(value) {
  if (Array.isArray(value)) return value[0] || ''
  return typeof value === 'string' ? value : ''
}

export function formatRelationMatchTendency(tendency) {
  if (tendency === 'a') return 'A 方更高'
  if (tendency === 'b') return 'B 方更高'
  if (tendency === 'equal') return '双方持平'
  return '未知'
}

export function buildRelationMatchDimensionInsight(row) {
  const label = row?.label || '该维度'
  const shared = Number(row?.shared) || 0
  const gap = Number(row?.gap) || 0
  const tendency = formatRelationMatchTendency(row?.tendency)
  if (row?.tendency === 'equal') {
    return `双方在${label}上的共同值为 ${shared}/10，差值为 ${gap}/10，整体表现接近。`
  }
  return `双方在${label}上的共同值为 ${shared}/10，差值为 ${gap}/10，整体更偏向 ${tendency}。`
}

export function buildRelationMatchAbsoluteUrl(path) {
  if (typeof window === 'undefined' || !path) return ''
  return new URL(path, window.location.origin).href
}

export function extractRelationMatchPairId(result) {
  const raw = result?.pair_id ?? result?.id ?? ''
  if (typeof raw === 'number' && Number.isFinite(raw)) return String(raw)
  if (typeof raw === 'string' && raw.trim()) return raw.trim()

  const url = result?.share_url || result?.result_url || ''
  const match = String(url).match(/\/(\d+)\/?$/)
  return match ? match[1] : ''
}
