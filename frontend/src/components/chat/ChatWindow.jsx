import { useEffect, useRef, useState } from "react";
import { MAX_FILE_SIZE_BYTES, MAX_UPLOAD_FILES, streamChat, uploadDocuments } from "../../api/client";
import AttachButton from "./AttachButton.jsx";
import AttachmentChips from "./AttachmentChips.jsx";
import "./ChatWindow.css";

function mapStoredMessages(initialMessages) {
  return (initialMessages || []).map((message) => ({
    role: message.role,
    text: message.content,
    sources: message.sources || [],
    isStreaming: false,
    isError: false,
  }));
}

/**
 * Chat interface with token-by-token streaming and source citations.
 *
 * @param {{
 *   documentId?: string|null,
 *   sessionId?: string|null,
 *   projectId?: string|null,
 *   initialMessages?: Array<{role: string, content: string, sources: Array<object>}>,
 *   onStageChange?: (stage: string|null) => void,
 *   onAnswerReady?: (payload: {query: string, answer: string, sources: Array<object>}) => void,
 *   onSessionChange?: (sessionId: string) => void,
 * }} props
 *
 * `sessionId` and `initialMessages` only seed this component's state on
 * mount — the parent forces a remount (via a changing `key`) whenever the
 * user explicitly starts a new chat or opens a different past session.
 * Within one mount, the session id learned back from the server after the
 * first message is tracked locally so later messages keep appending to it.
 * `projectId` is read fresh on every send (not just at mount) so switching
 * the active project in the sidebar re-scopes the very next message.
 */
function ChatWindow({ documentId, sessionId, projectId, initialMessages, onStageChange, onAnswerReady, onSessionChange }) {
  const [messages, setMessages] = useState(() => mapStoredMessages(initialMessages));
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [attachments, setAttachments] = useState([]);
  const [isAttaching, setIsAttaching] = useState(false);
  const messagesEndRef = useRef(null);
  const sessionIdRef = useRef(sessionId ?? null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const updateLastMessage = (updater) => {
    setMessages((prev) => {
      if (prev.length === 0) return prev;
      const next = [...prev];
      const lastIndex = next.length - 1;
      next[lastIndex] = updater(next[lastIndex]);
      return next;
    });
  };

  const handleSend = () => {
    const query = input.trim();
    if (!query || isSending) return;

    setInput("");
    setIsSending(true);
    setMessages((prev) => [
      ...prev,
      { role: "user", text: query },
      { role: "assistant", text: "", sources: null, isStreaming: true, isError: false, statusMessage: null },
    ]);

    onStageChange?.("retrieve");

    let firstTokenSeen = false;
    let fullAnswer = "";

    streamChat(
      query,
      documentId,
      sessionIdRef.current,
      projectId,
      (token) => {
        if (!firstTokenSeen) {
          firstTokenSeen = true;
          onStageChange?.("generate");
        }
        fullAnswer += token;
        updateLastMessage((msg) => ({ ...msg, text: msg.text + token, statusMessage: null }));
      },
      (statusMessage) => {
        updateLastMessage((msg) => ({ ...msg, statusMessage }));
      },
      (sources, returnedSessionId) => {
        updateLastMessage((msg) => ({ ...msg, isStreaming: false, sources: sources || [] }));
        setIsSending(false);
        onStageChange?.(null);
        onAnswerReady?.({ query, answer: fullAnswer, sources: sources || [] });
        if (returnedSessionId && returnedSessionId !== sessionIdRef.current) {
          sessionIdRef.current = returnedSessionId;
          onSessionChange?.(returnedSessionId);
        }
      },
      (errorMessage) => {
        updateLastMessage((msg) => ({
          ...msg,
          isStreaming: false,
          isError: true,
          text: msg.text || errorMessage || "Something went wrong.",
        }));
        setIsSending(false);
        onStageChange?.(null);
      }
    );
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  const makeChipId = (file) => `${file.name}-${file.lastModified}-${file.size}`;

  // Attaching is a separate action from sending a chat message — files are
  // uploaded/indexed immediately, the same as the top upload panel, rather
  // than waiting on the next chat send.
  const handleFilesSelected = async (files) => {
    if (files.length > MAX_UPLOAD_FILES) {
      setAttachments((prev) => [
        ...prev,
        {
          id: `limit-${Date.now()}`,
          name: `${files.length} files selected`,
          status: "error",
          error: "Upload up to 5 files at a time",
        },
      ]);
      return;
    }

    const oversized = files.filter((file) => file.size > MAX_FILE_SIZE_BYTES);
    const uploadable = files.filter((file) => file.size <= MAX_FILE_SIZE_BYTES);

    const oversizedChips = oversized.map((file) => ({
      id: makeChipId(file),
      name: file.name,
      status: "error",
      error: "File exceeds 15MB limit",
    }));
    const uploadingChips = uploadable.map((file) => ({
      id: makeChipId(file),
      name: file.name,
      status: "uploading",
      error: null,
    }));

    setAttachments((prev) => [...prev, ...uploadingChips, ...oversizedChips]);

    if (uploadable.length === 0) return;

    setIsAttaching(true);
    try {
      const results = await uploadDocuments(uploadable, projectId);
      setAttachments((prev) => {
        const next = [...prev];
        uploadable.forEach((file, index) => {
          const result = results[index];
          if (!result) return;
          const chipIndex = next.findIndex((chip) => chip.id === makeChipId(file));
          if (chipIndex !== -1) {
            next[chipIndex] = { ...next[chipIndex], status: result.status, error: result.error };
          }
        });
        return next;
      });
    } catch (err) {
      const message = err.message || "Upload failed.";
      setAttachments((prev) =>
        prev.map((chip) =>
          uploadingChips.some((uploading) => uploading.id === chip.id)
            ? { ...chip, status: "error", error: message }
            : chip
        )
      );
    } finally {
      setIsAttaching(false);
    }
  };

  return (
    <div className="chat-window">
      <div className="chat-window__messages">
        {messages.length === 0 && (
          <div className="chat-window__empty">
            Ask a question about your uploaded documents to get started.
          </div>
        )}

        {messages.map((message, index) => (
          <div
            key={index}
            className={"chat-message chat-message--" + message.role}
          >
            {message.role === "assistant" && message.isStreaming && message.statusMessage && !message.text && (
              <div className="chat-message__status">{message.statusMessage}</div>
            )}

            <div
              className={
                "chat-message__bubble chat-message__bubble--" +
                message.role +
                (message.isError ? " chat-message__bubble--error" : "")
              }
            >
              {message.text}
              {message.isStreaming && <span className="chat-message__cursor" />}
            </div>

            {message.role === "assistant" &&
              !message.isStreaming &&
              !message.isError &&
              message.sources &&
              message.sources.length > 0 && (
                <div className="chat-message__sources">
                  <div className="chat-message__sources-label">Sources</div>
                  <div className="chat-message__sources-list">
                    {message.sources.map((source, sourceIndex) => (
                      <span className="chat-message__source-chip" key={sourceIndex}>
                        {source.filename || source.document_id || "unknown"}
                        {typeof source.score === "number" && (
                          <span className="chat-message__source-score">
                            {source.score.toFixed(2)}
                          </span>
                        )}
                      </span>
                    ))}
                  </div>
                </div>
              )}
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>

      <AttachmentChips chips={attachments} />

      <div className="chat-window__input-row">
        <AttachButton onFilesSelected={handleFilesSelected} disabled={isAttaching} />
        <textarea
          className="chat-window__input"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your documents…"
          rows={1}
          disabled={isSending}
        />
        <button
          className="chat-window__send-button"
          onClick={handleSend}
          disabled={isSending || !input.trim()}
        >
          {isSending ? "Sending…" : "Send"}
        </button>
      </div>
    </div>
  );
}

export default ChatWindow;
