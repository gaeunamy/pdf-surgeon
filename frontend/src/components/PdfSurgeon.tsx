"use client";

import { useState, useRef, useCallback } from "react";
import type { Mode, ReplaceEntry, ProcessState } from "@/types";

/* ─── tiny uid ─── */
const uid = () => Math.random().toString(36).slice(2, 8);

/* ─── icons (inline svg) ─── */
const IconUpload = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
    <path d="M10 13V4M10 4L7 7M10 4l3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M3 15v1.5A1.5 1.5 0 004.5 18h11A1.5 1.5 0 0017 16.5V15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
);

const IconFile = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <rect x="2" y="1" width="7" height="11" rx="1.5" fill="#F09595"/>
    <path d="M7.5 1v3h3" fill="#E24B4A" opacity="0.6"/>
    <path d="M4 6.5h6M4 8.5h4" stroke="white" strokeWidth="1" strokeLinecap="round"/>
  </svg>
);

const IconPlay = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <path d="M3 2.5l8 4.5-8 4.5V2.5z" fill="currentColor"/>
  </svg>
);

const IconDownload = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <path d="M7 1v8M7 9L4.5 6.5M7 9l2.5-2.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M1.5 11h11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
);

const IconX = () => (
  <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
    <path d="M1.5 1.5l7 7M8.5 1.5l-7 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
);

const IconArrow = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <path d="M2 7h10M8 4l4 3-4 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

/* ─── mode definitions ─── */
const MODES: { id: Mode; label: string; sub: string; symbol: string }[] = [
  { id: "mask",   label: "마스킹",    sub: "단어를 검게 가려 기밀 처리",    symbol: "■" },
  { id: "manual", label: "수동 번역", sub: "단어를 지정해 원하는 값으로 교체", symbol: "↔" },
  { id: "smart",  label: "지능 번역", sub: "AI가 전체 문서를 한국어로 번역", symbol: "◈" },
];

/* ══════════════════════════════════════════════ */
export default function PdfSurgeon() {
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<Mode>("mask");
  const [isDragging, setIsDragging] = useState(false);

  /* mask state */
  const [maskInput, setMaskInput] = useState("");
  const [maskTags, setMaskTags] = useState<string[]>([]);

  /* manual state */
  const [replaceFrom, setReplaceFrom] = useState("");
  const [replaceTo, setReplaceTo]     = useState("");
  const [replaceEntries, setReplaceEntries] = useState<ReplaceEntry[]>([]);

  /* process state */
  const [ps, setPs] = useState<ProcessState>({ status: "idle", resultBlob: null, errorMessage: "" });
  const [resultName, setResultName] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  /* ── file handling ── */
  const handleFile = (f: File) => {
    if (f.type !== "application/pdf") return;
    setFile(f);
    setPs({ status: "idle", resultBlob: null, errorMessage: "" });
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, []);

  /* ── mask tags ── */
  const addMaskTag = () => {
    const v = maskInput.trim();
    if (!v || maskTags.includes(v)) return;
    setMaskTags(prev => [...prev, v]);
    setMaskInput("");
  };

  /* ── replace entries ── */
  const addReplaceEntry = () => {
    const f = replaceFrom.trim(), t = replaceTo.trim();
    if (!f || !t) return;
    setReplaceEntries(prev => [...prev, { id: uid(), from: f, to: t }]);
    setReplaceFrom(""); setReplaceTo("");
  };

  /* ── validate ── */
  const canRun = (): string | null => {
    if (!file) return "PDF 파일을 업로드해 주세요.";
    if (mode === "mask"   && maskTags.length === 0)    return "가릴 단어를 최소 하나 입력해 주세요.";
    if (mode === "manual" && replaceEntries.length === 0) return "교체할 단어 쌍을 최소 하나 입력해 주세요.";
    return null;
  };

  /* ── submit ── */
  const handleRun = async () => {
    const err = canRun();
    if (err) { setPs({ status: "error", resultBlob: null, errorMessage: err }); return; }

    setPs({ status: "loading", resultBlob: null, errorMessage: "" });

    const fd = new FormData();
    fd.append("file", file!);
    fd.append("mode", mode);

    if (mode === "mask") {
      // 여러 단어를 첫 번째로만 넘기거나, 백엔드가 지원하면 전부 넘기기
      // 현재 FastAPI는 단일 target_word만 받으므로 join해서 전달
      fd.append("target_word", maskTags.join(","));
      fd.append("manual_dict", "{}");
    } else if (mode === "manual") {
      const dict: Record<string, string> = {};
      replaceEntries.forEach(e => { dict[e.from] = e.to; });
      fd.append("manual_dict", JSON.stringify(dict));
      fd.append("target_word", "");
    } else {
      fd.append("manual_dict", "{}");
      fd.append("target_word", "");
    }

    try {
      const res = await fetch("/api/translate", { method: "POST", body: fd });

      if (!res.ok) {
        const json = await res.json().catch(() => ({ detail: "서버 오류" }));
        setPs({ status: "error", resultBlob: null, errorMessage: json.detail });
        return;
      }

      const blob = await res.blob();
      setResultName(`result_${file!.name}`);
      setPs({ status: "success", resultBlob: blob, errorMessage: "" });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "네트워크 오류";
      setPs({ status: "error", resultBlob: null, errorMessage: msg });
    }
  };

  /* ── download ── */
  const handleDownload = () => {
    if (!ps.resultBlob) return;
    const url = URL.createObjectURL(ps.resultBlob);
    const a = document.createElement("a");
    a.href = url; a.download = resultName; a.click();
    URL.revokeObjectURL(url);
  };

  /* ══ RENDER ══ */
  return (
    <div className="relative z-10 min-h-screen flex flex-col items-center px-4 py-10">

      {/* ── header ── */}
      <header className="w-full max-w-xl flex items-center justify-between mb-10">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 bg-[#1C1C1C] rounded-md flex items-center justify-center flex-shrink-0">
            <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
              <rect x="3" y="1.5" width="6" height="8" rx="1" fill="#F5F0E8"/>
              <rect x="7" y="5" width="5" height="2" rx="1" fill="#E24B4A"/>
              <rect x="7" y="8" width="5" height="1.5" rx="0.75" fill="#E24B4A" opacity="0.55"/>
              <rect x="3" y="10.5" width="9" height="1.5" rx="0.75" fill="#888" opacity="0.4"/>
              <rect x="3" y="13" width="6" height="1.5" rx="0.75" fill="#888" opacity="0.4"/>
            </svg>
          </div>
          <span className="font-mono text-[13px] font-medium tracking-tight text-[#2E3640]">
            pdf<span className="text-[#E24B4A]">-surgeon</span>
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[11px] px-2.5 py-1 rounded-full border border-[#2E3640]/20 text-[#4A5260] cursor-pointer hover:border-[#2E3640]/40 transition-colors">사용법</span>
          <span className="font-mono text-[11px] px-2.5 py-1 rounded-full border border-[#2E3640]/20 text-[#4A5260] cursor-pointer hover:border-[#2E3640]/40 transition-colors">API</span>
        </div>
      </header>

      {/* ── hero text ── */}
      <div className="w-full max-w-xl mb-8">
        <h1 className="text-3xl font-light leading-snug text-[#2E3640] mb-2">
          PDF를 <span className="italic text-[#E24B4A]">정밀하게</span> 처리해요.
        </h1>
        <p className="text-sm text-[#4A5260]">마스킹 · 수동 번역 · 지능 번역 — 세 가지 방식으로</p>
      </div>

      {/* ── main card ── */}
      <div className="w-full max-w-xl bg-white/80 border border-[#2E3640]/10 rounded-2xl overflow-hidden">

        {/* upload */}
        <div className="p-5 border-b border-[#2E3640]/08">
          {!file ? (
            <div
              onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={onDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-[1.5px] border-dashed rounded-xl p-8 flex flex-col items-center gap-2 cursor-pointer transition-colors
                ${isDragging ? "border-[#E24B4A]/60 bg-[#E24B4A]/04" : "border-[#2E3640]/20 hover:border-[#2E3640]/40 hover:bg-[#2E3640]/02"}`}
            >
              <div className="w-10 h-10 rounded-lg border border-[#2E3640]/12 bg-[#F5F0E8] flex items-center justify-center text-[#4A5260] mb-1">
                <IconUpload />
              </div>
              <span className="text-sm font-medium text-[#2E3640]">PDF 파일을 여기에 끌어다 놓거나 클릭하세요</span>
              <span className="font-mono text-[11px] text-[#888]">.pdf · 최대 50MB</span>
              <input ref={fileInputRef} type="file" accept=".pdf" className="hidden"
                onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }} />
            </div>
          ) : (
            <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl border border-[#2E3640]/10 bg-[#F5F0E8]/60">
              <div className="w-7 h-7 rounded-md bg-[#FCEBEB] flex items-center justify-center flex-shrink-0">
                <IconFile />
              </div>
              <span className="text-sm font-medium text-[#2E3640] flex-1 truncate">{file.name}</span>
              <span className="font-mono text-[11px] text-[#888] flex-shrink-0">
                {(file.size / 1024 / 1024).toFixed(1)} MB
              </span>
              <button
                onClick={() => { setFile(null); setPs({ status: "idle", resultBlob: null, errorMessage: "" }); }}
                className="w-6 h-6 rounded-full border border-[#2E3640]/15 flex items-center justify-center text-[#888] hover:text-[#2E3640] hover:border-[#2E3640]/30 transition-colors"
              >
                <IconX />
              </button>
            </div>
          )}
        </div>

        {/* mode selector */}
        <div className="p-5 border-b border-[#2E3640]/08">
          <p className="font-mono text-[11px] tracking-widest text-[#888] uppercase mb-3">처리 방식</p>
          <div className="grid grid-cols-3 gap-2">
            {MODES.map(m => (
              <button
                key={m.id}
                onClick={() => { setMode(m.id); setPs({ status: "idle", resultBlob: null, errorMessage: "" }); }}
                className={`relative text-left p-3.5 rounded-xl border transition-all
                  ${mode === m.id
                    ? "border-[#1C1C1C] border-[1.5px] bg-white"
                    : "border-[#2E3640]/12 bg-white/50 hover:border-[#2E3640]/25"}`}
              >
                <div className={`absolute top-3 right-3 w-2 h-2 rounded-full transition-colors
                  ${mode === m.id ? "bg-[#1C1C1C]" : "bg-transparent border border-[#2E3640]/25"}`} />
                <span className="block text-base mb-2 leading-none text-[#2E3640] font-mono">{m.symbol}</span>
                <span className="block text-[13px] font-medium text-[#2E3640] mb-1">{m.label}</span>
                <span className="block text-[11px] text-[#4A5260] leading-snug">{m.sub}</span>
              </button>
            ))}
          </div>
        </div>

        {/* mode panels */}
        <div className="p-5 border-b border-[#2E3640]/08 min-h-[120px]">

          {/* ── mask panel ── */}
          {mode === "mask" && (
            <div className="flex flex-col gap-3">
              <p className="font-mono text-[11px] tracking-widest text-[#888] uppercase">가릴 단어</p>
              <div className="flex gap-2">
                <input
                  value={maskInput}
                  onChange={e => setMaskInput(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && addMaskTag()}
                  placeholder="예: 홍길동, 주민등록번호"
                  className="flex-1 h-9 px-3 text-[13px] rounded-lg border border-[#2E3640]/15 bg-[#F5F0E8]/60 text-[#2E3640] placeholder:text-[#888] outline-none focus:border-[#2E3640]/35"
                />
                <button
                  onClick={addMaskTag}
                  className="h-9 px-3 font-mono text-[12px] rounded-lg border border-[#2E3640]/20 text-[#4A5260] hover:border-[#2E3640]/40 hover:bg-[#2E3640]/04 transition-colors"
                >
                  + 추가
                </button>
              </div>
              {maskTags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {maskTags.map(tag => (
                    <span key={tag} className="inline-flex items-center gap-1.5 pl-2.5 pr-1.5 py-1 rounded-full bg-[#FCEBEB] text-[#A32D2D] font-mono text-[12px]">
                      {tag}
                      <button onClick={() => setMaskTags(p => p.filter(t => t !== tag))}
                        className="opacity-50 hover:opacity-100 transition-opacity"><IconX /></button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── manual panel ── */}
          {mode === "manual" && (
            <div className="flex flex-col gap-3">
              <p className="font-mono text-[11px] tracking-widest text-[#888] uppercase">교체 단어 쌍</p>
              <div className="flex items-center gap-2">
                <input
                  value={replaceFrom}
                  onChange={e => setReplaceFrom(e.target.value)}
                  placeholder="원본 단어"
                  className="flex-1 h-9 px-3 text-[13px] rounded-lg border border-[#2E3640]/15 bg-[#F5F0E8]/60 text-[#2E3640] placeholder:text-[#888] outline-none focus:border-[#2E3640]/35"
                />
                <span className="text-[#888] flex-shrink-0"><IconArrow /></span>
                <input
                  value={replaceTo}
                  onChange={e => setReplaceTo(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && addReplaceEntry()}
                  placeholder="바꿀 단어"
                  className="flex-1 h-9 px-3 text-[13px] rounded-lg border border-[#2E3640]/15 bg-[#F5F0E8]/60 text-[#2E3640] placeholder:text-[#888] outline-none focus:border-[#2E3640]/35"
                />
                <button
                  onClick={addReplaceEntry}
                  className="h-9 px-3 font-mono text-[12px] rounded-lg border border-[#2E3640]/20 text-[#4A5260] hover:border-[#2E3640]/40 hover:bg-[#2E3640]/04 transition-colors flex-shrink-0"
                >
                  + 추가
                </button>
              </div>
              {replaceEntries.length > 0 && (
                <div className="flex flex-col gap-1.5">
                  {replaceEntries.map(e => (
                    <div key={e.id} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#1C1C1C]/04 border border-[#2E3640]/08">
                      <span className="font-mono text-[12px] text-[#2E3640] flex-1">{e.from}</span>
                      <span className="text-[#888]"><IconArrow /></span>
                      <span className="font-mono text-[12px] text-[#2E3640] flex-1">{e.to}</span>
                      <button onClick={() => setReplaceEntries(p => p.filter(x => x.id !== e.id))}
                        className="text-[#888] hover:text-[#2E3640] transition-colors ml-1"><IconX /></button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── smart panel ── */}
          {mode === "smart" && (
            <div className="flex flex-col gap-3">
              <p className="font-mono text-[11px] tracking-widest text-[#888] uppercase">번역 설정</p>
              <div className="flex items-center gap-3">
                <select className="flex-1 h-9 px-3 text-[13px] rounded-lg border border-[#2E3640]/15 bg-[#F5F0E8]/60 text-[#2E3640] outline-none focus:border-[#2E3640]/35">
                  <option>자동 감지</option>
                  <option>영어 (EN)</option>
                  <option>일본어 (JA)</option>
                  <option>중국어 (ZH)</option>
                  <option>독일어 (DE)</option>
                  <option>프랑스어 (FR)</option>
                </select>
                <span className="text-[#888] flex-shrink-0"><IconArrow /></span>
                <div className="flex-1 h-9 px-3 text-[13px] rounded-lg border border-[#2E3640]/15 bg-[#F5F0E8]/30 text-[#4A5260] flex items-center">
                  한국어 (KO)
                </div>
              </div>
              <p className="font-mono text-[11px] text-[#888]">레이아웃 · 서식 최대한 유지</p>
            </div>
          )}
        </div>

        {/* run / result */}
        <div className="p-5 flex flex-col gap-3">

          {/* error message */}
          {ps.status === "error" && (
            <div className="px-4 py-2.5 rounded-xl border border-[#E24B4A]/25 bg-[#FCEBEB] text-[#A32D2D] text-[13px]">
              {ps.errorMessage}
            </div>
          )}

          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 transition-colors
                ${ps.status === "loading" ? "bg-[#BA7517] animate-pulse" :
                  ps.status === "success" ? "bg-[#3B6D11]" :
                  ps.status === "error"   ? "bg-[#E24B4A]" : "bg-[#3B6D11]"}`} />
              <span className="font-mono text-[12px] text-[#4A5260]">
                {ps.status === "loading" ? "처리 중..." :
                 ps.status === "success" ? "완료" :
                 ps.status === "error"   ? "오류 발생" : "준비됨"}
              </span>
            </div>

            <div className="flex gap-2">
              {ps.status === "success" && ps.resultBlob && (
                <button
                  onClick={handleDownload}
                  className="h-9 px-4 rounded-lg bg-[#E24B4A] text-white text-[13px] font-medium flex items-center gap-2 hover:bg-[#C8332A] transition-colors"
                >
                  <IconDownload /> 다운로드
                </button>
              )}
              <button
                onClick={handleRun}
                disabled={ps.status === "loading"}
                className="h-9 px-5 rounded-lg bg-[#1C1C1C] text-[#F5F0E8] text-[13px] font-medium flex items-center gap-2 hover:opacity-80 disabled:opacity-40 transition-opacity"
              >
                {ps.status === "loading" ? (
                  <span className="font-mono text-[12px]">처리 중...</span>
                ) : (
                  <><IconPlay /> 처리 시작</>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* footer */}
      <footer className="mt-10 font-mono text-[11px] text-[#888]">
        pdf-surgeon · FastAPI + Next.js
      </footer>
    </div>
  );
}
