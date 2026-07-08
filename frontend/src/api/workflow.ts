export async function startWorkflowJob (params: {
  file: File
  workflowPayload: Record<string, unknown>
}): Promise<{ jobId: string, totalModels: number }> {
  const { file, workflowPayload } = params

  const formData = new FormData()
  formData.append('file', file, file.name || 'data.csv')
  formData.append('workflow_payload', JSON.stringify(workflowPayload))

  const response = await fetch('/api/models/workflow/jobs', {
    method: 'POST',
    body: formData,
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return { jobId: String(result.job_id ?? ''), totalModels: Number(result.total_models ?? 0) }
}

export interface WorkflowJobStatus {
  status: 'running' | 'done' | 'error'
  totalModels: number
  completedModels: string[]
  result: Record<string, unknown> | null
  error: string | null
}

export async function fetchWorkflowJob (jobId: string): Promise<WorkflowJobStatus> {
  const response = await fetch(`/api/models/workflow/jobs/${jobId}`)
  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return {
    status: result.status as WorkflowJobStatus['status'],
    totalModels: Number(result.total_models ?? 0),
    completedModels: Array.isArray(result.completed_models) ? result.completed_models.map(String) : [],
    result: (result.result as Record<string, unknown> | null) ?? null,
    error: result.error ? String(result.error) : null,
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
