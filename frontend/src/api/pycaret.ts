import type { PyCaretTrainResponse } from "@/types/pycaret";

export async function trainPyCaret(params: {
  file: File;
  targetCol: string;
  outputDir?: string;
}): Promise<PyCaretTrainResponse> {
  const { file, targetCol, outputDir = "artifacts/pycaret" } = params;

  const fd = new FormData();
  fd.append("file", file, file.name || "data.csv");
  fd.append("target_col", targetCol);
  fd.append("output_dir", outputDir);

  const res = await fetch("/api/ml/pycaret/train", {
    method: "POST",
    body: fd,
  });

  const data = (await res.json()) as PyCaretTrainResponse;
  if (!res.ok) {
    throw new Error(data.error || `HTTP ${res.status}`);
  }
  return data;
}
