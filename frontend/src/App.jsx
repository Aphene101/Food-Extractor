// src/App.jsx
import { useState } from "react";

function JSONViewer({ data }) {
  return (
    <pre
      style={{
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
        background: "#0f172a",
        color: "#e6eef8",
        padding: 16,
        borderRadius: 8,
        fontSize: 13,
        lineHeight: 1.45,
        overflowX: "auto",
        maxHeight: "60vh",
      }}
    >
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

function formatNutritionCell(v) {
  if (!v) return "—";
  const parts = [];
  if (v.value !== undefined && v.value !== null) parts.push(v.value);
  if (v.unit) parts.push(v.unit);
  // only show source if it's defined and not the generic "unknown"
  if (v.source && v.source !== "unknown") parts.push(`(${v.source})`);
  return parts.length ? parts.join(" ") : "—";
}

export default function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showRaw, setShowRaw] = useState(false);
  const [error, setError] = useState("");

  async function uploadFile(e) {
    e.preventDefault();
    setError("");
    if (!file) {
      setError("Choose a PDF first.");
      return;
    }
    setLoading(true);
    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch("http://127.0.0.1:8000/upload", {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`Server returned ${res.status}: ${txt}`);
      }
      const json = await res.json();
      setResult(json);
      setShowRaw(false);
    } catch (err) {
      setError(String(err));
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        fontFamily: "Inter, system-ui, Arial",
        padding: 24,
        maxWidth: 980,
        margin: "0 auto",
      }}
    >
      <h1 style={{ marginBottom: 6 }}>Food PDF Extractor</h1>
      <p style={{ color: "#334155" }}>
        Upload a product PDF (scanned or digital) to return allergens &
        nutrition JSON.
      </p>

      <form
        onSubmit={uploadFile}
        style={{
          display: "flex",
          gap: 12,
          alignItems: "center",
          marginBottom: 12,
        }}
      >
        <input
          type="file"
          accept="application/pdf"
          onChange={(ev) => setFile(ev.target.files?.[0] || null)}
        />
        <button
          type="submit"
          disabled={loading}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            border: "1px solid #cbd5e1",
            background: "#0369a1",
            color: "white",
            cursor: "pointer",
          }}
        >
          {loading ? "Uploading..." : "Upload & Extract"}
        </button>
        <button
          type="button"
          onClick={() => {
            setResult(null);
            setError("");
            setFile(null);
          }}
          style={{
            padding: "6px 10px",
            borderRadius: 8,
            border: "1px solid #e2e8f0",
            background: "#fff",
          }}
        >
          Reset
        </button>
      </form>

      {error && (
        <div style={{ color: "crimson", marginBottom: 12 }}>{error}</div>
      )}

      {result ? (
        <div
          style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}
        >
          <div>
            <h3>Allergens</h3>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <tbody>
                {Object.entries(result.allergens || {}).map(([k, v]) => (
                  <tr key={k}>
                    <td
                      style={{
                        padding: "6px 8px",
                        borderBottom: "1px solid #e6eef8",
                        fontWeight: 600,
                      }}
                    >
                      {k}
                    </td>
                    <td
                      style={{
                        padding: "6px 8px",
                        borderBottom: "1px solid #e6eef8",
                      }}
                    >
                      {v}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div>
            <h3>Nutrition (per 100g)</h3>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <tbody>
                {Object.entries(result.nutrition || {}).map(([k, v]) => (
                  <tr key={k}>
                    <td
                      style={{
                        padding: "6px 8px",
                        borderBottom: "1px solid #e6eef8",
                        fontWeight: 600,
                      }}
                    >
                      {k}
                    </td>
                    <td
                      style={{
                        padding: "6px 8px",
                        borderBottom: "1px solid #e6eef8",
                      }}
                    >
                      {formatNutritionCell(v)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ gridColumn: "1 / -1" }}>
            <h3>Raw text extract (OCR)</h3>

            <div
              style={{
                marginBottom: 8,
                color: "#334155",
                display: "flex",
                gap: 12,
                alignItems: "center",
              }}
            >
              <div>{result.filename}</div>

              {/* short preview (first 200 chars, cleaned) */}
              <div style={{ color: "#64748b", fontSize: 13 }}>
                {result.raw_text_extract
                  ? result.raw_text_extract.slice(0, 180).replace(/\s+/g, " ") +
                    (result.raw_text_extract.length > 180 ? "…" : "")
                  : "No OCR text available"}
              </div>

              <button
                onClick={() => setShowRaw((s) => !s)}
                style={{
                  marginLeft: "auto",
                  padding: "6px 8px",
                  borderRadius: 8,
                  border: "1px solid #cbd5e1",
                  background: "#fff",
                  cursor: "pointer",
                }}
              >
                {showRaw ? "Hide OCR" : "Show OCR output"}
              </button>

              {/* download raw text (client-side) */}
              {result.raw_text_extract && (
                <button
                  onClick={() => {
                    const blob = new Blob([result.raw_text_extract], {
                      type: "text/plain;charset=utf-8",
                    });
                    const a = document.createElement("a");
                    a.href = URL.createObjectURL(blob);
                    const safeName = (result.filename || "ocr").replace(
                      /[^a-zA-Z0-9._-]/g,
                      "_"
                    );
                    a.download = safeName + ".ocr.txt";
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                  }}
                  style={{
                    padding: "6px 8px",
                    borderRadius: 8,
                    border: "1px solid #cbd5e1",
                    background: "#fff",
                    cursor: "pointer",
                  }}
                >
                  Download OCR
                </button>
              )}
            </div>

            {showRaw && (
              <div style={{ marginTop: 8 }}>
                <JSONViewer
                  data={{ raw_text_extract: result.raw_text_extract }}
                />
              </div>
            )}

            <div style={{ marginTop: 12 }}>
              <strong>Notes:</strong>{" "}
              {Array.isArray(result.notes)
                ? result.notes.join(" · ")
                : result.notes}
            </div>
          </div>
        </div>
      ) : (
        <div style={{ color: "#64748b" }}>
          No result yet, upload a PDF to extract data.
        </div>
      )}

      <footer style={{ marginTop: 28, color: "#94a3b8" }}>
        React frontend (Vite) • Backend: FastAPI
      </footer>
    </div>
  );
}
