import { useState } from "react";
import { generateReport } from "../../api/client";
import "./ReportDownload.css";

/**
 * Two download buttons for exporting the current Q&A as a report.
 *
 * @param {{ query: string, answer: string, sources: Array<object> }} props
 */
function ReportDownload({ query, answer, sources }) {
  const [pendingFormat, setPendingFormat] = useState(null);
  const [error, setError] = useState(null);

  const handleDownload = async (format) => {
    setPendingFormat(format);
    setError(null);
    try {
      await generateReport(query, answer, sources || [], format);
    } catch (err) {
      setError(err.message || "Report generation failed.");
    } finally {
      setPendingFormat(null);
    }
  };

  return (
    <div className="report-download">
      <span className="report-download__label">Export this answer:</span>
      <button
        className="report-download__button"
        onClick={() => handleDownload("docx")}
        disabled={pendingFormat !== null}
      >
        {pendingFormat === "docx" ? "Preparing…" : "Download as Word"}
      </button>
      <button
        className="report-download__button report-download__button--secondary"
        onClick={() => handleDownload("xlsx")}
        disabled={pendingFormat !== null}
      >
        {pendingFormat === "xlsx" ? "Preparing…" : "Download as Excel"}
      </button>
      {error && <span className="report-download__error">{error}</span>}
    </div>
  );
}

export default ReportDownload;
