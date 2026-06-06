export async function analyzeWorkflowFromPdf (params: {
  file: File
  title?: string
  focus?: string
}): Promise<Record<string, unknown>> {
  const { file, title, focus } = params

  const formData = new FormData()
  formData.append('file', file, file.name)
  if (title) formData.append('title', title)
  if (focus) formData.append('focus', focus)

  const response = await fetch('/api/gemini/ai-analyze', {
    method: 'POST',
    body: formData,
  })

  const result = (await response.json()) as {
    success?: boolean
    result?: { workflow_json?: Record<string, unknown> }
    error?: string
  }

  if (!response.ok || !result.success) {
    throw new Error(result.error ?? `HTTP ${response.status}`)
  }

  const workflowJson = result.result?.workflow_json
  if (!workflowJson || typeof workflowJson !== 'object') {
    throw new Error('Gemini 回傳的 workflow_json 格式錯誤')
  }

  return workflowJson
}
