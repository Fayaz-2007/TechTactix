/**
 * All requests use relative paths only (e.g. "/api/chat") so the exact same
 * build works whether the browser is on the same laptop as the backend or
 * on a second laptop reaching it over the LAN through a reverse proxy /
 * the same origin the frontend was served from.
 */

async function readErrorDetail(response) {
  try {
    const body = await response.json();
    return body.detail || `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

// Mirrors backend/modules/ingestion/routes.py's MAX_FILES_PER_UPLOAD / MAX_UPLOAD_SIZE_BYTES.
export const MAX_UPLOAD_FILES = 5;
export const MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024;

/**
 * Upload up to MAX_UPLOAD_FILES documents in one batch for OCR/extraction +
 * indexing. Each file is processed independently server-side, so one
 * corrupt/oversized file doesn't fail the rest of the batch.
 * @param {File[]} files
 * @param {string|null} projectId - tag the documents with this project, or
 *   null to leave them unscoped (searchable from every project/"All documents").
 * @returns {Promise<Array<{document_id: string|null, filename: string, chunks_indexed: number, status: "success"|"error", error: string|null}>>}
 */
export async function uploadDocuments(files, projectId) {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  if (projectId) {
    formData.append("project_id", projectId);
  }

  const response = await fetch("/api/upload", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }

  return response.json();
}

/**
 * Upload a single document. Thin wrapper over uploadDocuments() that keeps
 * the original single-file call shape used by the top upload panel.
 * @param {File} file
 * @param {string|null} projectId
 * @returns {Promise<{document_id: string, filename: string, chunks_indexed: number, status: string}>}
 */
export async function uploadDocument(file, projectId) {
  const [result] = await uploadDocuments([file], projectId);
  if (result.status === "error") {
    throw new Error(result.error || "Upload failed.");
  }
  return result;
}

/**
 * Stream a chat answer over SSE. Uses fetch + a manual ReadableStream
 * reader (rather than EventSource) because EventSource cannot send a POST
 * body.
 *
 * @param {string} query
 * @param {string|null} documentId
 * @param {string|null} sessionId - existing session to append to, or null
 *   to let the server create a new one (its id comes back via onDone).
 * @param {string|null} projectId - restrict retrieval to this project's
 *   documents; null searches everything ("All documents").
 * @param {(token: string) => void} onToken
 * @param {(message: string) => void} onStatus - real pipeline status
 *   updates (e.g. retrieval starting, retrieval result, generation
 *   starting), fired zero or more times before the first token.
 * @param {(sources: Array<object>, sessionId: string|null) => void} onDone
 * @param {(message: string) => void} onError
 */
export async function streamChat(query, documentId, sessionId, projectId, onToken, onStatus, onDone, onError) {
  let response;
  try {
    response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        document_id: documentId ?? null,
        session_id: sessionId ?? null,
        project_id: projectId ?? null,
      }),
    });
  } catch (err) {
    onError(err.message || "Could not reach the server.");
    return;
  }

  if (!response.ok || !response.body) {
    onError(await readErrorDetail(response));
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE events are separated by a blank line.
      const rawEvents = buffer.split("\n\n");
      buffer = rawEvents.pop() ?? ""; // last piece may be incomplete

      for (const rawEvent of rawEvents) {
        const dataLine = rawEvent
          .split("\n")
          .find((line) => line.startsWith("data:"));
        if (!dataLine) continue;

        const jsonText = dataLine.slice(dataLine.indexOf(":") + 1).trim();
        if (!jsonText) continue;

        let payload;
        try {
          payload = JSON.parse(jsonText);
        } catch {
          continue;
        }

        if (payload.error) {
          onError(payload.error);
          return;
        }
        if (payload.type === "status") {
          onStatus(payload.message || "");
          continue;
        }
        if (payload.type === "done") {
          onDone(payload.sources || [], payload.session_id ?? null);
          return;
        }
        if (payload.type === "token" && typeof payload.token === "string") {
          onToken(payload.token);
        }
      }
    }
  } catch (err) {
    onError(err.message || "Connection to server was interrupted.");
  }
}

/**
 * Request a generated report and trigger a browser download of it.
 * @param {string} query
 * @param {string} answer
 * @param {Array<object>} sources
 * @param {"docx"|"xlsx"} format
 */
export async function generateReport(query, answer, sources, format) {
  const response = await fetch("/api/generate-report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, answer, sources, format }),
  });

  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `report.${format}`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Poll-friendly status check for the offline/network monitor.
 * @returns {Promise<{external_connections: number, local_connections: number, status: "clean"|"alert"}>}
 */
export async function getMonitorStatus() {
  const response = await fetch("/api/monitor");
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
  return response.json();
}

/**
 * List chat sessions, newest first, optionally scoped to one project.
 * @param {string|null} [projectId] - if given, only that project's sessions.
 * @returns {Promise<Array<{id: string, title: string, project_id: string|null, created_at: string}>>}
 */
export async function getHistory(projectId) {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  const response = await fetch(`/api/history${query}`);
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
  return response.json();
}

/**
 * List all projects, newest first.
 * @returns {Promise<Array<{id: string, name: string, created_at: string}>>}
 */
export async function getProjects() {
  const response = await fetch("/api/projects");
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
  return response.json();
}

/**
 * Create a new project.
 * @param {string} name
 * @returns {Promise<{id: string, name: string}>}
 */
export async function createProject(name) {
  const response = await fetch("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
  return response.json();
}

/**
 * Fetch the full message list for one past session.
 * @param {string} sessionId
 * @returns {Promise<Array<{id: number, role: string, content: string, sources: Array<object>, created_at: string}>>}
 */
export async function getSessionMessages(sessionId) {
  const response = await fetch(`/api/history/${encodeURIComponent(sessionId)}`);
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
  return response.json();
}

/**
 * Permanently delete a past chat session.
 * @param {string} sessionId
 * @returns {Promise<{status: string, session_id: string}>}
 */
export async function deleteSession(sessionId) {
  const response = await fetch(`/api/history/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
  return response.json();
}
