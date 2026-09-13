import "./PipelineSteps.css";

const STAGES = [
  { key: "ingest", label: "Ingest" },
  { key: "ocr", label: "OCR" },
  { key: "embed", label: "Embed" },
  { key: "retrieve", label: "Retrieve" },
  { key: "generate", label: "Generate" },
];

/**
 * Horizontal pipeline indicator. Purely presentational — the parent
 * component decides which stage (if any) is active based on which API
 * call is currently in flight.
 *
 * @param {{ activeStage: string|null }} props
 */
function PipelineSteps({ activeStage }) {
  return (
    <div className="pipeline-steps" role="list">
      {STAGES.map((stage, index) => (
        <div className="pipeline-steps__segment" key={stage.key}>
          <div
            className={
              "pipeline-steps__step" +
              (activeStage === stage.key ? " pipeline-steps__step--active" : "")
            }
            role="listitem"
          >
            <span className="pipeline-steps__dot" />
            <span className="pipeline-steps__label">{stage.label}</span>
          </div>
          {index < STAGES.length - 1 && <span className="pipeline-steps__connector" />}
        </div>
      ))}
    </div>
  );
}

export default PipelineSteps;
