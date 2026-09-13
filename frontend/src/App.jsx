import { useState } from "react";
import DocumentUpload from "./components/upload/DocumentUpload.jsx";
import PipelineSteps from "./components/pipeline/PipelineSteps.jsx";
import ChatWindow from "./components/chat/ChatWindow.jsx";
import ChatHistory from "./components/history/ChatHistory.jsx";
import NetworkMonitor from "./components/monitor/NetworkMonitor.jsx";
import ReportDownload from "./components/reports/ReportDownload.jsx";
import TriNodeMark from "./components/common/TriNodeMark.jsx";
import "./App.css";

// `epoch` only increments on an explicit "New chat" / "select a past
// session" action, and is used as ChatWindow's `key` so those two actions
// force a clean remount. A session id learned mid-conversation (the server
// auto-creating one for a brand-new chat) flows back through
// handleSessionChange without touching epoch, so it does NOT remount and
// the in-progress conversation is preserved.
function App() {
  const [activeStage, setActiveStage] = useState(null);
  const [documentId, setDocumentId] = useState(null);
  const [activeDocument, setActiveDocument] = useState(null);
  const [lastAnswer, setLastAnswer] = useState(null);
  const [historyRefreshToken, setHistoryRefreshToken] = useState(0);
  const [sessionView, setSessionView] = useState({ epoch: 0, sessionId: null, messages: [] });
  const [activeProjectId, setActiveProjectId] = useState(null);

  const handleUploaded = (result) => {
    setActiveDocument(result);
    setDocumentId(result.document_id);
  };

  const handleNewChat = () => {
    setSessionView((prev) => ({ epoch: prev.epoch + 1, sessionId: null, messages: [] }));
    setLastAnswer(null);
  };

  const handleSelectSession = (sessionId, messages, projectId) => {
    setSessionView((prev) => ({ epoch: prev.epoch + 1, sessionId, messages }));
    setActiveProjectId(projectId ?? null);
    setLastAnswer(null);
  };

  const handleSessionChange = (sessionId) => {
    setSessionView((prev) => ({ ...prev, sessionId }));
    setHistoryRefreshToken((token) => token + 1);
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header__titles">
          <h1 className="app-title">
            <TriNodeMark size={28} color="#2952cc" />
            Sovereign Document Workbench
          </h1>
          <p className="app-subtitle">
            Fully local, offline AI assistant for confidential industrial documents
          </p>
        </div>
        <NetworkMonitor />
      </header>

      <div className="app-body">
        <ChatHistory
          activeSessionId={sessionView.sessionId}
          activeProjectId={activeProjectId}
          onNewChat={handleNewChat}
          onSelectSession={handleSelectSession}
          onProjectChange={setActiveProjectId}
          refreshToken={historyRefreshToken}
        />

        <div className="app-main-column">
          <section className="app-panel">
            <h2 className="app-panel__heading">Upload a document</h2>
            <DocumentUpload
              projectId={activeProjectId}
              onStageChange={setActiveStage}
              onUploaded={handleUploaded}
            />
            {activeDocument && (
              <p className="app-active-document">
                Currently asking about: <strong>{activeDocument.filename}</strong>
              </p>
            )}
          </section>

          <section className="app-panel app-panel--tight">
            <PipelineSteps activeStage={activeStage} />
          </section>

          <main className="app-main">
            <ChatWindow
              key={sessionView.epoch}
              documentId={documentId}
              sessionId={sessionView.sessionId}
              projectId={activeProjectId}
              initialMessages={sessionView.messages}
              onStageChange={setActiveStage}
              onAnswerReady={setLastAnswer}
              onSessionChange={handleSessionChange}
            />
          </main>

          {lastAnswer && (
            <section className="app-panel app-panel--tight">
              <ReportDownload
                query={lastAnswer.query}
                answer={lastAnswer.answer}
                sources={lastAnswer.sources}
              />
            </section>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
