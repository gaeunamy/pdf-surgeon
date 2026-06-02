export type Mode = "smart" | "manual" | "mask";

export interface ReplaceEntry {
  id: string;
  from: string;
  to: string;
}

export interface ProcessState {
  status: "idle" | "loading" | "success" | "error";
  resultBlob: Blob | null;
  errorMessage: string;
}
