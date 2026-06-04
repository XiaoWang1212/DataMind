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
