import { AlertCircle, Check, Loader2 } from "lucide-react";
import "./AttachmentChips.css";

/**
 * Small status chips for files attached via AttachButton, rendered above
 * the chat input while each upload is in flight (and left in place
 * afterward so the outcome stays visible) — reuses the same success/error
 * color tokens as DocumentUpload.jsx's inline messages.
 *
 * @param {{
 *   chips: Array<{id: string, name: string, status: "uploading"|"success"|"error", error: string|null}>,
 * }} props
 */
function AttachmentChips({ chips }) {
  if (!chips || chips.length === 0) return null;

  return (
    <div className="attachment-chips">
      {chips.map((chip) => (
        <div
          key={chip.id}
          className={`attachment-chips__chip attachment-chips__chip--${chip.status}`}
          title={chip.error || chip.name}
        >
          {chip.status === "uploading" && (
            <Loader2 size={12} className="attachment-chips__icon attachment-chips__icon--spin" />
          )}
          {chip.status === "success" && <Check size={12} className="attachment-chips__icon" />}
          {chip.status === "error" && <AlertCircle size={12} className="attachment-chips__icon" />}
          <span className="attachment-chips__name">{chip.name}</span>
        </div>
      ))}
    </div>
  );
}

export default AttachmentChips;
