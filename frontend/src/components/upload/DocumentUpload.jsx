import { useCallback, useRef, useState } from "react";
import { MAX_FILE_SIZE_BYTES, uploadDocument } from "../../api/client";
import "./DocumentUpload.css";

/**
 * Drag-and-drop / click-to-upload document input.
 *
 * @param {{
 *   projectId?: string|null,
 *   onStageChange?: (stage: string|null) => void,
 *   onUploaded?: (result: {document_id: string, filename: string, chunks_indexed: number}) => void,
 * }} props
 */
function DocumentUpload({ projectId, onStageChange, onUploaded }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);
  const timersRef = useRef([]);

  const clearTimers = () => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  };

  const runUpload = useCallback(
    async (file) => {
      if (!file || isUploading) return;

      setIsUploading(true);
      setError(null);
      setResult(null);
      clearTimers();

      // Ingest/OCR/Embed all happen inside one backend call with no
      // incremental progress events, so we advance the pipeline display on
      // a short local schedule purely for visual feedback during the demo.
      onStageChange?.("ingest");
      timersRef.current.push(setTimeout(() => onStageChange?.("ocr"), 700));
      timersRef.current.push(setTimeout(() => onStageChange?.("embed"), 1600));

      try {
        const response = await uploadDocument(file, projectId);
        setResult(response);
        onUploaded?.(response);
      } catch (err) {
        setError(err.message || "Upload failed.");
      } finally {
        clearTimers();
        onStageChange?.(null);
        setIsUploading(false);
      }
    },
    [isUploading, projectId, onStageChange, onUploaded]
  );

  const rejectIfOversized = (file) => {
    if (!file || file.size <= MAX_FILE_SIZE_BYTES) return false;
    setResult(null);
    setError(`"${file.name}" exceeds the 15MB limit and was not uploaded.`);
    return true;
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (rejectIfOversized(file)) return;
    runUpload(file);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (rejectIfOversized(file)) return;
    runUpload(file);
  };

  const handleDragOver = (event) => {
    event.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const dropzoneClassName = [
    "document-upload__dropzone",
    isDragging ? "document-upload__dropzone--dragging" : "",
    isUploading ? "document-upload__dropzone--busy" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="document-upload">
      <div
        className={dropzoneClassName}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !isUploading && fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            !isUploading && fileInputRef.current?.click();
          }
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.xlsx"
          className="document-upload__input"
          onChange={handleFileChange}
          disabled={isUploading}
        />
        <div className="document-upload__icon" aria-hidden="true">
          &#8593;
        </div>
        <div className="document-upload__text">
          {isUploading ? (
            <span>Processing document&hellip;</span>
          ) : (
            <>
              <strong>Drag &amp; drop</strong> a PDF or image here, or click to browse
            </>
          )}
        </div>
      </div>

      {result && (
        <div className="document-upload__message document-upload__message--success">
          Indexed &ldquo;{result.filename}&rdquo; — {result.chunks_indexed} chunk
          {result.chunks_indexed === 1 ? "" : "s"} added to the knowledge base.
        </div>
      )}

      {error && (
        <div className="document-upload__message document-upload__message--error">{error}</div>
      )}
    </div>
  );
}

export default DocumentUpload;
