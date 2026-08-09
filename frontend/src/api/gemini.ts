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

export async function streamAnalyzeWorkflowFromPdf (
  params: { file: File, title?: string },
  callbacks: {
    onThought: (text: string) => void
    onResult: (workflowJson: Record<string, unknown>) => void
    onError: (message: string) => void
  },
): Promise<void> {
  const { file, title } = params
  const { onThought, onResult, onError } = callbacks

  const formData = new FormData()
  formData.append('file', file, file.name)
  if (title) formData.append('title', title)

  const response = await fetch('/api/gemini/ai-analyze/stream', {
    method: 'POST',
    body: formData,
  })

  if (!response.ok || !response.body) {
    const result = (await response.json().catch(() => null)) as { error?: string } | null
    onError(result?.error ?? `HTTP ${response.status}`)
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let boundary = buffer.indexOf('\n\n')
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)

      let eventType = 'message'
      let dataLine = ''
      for (const line of rawEvent.split('\n')) {
        if (line.startsWith('event: ')) eventType = line.slice(7)
        else if (line.startsWith('data: ')) dataLine = line.slice(6)
      }

      if (dataLine) {
        const payload = JSON.parse(dataLine) as Record<string, unknown>
        if (eventType === 'thought' && typeof payload.text === 'string') {
          onThought(payload.text)
        } else if (eventType === 'result') {
          const data = payload.data as { workflow_json?: Record<string, unknown> } | undefined
          const workflowJson = data?.workflow_json
          if (workflowJson && typeof workflowJson === 'object') {
            onResult(workflowJson)
          } else {
            onError('Gemini 回傳的 workflow_json 格式錯誤')
          }
        } else if (eventType === 'error' && typeof payload.message === 'string') {
          onError(payload.message)
        }
      }

      boundary = buffer.indexOf('\n\n')
    }
  }
}
