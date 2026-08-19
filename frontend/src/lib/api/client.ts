import type {
  ReaderResponse,
  ReferenceResolution,
  StructureNode,
  TextSummary,
  VersionSummary,
} from "@/types/api";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      message = body.detail ?? message;
    } catch {
      // Preserve the status-based fallback for non-JSON errors.
    }
    throw new ApiError(message, response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  texts: (signal?: AbortSignal) => apiFetch<TextSummary[]>("/api/v1/texts", signal),
  versions: (textSlug: string, signal?: AbortSignal) =>
    apiFetch<VersionSummary[]>(
      `/api/v1/texts/${encodeURIComponent(textSlug)}/versions`,
      signal,
    ),
  structure: (textSlug: string, signal?: AbortSignal) =>
    apiFetch<StructureNode[]>(
      `/api/v1/texts/${encodeURIComponent(textSlug)}/structure`,
      signal,
    ),
  children: (textSlug: string, nodeId: string, signal?: AbortSignal) =>
    apiFetch<StructureNode[]>(
      `/api/v1/texts/${encodeURIComponent(textSlug)}/structure/${encodeURIComponent(nodeId)}/children`,
      signal,
    ),
  resolveReference: (
    textSlug: string,
    reference: string,
    signal?: AbortSignal,
  ) =>
    apiFetch<ReferenceResolution>(
      `/api/v1/texts/${encodeURIComponent(textSlug)}/references/resolve?reference=${encodeURIComponent(reference)}`,
      signal,
    ),
  reader: (
    textSlug: string,
    reference: string,
    versions: string[],
    signal?: AbortSignal,
  ) => {
    const params = new URLSearchParams();
    if (versions.length) params.set("versions", versions.join(","));
    return apiFetch<ReaderResponse>(
      `/api/v1/reader/${encodeURIComponent(textSlug)}/${encodeURIComponent(reference)}?${params.toString()}`,
      signal,
    );
  },
};
