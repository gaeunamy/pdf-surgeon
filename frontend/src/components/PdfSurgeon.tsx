"use client";

import { useState, useRef, useCallback } from "react";
import type { Mode, ReplaceEntry, ProcessState } from "../types";

const uid = () => Math.random().toString(36).slice(2, 8);

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
  <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
    <path d="M3 2l7 4.5L3 11V2z" fill="currentColor"/>
  </svg>
);

const IconDownload = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <path d="M7 1v8M7 9L4.5 6.5M7 9l2.5-2.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M1.5 11h11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
);

const IconX = () => (
  <svg width="9" height="9" viewBox="0 0 9 9" fill="none">
    <path d="M1 1l7 7M8 1L1 8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
  </svg>
);

const IconArrow = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <path d="M2 7h10M8 4l4 3-4 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const MODES: { id: Mode; label: string; sub: string; symbol: string }[] = [
  { id: "mask",   label: "마스킹",    sub: "단어를 검게 가려 기밀 처리",       symbol: "■" },
  { id: "manual", label: "수동 번역", sub: "단어를 지정해 원하는 값으로 교체",  symbol: "↔" },
  { id: "smart",  label: "지능 번역", sub: "AI가 전체 문서를 한국어로 번역",    symbol: "◈" },
];

export default function PdfSurgeon() {
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<Mode>("mask");
  const [isDragging, setIsDragging] = useState(false);
  const [maskInput, setMaskInput] = useState("");
  const [maskTags, setMaskTags] = useState<string[]>([]);
  const [replaceFrom, setReplaceFrom] = useState("");
  const [replaceTo, setReplaceTo] = useState("");
  const [replaceEntries, setReplaceEntries] = useState<ReplaceEntry[]>([]);
  const [ps, setPs] = useState<ProcessState>({ status: "idle", resultBlob: null, errorMessage: "" });
  const [resultName, setResultName] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const addMaskTag = () => {
    const v = maskInput.trim();
    if (!v || maskTags.includes(v)) return;
    setMaskTags(prev => [...prev, v]);
    setMaskInput("");
  };

  const addReplaceEntry = () => {
    const f = replaceFrom.trim(), t = replaceTo.trim();
    if (!f || !t) return;
    setReplaceEntries(prev => [...prev, { id: uid(), from: f, to: t }]);
    setReplaceFrom(""); setReplaceTo("");
  };

  const canRun = (): string | null => {
    if (!file) return "PDF 파일을 업로드해 주세요.";
    if (mode === "mask"   && maskTags.length === 0)       return "가릴 단어를 최소 하나 입력해 주세요.";
    if (mode === "manual" && replaceEntries.length === 0) return "교체할 단어 쌍을 최소 하나 입력해 주세요.";
    return null;
  };

  const handleRun = async () => {
    const err = canRun();
    if (err) { setPs({ status: "error", resultBlob: null, errorMessage: err }); return; }
    setPs({ status: "loading", resultBlob: null, errorMessage: "" });

    const fd = new FormData();
    fd.append("file", file!);
    fd.append("mode", mode);
    if (mode === "mask") {
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
      setResultName("result_" + file!.name);
      setPs({ status: "success", resultBlob: blob, errorMessage: "" });
    } catch (e) {
      setPs({ status: "error", resultBlob: null, errorMessage: e instanceof Error ? e.message : "네트워크 오류" });
    }
  };

  const handleDownload = () => {
    if (!ps.resultBlob) return;
    const url = URL.createObjectURL(ps.resultBlob);
    const a = document.createElement("a");
    a.href = url; a.download = resultName; a.click();
    URL.revokeObjectURL(url);
  };

  const inputCls = "flex-1 h-9 px-3 text-[13px] rounded-lg border border-[#2E3640]/15 bg-[#F5F0E8]/60 text-[#2E3640] placeholder:text-[#888] outline-none focus:border-[#2E3640]/35 transition-colors font-mono";

  return (
    <div className="relative z-10 min-h-screen flex flex-col">

      {/* header */}
      <header className="flex items-center justify-between px-8 py-4 border-b border-[#2E3640]/10 bg-[#F5F0E8]/80 backdrop-blur-sm sticky top-0 z-20">
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
          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-[#E24B4A]/10 text-[#E24B4A] border border-[#E24B4A]/20">beta</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] px-3 py-1.5 rounded-lg border border-[#2E3640]/15 text-[#4A5260] cursor-pointer hover:border-[#2E3640]/30 hover:text-[#2E3640] transition-colors">사용법</span>
          <span className="font-mono text-[11px] px-3 py-1.5 rounded-lg border border-[#2E3640]/15 text-[#4A5260] cursor-pointer hover:border-[#2E3640]/30 hover:text-[#2E3640] transition-colors">API 문서</span>
        </div>
      </header>

      {/* main */}
      <div className="flex-1 flex flex-col items-center px-6 py-12">
        <div className="w-full max-w-2xl flex flex-col gap-3">

          {/* hero */}
          <div className="mb-4">
            <h1 className="text-[26px] font-light leading-snug text-[#2E3640] mb-1">
              PDF를 <span className="italic text-[#E24B4A]">정밀하게</span> 처리해요.
            </h1>
            <p className="text-[13px] text-[#888] font-mono">마스킹 · 수동 번역 · 지능 번역</p>
          </div>

          {/* ① 파일 */}
          <div className="bg-white/70 border border-[#2E3640]/10 rounded-2xl p-5">
            <p className="font-mono text-[10px] tracking-widest text-[#888] uppercase mb-3">01 — 파일</p>
            {!file ? (
              <div
                onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={onDrop}
                onClick={() => fileInputRef.current?.click()}
                className={"border border-dashed rounded-xl p-8 flex flex-col items-center gap-2 cursor-pointer transition-all " +
                  (isDragging
                    ? "border-[#E24B4A]/50 bg-[#E24B4A]/5"
                    : "border-[#2E3640]/15 hover:border-[#2E3640]/30 hover:bg-[#2E3640]/2")}
              >
                <div className="w-10 h-10 rounded-xl bg-[#F5F0E8] border border-[#2E3640]/10 flex items-center justify-center text-[#4A5260] mb-1">
                  <IconUpload />
                </div>
                <span className="text-[13px] text-[#4A5260]">끌어다 놓거나 클릭해서 업로드</span>
                <span className="font-mono text-[11px] text-[#888]">.pdf · 최대 50MB</span>
                <input ref={fileInputRef} type="file" accept=".pdf" className="hidden"
                  onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }} />
              </div>
            ) : (
              <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-[#2E3640]/10 bg-[#F5F0E8]/60">
                <div className="w-8 h-8 rounded-lg bg-[#FCEBEB] flex items-center justify-center flex-shrink-0">
                  <IconFile />
                </div>
                <span className="text-[13px] text-[#2E3640] flex-1 truncate font-mono">{file.name}</span>
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

          {/* ② 처리 방식 */}
          <div className="bg-white/70 border border-[#2E3640]/10 rounded-2xl p-5">
            <p className="font-mono text-[10px] tracking-widest text-[#888] uppercase mb-3">02 — 처리 방식</p>
            <div className="grid grid-cols-3 gap-2">
              {MODES.map(m => (
                <button
                  key={m.id}
                  onClick={() => { setMode(m.id); setPs({ status: "idle", resultBlob: null, errorMessage: "" }); }}
                  className={"relative text-left px-4 py-3.5 rounded-xl border transition-all " +
                    (mode === m.id
                      ? "border-[#1C1C1C] bg-white"
                      : "border-[#2E3640]/10 bg-white/50 hover:border-[#2E3640]/25 hover:bg-white/80")}
                >
                  <div className={"absolute top-3 right-3 w-1.5 h-1.5 rounded-full " +
                    (mode === m.id ? "bg-[#1C1C1C]" : "bg-[#2E3640]/15")} />
                  <span className={"block font-mono text-base mb-2 " +
                    (mode === m.id ? "text-[#E24B4A]" : "text-[#2E3640]/20")}>
                    {m.symbol}
                  </span>
                  <span className={"block text-[13px] font-medium mb-0.5 " +
                    (mode === m.id ? "text-[#2E3640]" : "text-[#4A5260]")}>
                    {m.label}
                  </span>
                  <span className="block text-[11px] text-[#888] font-mono leading-snug">{m.sub}</span>
                </button>
              ))}
            </div>
          </div>

          {/* ③ 옵션 */}
          <div className="bg-white/70 border border-[#2E3640]/10 rounded-2xl p-5">
            <p className="font-mono text-[10px] tracking-widest text-[#888] uppercase mb-4">03 — 옵션</p>

            {mode === "mask" && (
              <div className="flex flex-col gap-3">
                <p className="text-[13px] text-[#4A5260]">PDF에서 가릴 단어를 입력하세요. 여러 개 추가할 수 있어요.</p>
                <div className="flex gap-2">
                  <input value={maskInput} onChange={e => setMaskInput(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && addMaskTag()}
                    placeholder="예: 홍길동, 주민등록번호, 계좌번호" className={inputCls} />
                  <button onClick={addMaskTag}
                    className="h-9 px-4 font-mono text-[12px] rounded-lg border border-[#2E3640]/15 text-[#4A5260] hover:border-[#2E3640]/30 hover:text-[#2E3640] transition-colors flex-shrink-0">
                    + 추가
                  </button>
                </div>
                {maskTags.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-1">
                    {maskTags.map(tag => (
                      <span key={tag} className="inline-flex items-center gap-1.5 pl-3 pr-2 py-1.5 rounded-lg bg-[#FCEBEB] border border-[#E24B4A]/20 text-[#A32D2D] font-mono text-[12px]">
                        {tag}
                        <button onClick={() => setMaskTags(p => p.filter(t => t !== tag))}
                          className="opacity-40 hover:opacity-80 transition-opacity"><IconX /></button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {mode === "manual" && (
              <div className="flex flex-col gap-3">
                <p className="text-[13px] text-[#4A5260]">원본 단어와 바꿀 단어를 쌍으로 입력하세요.</p>
                <div className="flex items-center gap-2">
                  <input value={replaceFrom} onChange={e => setReplaceFrom(e.target.value)}
                    placeholder="원본 단어" className={inputCls} />
                  <span className="text-[#888] flex-shrink-0"><IconArrow /></span>
                  <input value={replaceTo} onChange={e => setReplaceTo(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && addReplaceEntry()}
                    placeholder="바꿀 단어" className={inputCls} />
                  <button onClick={addReplaceEntry}
                    className="h-9 px-4 font-mono text-[12px] rounded-lg border border-[#2E3640]/15 text-[#4A5260] hover:border-[#2E3640]/30 hover:text-[#2E3640] transition-colors flex-shrink-0">
                    + 추가
                  </button>
                </div>
                {replaceEntries.length > 0 && (
                  <div className="flex flex-col gap-1.5 mt-1">
                    {replaceEntries.map(e => (
                      <div key={e.id} className="flex items-center gap-3 px-4 py-2.5 rounded-lg bg-[#F5F0E8]/60 border border-[#2E3640]/08">
                        <span className="font-mono text-[12px] text-[#2E3640] flex-1">{e.from}</span>
                        <span className="text-[#888]"><IconArrow /></span>
                        <span className="font-mono text-[12px] text-[#2E3640] flex-1">{e.to}</span>
                        <button onClick={() => setReplaceEntries(p => p.filter(x => x.id !== e.id))}
                          className="text-[#888] hover:text-[#2E3640] transition-colors"><IconX /></button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {mode === "smart" && (
              <div className="flex flex-col gap-3">
                <p className="text-[13px] text-[#4A5260]">문서의 언어를 감지하여 한국어로 번역합니다. 레이아웃과 서식을 최대한 유지해요.</p>
                <div className="flex items-center gap-3">
                  <select className="flex-1 h-9 px-3 text-[13px] rounded-lg border border-[#2E3640]/15 bg-[#F5F0E8]/60 text-[#2E3640] outline-none focus:border-[#2E3640]/35 transition-colors font-mono">
                    <option>자동 감지</option>
                    <option>영어 (EN)</option>
                    <option>일본어 (JA)</option>
                    <option>중국어 (ZH)</option>
                    <option>독일어 (DE)</option>
                    <option>프랑스어 (FR)</option>
                  </select>
                  <span className="text-[#888] flex-shrink-0"><IconArrow /></span>
                  <div className="flex-1 h-9 px-3 text-[13px] rounded-lg border border-[#2E3640]/10 bg-[#F5F0E8]/30 text-[#888] flex items-center font-mono">
                    한국어 (KO)
                  </div>
                </div>
                <div className="flex gap-2 mt-1">
                  {["레이아웃 유지", "서식 보존", "GPT-4o 기반"].map(t => (
                    <span key={t} className="font-mono text-[11px] px-2.5 py-1 rounded-md bg-[#F5F0E8] border border-[#2E3640]/10 text-[#888]">{t}</span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 에러 */}
          {ps.status === "error" && (
            <div className="px-4 py-3 rounded-xl border border-[#E24B4A]/25 bg-[#FCEBEB] text-[#A32D2D] text-[13px] font-mono">
              {ps.errorMessage}
            </div>
          )}

          {/* 실행 */}
          <div className="flex items-center justify-between gap-4 pt-1">
            <div className="flex items-center gap-2">
              <div className={"w-1.5 h-1.5 rounded-full flex-shrink-0 transition-colors " +
                (ps.status === "loading" ? "bg-amber-500 animate-pulse" :
                 ps.status === "success" ? "bg-emerald-600" :
                 ps.status === "error"   ? "bg-[#E24B4A]" : "bg-[#2E3640]/20")} />
              <span className="font-mono text-[12px] text-[#888]">
                {ps.status === "loading" ? "처리 중..." :
                 ps.status === "success" ? "완료 — " + resultName :
                 ps.status === "error"   ? "오류 발생" :
                 file ? file.name + " 준비됨" : "파일을 업로드해 주세요"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {ps.status === "success" && ps.resultBlob && (
                <button onClick={handleDownload}
                  className="h-9 px-4 rounded-lg bg-emerald-600 text-white text-[13px] font-medium flex items-center gap-2 hover:bg-emerald-500 transition-colors">
                  <IconDownload /> 다운로드
                </button>
              )}
              <button onClick={handleRun} disabled={ps.status === "loading"}
                className="h-9 px-6 rounded-lg bg-[#1C1C1C] text-[#F5F0E8] text-[13px] font-medium flex items-center gap-2 hover:opacity-80 disabled:opacity-30 transition-all">
                {ps.status === "loading"
                  ? <span className="font-mono text-[12px]">처리 중...</span>
                  : <><IconPlay /> 처리 시작</>}
              </button>
            </div>
          </div>

        </div>
      </div>

      <footer className="px-8 py-3 border-t border-[#2E3640]/10 flex items-center justify-between">
        <span className="font-mono text-[10px] text-[#2E3640]/20">pdf-surgeon</span>
        <span className="font-mono text-[10px] text-[#2E3640]/20">FastAPI + Next.js</span>
      </footer>
    </div>
  );
}