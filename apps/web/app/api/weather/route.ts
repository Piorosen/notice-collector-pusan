import { NextResponse } from "next/server";

const BUSAN_LAT = 35.1796;
const BUSAN_LON = 129.0756;

const WEATHER_CODE_LABEL: Record<number, string> = {
  0: "맑음",
  1: "대체로 맑음",
  2: "부분적으로 흐림",
  3: "흐림",
  45: "안개",
  48: "착빙 안개",
  51: "약한 이슬비",
  53: "이슬비",
  55: "강한 이슬비",
  56: "약한 어는 이슬비",
  57: "강한 어는 이슬비",
  61: "약한 비",
  63: "비",
  65: "강한 비",
  66: "약한 어는 비",
  67: "강한 어는 비",
  71: "약한 눈",
  73: "눈",
  75: "강한 눈",
  77: "싸락눈",
  80: "약한 소나기",
  81: "소나기",
  82: "강한 소나기",
  85: "약한 눈 소나기",
  86: "강한 눈 소나기",
  95: "뇌우",
  96: "약한 우박 동반 뇌우",
  99: "강한 우박 동반 뇌우",
};

export async function GET() {
  try {
    const params = new URLSearchParams({
      latitude: String(BUSAN_LAT),
      longitude: String(BUSAN_LON),
      current: "temperature_2m,weather_code",
      timezone: "Asia/Seoul",
    });

    const res = await fetch(`https://api.open-meteo.com/v1/forecast?${params.toString()}`, {
      cache: "no-store",
    });
    if (!res.ok) throw new Error(`weather api failed: ${res.status}`);
    const json = await res.json();

    const temp = json?.current?.temperature_2m;
    const code = json?.current?.weather_code;
    const unit = json?.current_units?.temperature_2m || "°C";
    const weather = typeof code === "number" ? WEATHER_CODE_LABEL[code] || "날씨 정보" : "날씨 정보";

    return NextResponse.json({
      location: "부산",
      temperature: typeof temp === "number" ? temp : null,
      temperature_unit: unit,
      weather,
      fetched_at: new Date().toISOString(),
    });
  } catch {
    return NextResponse.json(
      {
        location: "부산",
        temperature: null,
        temperature_unit: "°C",
        weather: "날씨 정보 없음",
        fetched_at: new Date().toISOString(),
      },
      { status: 200 },
    );
  }
}
