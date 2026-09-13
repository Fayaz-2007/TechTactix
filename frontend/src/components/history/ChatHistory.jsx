import { useEffect, useRef, useState } from "react";
import {
  Check,
  ChevronDown,
  FolderKanban,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
} from "lucide-react";
import { createProject, getHistory, getProjects, getSessionMessages } from "../../api/client";
import "./ChatHistory.css";

function formatRelativeTime(isoString) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "";

  const diffSec = Math.round((Date.now() - date.getTime()) / 1000);
  if (diffSec < 60) return "just now";

  const diffMin = Math.round(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;

  const diffHour = Math.round(diffMin / 60);
  if (diffHour < 24) return `${diffHour}h ago`;

  const diffDay = Math.round(diffHour / 24);
  if (diffDay === 1) return "Yesterday";
  if (diffDay < 7) return `${diffDay}d ago`;

  return date.toLocaleDateString();
}

/**
 * Collapsible left sidebar: project selector, "+ New chat", and the
 * project-filtered session list. Everything it shows comes from the
 * server (not localStorage) so it's identical no matter which screen, or
 * which laptop over LAN, is looking at it.
 *
 * @param {{
 *   activeSessionId?: string|null,
 *   activeProjectId?: string|null,
 *   onNewChat: () => void,
 *   onSelectSession: (sessionId: string, messages: Array<object>, projectId: string|null) => void,
 *   onProjectChange: (projectId: string|null) => void,
 *   refreshToken?: number,
 * }} props
 */
function ChatHistory({
  activeSessionId,
  activeProjectId,
  onNewChat,
  onSelectSession,
  onProjectChange,
  refreshToken,
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [projects, setProjects] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [loadingSessionId, setLoadingSessionId] = useState(null);
  const [error, setError] = useState(null);

  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [isSavingProject, setIsSavingProject] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    getProjects()
      .then(setProjects)
      .catch(() => {
        /* project selector just shows "All documents" if this fails */
      });
  }, [refreshToken]);

  useEffect(() => {
    let cancelled = false;

    getHistory(activeProjectId)
      .then((result) => {
        if (!cancelled) setSessions(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "Could not load chat history.");
      });

    return () => {
      cancelled = true;
    };
  }, [activeProjectId, refreshToken]);

  useEffect(() => {
    if (!dropdownOpen) return undefined;

    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
        setIsCreatingProject(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [dropdownOpen]);

  const activeProject = projects.find((project) => project.id === activeProjectId) || null;

  const handleSelect = async (sessionId, projectId) => {
    if (loadingSessionId) return;
    setLoadingSessionId(sessionId);
    setError(null);
    try {
      const messages = await getSessionMessages(sessionId);
      onSelectSession(sessionId, messages, projectId ?? null);
    } catch (err) {
      setError(err.message || "Could not load that conversation.");
    } finally {
      setLoadingSessionId(null);
    }
  };

  const handlePickProject = (projectId) => {
    onProjectChange(projectId);
    setDropdownOpen(false);
    setIsCreatingProject(false);
  };

  const handleCreateProject = async (event) => {
    event.preventDefault();
    const name = newProjectName.trim();
    if (!name || isSavingProject) return;

    setIsSavingProject(true);
    setError(null);
    try {
      const project = await createProject(name);
      setProjects((prev) => [{ ...project, created_at: new Date().toISOString() }, ...prev]);
      setNewProjectName("");
      setIsCreatingProject(false);
      setDropdownOpen(false);
      onProjectChange(project.id);
    } catch (err) {
      setError(err.message || "Could not create project.");
    } finally {
      setIsSavingProject(false);
    }
  };

  if (collapsed) {
    return (
      <aside className="chat-history chat-history--collapsed">
        <button
          className="chat-history__collapse-toggle"
          onClick={() => setCollapsed(false)}
          title="Expand sidebar"
          aria-label="Expand sidebar"
        >
          <PanelLeftOpen size={18} />
        </button>
        <button
          className="chat-history__collapsed-new-chat"
          onClick={onNewChat}
          title="New chat"
          aria-label="New chat"
        >
          <Plus size={18} />
        </button>
      </aside>
    );
  }

  return (
    <aside className="chat-history">
      <div className="chat-history__top-row">
        <span className="chat-history__brand">Chats</span>
        <button
          className="chat-history__collapse-toggle"
          onClick={() => setCollapsed(true)}
          title="Collapse sidebar"
          aria-label="Collapse sidebar"
        >
          <PanelLeftClose size={18} />
        </button>
      </div>

      <div className="chat-history__project-picker" ref={dropdownRef}>
        <button
          className="chat-history__project-trigger"
          onClick={() => setDropdownOpen((open) => !open)}
        >
          <FolderKanban size={15} className="chat-history__project-trigger-icon" />
          <span className="chat-history__project-trigger-label">
            {activeProject ? activeProject.name : "All documents"}
          </span>
          <ChevronDown size={14} className="chat-history__project-trigger-chevron" />
        </button>

        {dropdownOpen && (
          <div className="chat-history__project-menu">
            <button
              className={
                "chat-history__project-option" + (!activeProjectId ? " chat-history__project-option--selected" : "")
              }
              onClick={() => handlePickProject(null)}
            >
              <span>All documents</span>
              {!activeProjectId && <Check size={14} />}
            </button>

            {projects.map((project) => (
              <button
                key={project.id}
                className={
                  "chat-history__project-option" +
                  (project.id === activeProjectId ? " chat-history__project-option--selected" : "")
                }
                onClick={() => handlePickProject(project.id)}
              >
                <span className="chat-history__project-option-label">{project.name}</span>
                {project.id === activeProjectId && <Check size={14} />}
              </button>
            ))}

            <div className="chat-history__project-menu-divider" />

            {isCreatingProject ? (
              <form className="chat-history__new-project-form" onSubmit={handleCreateProject}>
                <input
                  autoFocus
                  className="chat-history__new-project-input"
                  placeholder="Project name…"
                  value={newProjectName}
                  onChange={(event) => setNewProjectName(event.target.value)}
                  disabled={isSavingProject}
                />
                <button
                  type="submit"
                  className="chat-history__new-project-confirm"
                  disabled={isSavingProject || !newProjectName.trim()}
                >
                  {isSavingProject ? "…" : "Add"}
                </button>
              </form>
            ) : (
              <button
                className="chat-history__project-option chat-history__project-option--new"
                onClick={() => setIsCreatingProject(true)}
              >
                <Plus size={14} />
                <span>New project</span>
              </button>
            )}
          </div>
        )}
      </div>

      <button className="chat-history__new-button" onClick={onNewChat}>
        <Plus size={15} />
        New chat
      </button>

      {error && <div className="chat-history__error">{error}</div>}

      {sessions.length === 0 && !error && (
        <div className="chat-history__empty">No past conversations yet.</div>
      )}

      <ul className="chat-history__list">
        {sessions.map((session) => {
          const isActive = session.id === activeSessionId;
          return (
            <li key={session.id}>
              <button
                className={"chat-history__item" + (isActive ? " chat-history__item--active" : "")}
                onClick={() => handleSelect(session.id, session.project_id)}
                disabled={loadingSessionId === session.id}
              >
                <MessageSquare size={14} className="chat-history__item-icon" />
                <span className="chat-history__item-body">
                  <span className="chat-history__item-title">{session.title || "Untitled chat"}</span>
                  <span className="chat-history__item-date">{formatRelativeTime(session.created_at)}</span>
                </span>
                {isActive && <span className="chat-history__item-dot" aria-hidden="true" />}
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}

export default ChatHistory;
