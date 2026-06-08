export async function executeWorkflowApiStream(params: {
  file: File
  workflowPayload: Record<string, unknown>
  onModelDone: (modelName: string, results: unknown[]) => void
  onDone: (result: Record<string, unknown>) => void
}): Promise<void> {
  const { file, workflowPayload, onModelDone, onDone } = params

  const formData = new FormData()
  formData.append('file', file, file.name || 'data.csv')
  formData.append('workflow_payload', JSON.stringify(workflowPayload))

  const response = await fetch('/api/models/workflow/execute-stream', {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const result = (await response.json()) as Record<string, unknown>
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  if (!response.body) throw new Error('Streaming not supported by this environment')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const event = JSON.parse(line.slice(6)) as Record<string, unknown>
          if (event.type === 'model_done') {
            onModelDone(
              String(event.model_name ?? ''),
              Array.isArray(event.results) ? event.results : [],
            )
          } else if (event.type === 'done') {
            onDone(event)
          } else if (event.type === 'error') {
            throw new Error(String(event.message ?? 'Workflow stream error'))
          }
        } catch (parseErr) {
          if (parseErr instanceof Error && parseErr.message !== 'Workflow stream error')
            continue
          throw parseErr
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

export async function executeWorkflowApi(params: {
  file: File;
  workflowPayload: Record<string, unknown>;
}): Promise<Record<string, unknown>> {
  const { file, workflowPayload } = params;

  const formData = new FormData();
  formData.append("file", file, file.name || "data.csv");
  formData.append("workflow_payload", JSON.stringify(workflowPayload));

  const response = await fetch("/api/models/workflow/execute", {
    method: "POST",
    body: formData,
  });

  const result = (await response.json()) as Record<string, unknown>;
  if (!response.ok) {
    throw new Error(
      result.error ? String(result.error) : `HTTP ${response.status}`,
    );
  }

  return result;
}

export async function fetchAvailableModels(): Promise<string[]> {
  const response = await fetch("/api/models/available");
  const result = (await response.json()) as {
    success?: boolean;
    models?: string[];
    error?: string;
  };
  if (!response.ok) {
    throw new Error(
      result.error ? String(result.error) : `HTTP ${response.status}`,
    );
  }

  return Array.isArray(result.models) ? result.models : [];
}
