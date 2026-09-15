import { useEffect, useRef, useState } from "react";
import { FileText, Image as ImageIcon, Plus } from "lucide-react";
import "./AttachButton.css";

const ATTACH_OPTIONS = [
  { key: "files", label: "Add files", accept: ".pdf,.xlsx", icon: FileText },
  { key: "images", label: "Add images", accept: ".png,.jpg,.jpeg", icon: ImageIcon },
];

/**
 * "+" trigger that opens a small popover offering separate "Add files"
 * (.pdf/.xlsx) and "Add images" (.png/.jpg/.jpeg) options, each scoping the
 * native file picker to just that type before handing selection upward via
 * onFilesSelected. This component holds no upload state.
 *
 * @param {{
 *   onFilesSelected: (files: File[]) => void,
 *   disabled?: boolean,
 * }} props
 */
function AttachButton({ onFilesSelected, disabled }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const fileInputRef = useRef(null);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!menuOpen) return undefined;

    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [menuOpen]);

  const handleChange = (event) => {
    const files = Array.from(event.target.files || []);
    event.target.value = "";
    if (files.length > 0) {
      onFilesSelected(files);
    }
  };

  const handlePickOption = (option) => {
    setMenuOpen(false);
    if (fileInputRef.current) {
      fileInputRef.current.accept = option.accept;
      fileInputRef.current.click();
    }
  };

  return (
    <div className="attach-button-wrap" ref={menuRef}>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="attach-button__input"
        onChange={handleChange}
        disabled={disabled}
      />
      <button
        type="button"
        className="attach-button"
        onClick={() => setMenuOpen((open) => !open)}
        disabled={disabled}
        aria-label="Attach files"
        aria-haspopup="menu"
        aria-expanded={menuOpen}
        title="Attach files or images (up to 5)"
      >
        <Plus size={18} />
      </button>

      {menuOpen && (
        <div className="attach-button__menu" role="menu">
          {ATTACH_OPTIONS.map((option) => {
            const OptionIcon = option.icon;
            return (
              <button
                key={option.key}
                type="button"
                role="menuitem"
                className="attach-button__menu-item"
                onClick={() => handlePickOption(option)}
              >
                <OptionIcon size={15} className="attach-button__menu-item-icon" />
                <span>{option.label}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default AttachButton;
