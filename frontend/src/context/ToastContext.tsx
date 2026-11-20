import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";


type ToastType = "success" | "error" | "info";


interface ToastItem {
  id: number;
  message: string;
  type: ToastType;
  onUndo?: () => Promise<void> | void;
}


interface ConfirmOptions {
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => Promise<void> | void;
}


interface ToastContextValue {
  showToast: (
    message: string,
    type?: ToastType,
    onUndo?: () => Promise<void> | void
  ) => void;
  confirmAction: (options: ConfirmOptions) => void;
}


const ToastContext = createContext<ToastContextValue | undefined>(undefined);


export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [modal, setModal] = useState<ConfirmOptions | null>(null);
  const [busy, setBusy] = useState(false);


  // Mandel Rule 1: Never trap the user in a modal — Esc always cancels when not busy
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && modal && !busy) {
        setModal(null);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [modal, busy]);


  const showToast = useCallback(
    (
      message: string,
      type: ToastType = "info",
      onUndo?: () => Promise<void> | void
    ) => {
      const id = Date.now() + Math.floor(Math.random() * 1000);
      setToasts((prev) => [...prev, { id, message, type, onUndo }]);
      setTimeout(
        () => {
          setToasts((prev) => prev.filter((t) => t.id !== id));
        },
        onUndo ? 6000 : 3500
      );
    },
    []
  );


  const confirmAction = useCallback((options: ConfirmOptions) => {
    setModal(options);
  }, []);


  const handleConfirm = async () => {
    if (!modal) return;
    setBusy(true);
    try {
      await modal.onConfirm();
      setModal(null);
    } finally {
      setBusy(false);
    }
  };


  return (
    <ToastContext.Provider value={{ showToast, confirmAction }}>
      {children}


      <div className="toast-stack" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast-item toast-${t.type}`}>
            <span>{t.message}</span>
            {t.onUndo && (
              <button
                type="button"
                className="toast-undo-btn"
                onClick={async () => {
                  setToasts((prev) => prev.filter((item) => item.id !== t.id));
                  await t.onUndo?.();
                }}
              >
                Undo
              </button>
            )}
          </div>
        ))}
      </div>


      {modal && (
        <div
          className="modal-backdrop"
          role="dialog"
          aria-modal="true"
          onClick={(e) => {
            if (e.target === e.currentTarget && !busy) setModal(null);
          }}
        >
          <div className="card modal-card">
            <h3 className="section-title">{modal.title}</h3>
            <p className="page-subtitle mt-2">{modal.message}</p>
            <div className="form-actions mt-4">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={busy}
                onClick={() => setModal(null)}
              >
                Cancel (Esc)
              </button>
              <button
                type="button"
                className="btn btn-danger btn-sm"
                disabled={busy}
                onClick={handleConfirm}
              >
                {busy ? "Processing..." : modal.confirmLabel || "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}
    </ToastContext.Provider>
  );
};


export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside ToastProvider");
  return ctx;
}
