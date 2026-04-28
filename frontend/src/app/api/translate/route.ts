import { NextRequest, NextResponse } from "next/server";

const FASTAPI_URL = process.env.FASTAPI_URL ?? "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  try {
    // 1. 클라이언트의 Content-Type 헤더 가져오기 (여기에 boundary 정보가 포함되어 있음)
    const contentType = req.headers.get("content-type");
    
    if (!contentType) {
      return NextResponse.json({ detail: "Content-Type이 없습니다." }, { status: 400 });
    }

    // 2. formData()로 파싱하지 않고, req.body(스트림)를 그대로 넘김
    const upstream = await fetch(`${FASTAPI_URL}/translate/`, {
      method: "POST",
      headers: {
        "Content-Type": contentType, // 필수: boundary 유지
      },
      body: req.body, 
      // Node 18+ fetch에서 스트림 body를 보낼 때 필요한 옵션 (Next.js 환경에 따라 에러 방지)
      // @ts-ignore
      duplex: "half", 
    });

    if (!upstream.ok) {
      const err = await upstream.json().catch(() => ({ detail: "서버 오류" }));
      return NextResponse.json(
        { detail: err.detail ?? "서버 오류" },
        { status: upstream.status }
      );
    }

    // 3. 정상 처리된 경우 PDF 반환
    const pdfBuffer = await upstream.arrayBuffer();
    return new NextResponse(pdfBuffer, {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": upstream.headers.get("Content-Disposition") ?? "",
      },
    });
// src/app/api/translate/route.ts (제일 하단)
  } catch (e) {
    // 터미널에 상세 에러 로깅
    console.error("Next.js 프록시 에러:", e); 
    
    const message = e instanceof Error ? e.message : "알 수 없는 오류";
    return NextResponse.json({ detail: `Next.js 에러: ${message}` }, { status: 500 });
  }
}