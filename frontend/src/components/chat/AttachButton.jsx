import { useRef } from "react";
import { Plus } from "lucide-react";
import "./AttachButton.css";

/**
 * "+" trigger that opens a native multi-file picker for attaching documents
 * directly from the chat input, without leaving the conversation. This
 * component holds no upload state — selection is just reported upward via
 * onFilesSelected.
 *
 * @param {{
 *   onFilesSelected: (files: File[]) => void,
 *   disabled?: boolean,
 * }} props
 */
function AttachButton({ onFilesSelected, disabled }) {
  const fileInputRef = useRef(null);

  const handleChange = (event) => {
    const files = Array.from(event.target.files || []);
    event.target.value = "";
    if (files.length > 0) {
      onFilesSelected(files);
    }
  };

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.png,.jpg,.jpeg,.xlsx"
        className="attach-button__input"
        onChange={handleChange}
        disabled={disabled}
      />
      <button
        type="button"
        className="attach-button"
        onClick={() => fileInputRef.current?.click()}
        disabled={disabled}
        aria-label="Attach files"
        title="Attach files (PDF, image, or Excel — up to 5)"
      >
        <Plus size={18} />
      </button>
    </>
  );
}

export default AttachButton;
