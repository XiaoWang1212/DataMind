import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export interface Framework {
  id: number
  title: string
  subtitle: string
  tag: string
  date: string
  variables: number
  paperTitle: string
  description: string
  independentVars: string[]
  dependentVars: string[]
  hypotheses: string[]
  workflowJson?: Record<string, unknown>
}

const STORAGE_KEY = 'datamind_frameworks'

const INITIAL_FRAMEWORKS: Framework[] = [
  {
    id: 1,
    title: 'CNN 圖像分類',
    subtitle: '深度殘差學習圖像識別',
    tag: 'CNN 架構',
    date: '2026-05-28',
    variables: 12,
    paperTitle: 'Deep Residual Learning for Image Recognition',
    description: 'A deep residual learning framework for image recognition tasks using convolutional neural networks with skip connections.',
    independentVars: ['network_depth', 'residual_blocks', 'learning_rate', 'batch_size', 'dropout_rate'],
    dependentVars: ['classification_accuracy', 'training_loss', 'validation_loss'],
    hypotheses: [
      'H1: Deeper networks with residual connections will achieve higher accuracy',
      'H2: Skip connections prevent gradient vanishing in deep networks',
    ],
  },
  {
    id: 2,
    title: '市場情緒回歸',
    subtitle: '使用社群媒體預測股市走勢',
    tag: '線性回歸',
    date: '2026-05-25',
    variables: 8,
    paperTitle: 'Predicting Stock Market Movements using Social Media',
    description: 'A regression model that predicts stock market movements based on sentiment analysis of social media posts.',
    independentVars: ['sentiment_score', 'post_volume', 'engagement_rate', 'user_influence'],
    dependentVars: ['stock_price_change', 'trading_volume'],
    hypotheses: [
      'H1: Positive sentiment correlates with stock price increases',
      'H2: High post volume predicts increased trading activity',
    ],
  },
  {
    id: 3,
    title: '用戶行為 RNN',
    subtitle: '用戶導航中的序列模式',
    tag: '遞歸神經網絡',
    date: '2026-05-20',
    variables: 15,
    paperTitle: 'Sequential Patterns in User Navigation',
    description: 'An RNN-based model for predicting user navigation patterns and next-page visits on websites.',
    independentVars: ['page_sequence', 'time_on_page', 'click_depth', 'session_duration', 'device_type'],
    dependentVars: ['next_page_prediction', 'bounce_probability', 'conversion_likelihood'],
    hypotheses: [
      'H1: Longer session duration increases conversion probability',
      'H2: Sequential patterns can predict user intent',
      'H3: Device type influences navigation behavior',
    ],
  },
]

function loadFromStorage (): { frameworks: Framework[]; nextId: number } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { frameworks: [...INITIAL_FRAMEWORKS], nextId: INITIAL_FRAMEWORKS.length + 1 }
    const parsed = JSON.parse(raw) as { frameworks: Framework[]; nextId: number }
    if (Array.isArray(parsed.frameworks) && parsed.frameworks.length > 0) return parsed
  } catch {
    // ignore
  }
  return { frameworks: [...INITIAL_FRAMEWORKS], nextId: INITIAL_FRAMEWORKS.length + 1 }
}

export const useFrameworkStore = defineStore('framework', () => {
  const saved = loadFromStorage()
  const frameworks = ref<Framework[]>(saved.frameworks)
  let nextId = saved.nextId

  watch(
    frameworks,
    (val) => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ frameworks: val, nextId }))
      } catch { /* ignore */ }
    },
    { deep: true },
  )

  function addFramework (fw: Omit<Framework, 'id'>): Framework {
    const newFw: Framework = { id: nextId++, ...fw }
    frameworks.value = [newFw, ...frameworks.value]
    return newFw
  }

  return { frameworks, addFramework }
})
