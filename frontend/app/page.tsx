"use client";

import React, { useEffect, useState } from "react";
import ConnectionBadge from "@/components/dashboard/ConnectionBadge";
import SensorCard from "@/components/dashboard/SensorCard";
import ActuatorCard from "@/components/dashboard/ActuatorCard";
import AlertCard from "@/components/dashboard/AlertCard";
import SeatMap from "@/components/dashboard/SeatMap";
import AttendanceTable from "@/components/dashboard/AttendanceTable";
import VisionLogList from "@/components/dashboard/VisionLogList";
import { useSmartClassroomSocket } from "@/hooks/useSmartClassroomSocket";
import {
  GraduationCap,
  Users,
  Lightbulb,
  DoorOpen,
  Thermometer,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

export default function Home() {
  const {
    connected,
    devices,
    seats,
    attendance,
    visionLogs,
    flameAlert,
    controlDevice,
    resetAlert,
    reserveSeat,
    releaseSeat,
  } = useSmartClassroomSocket();

  const [currentTime, setCurrentTime] = useState<string>("");

  useEffect(() => {
    const updateTime = () => {
      setCurrentTime(new Date().toLocaleTimeString("ko-KR", { hour12: false }));
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  // 장치 필터링
  const actuators = devices.filter((d) =>
    ["servo_door", "relay_light", "buzzer", "seat_led", "neopixel_seat"].includes(d.id)
  );
  const sensors = devices.filter((d) =>
    ["dht_sensor", "reed_switch", "cam_entrance", "cam_classroom"].includes(d.id)
  );

  // 요약 지표 계산
  const presentCount = attendance.filter((a) => a.status === "출석완료").length;
  const occupiedSeatCount = seats.filter((s) => s.status === "OCCUPIED").length;
  const lightDevice = devices.find((d) => d.id === "relay_light");
  const doorDevice = devices.find((d) => d.id === "servo_door");
  const dhtDevice = devices.find((d) => d.id === "dht_sensor");

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 text-slate-900 dark:text-zinc-100 p-4 sm:p-6 md:p-8 font-sans transition-colors">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* ==================================================================== */}
        {/* 상단 헤더 & 연결 상태 & 시계 */}
        {/* ==================================================================== */}
        <header className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-6 border-b border-slate-200 dark:border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-600 text-white shadow-xs">
              <GraduationCap className="w-7 h-7" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-zinc-100 flex items-center gap-2">
                스마트 교실 출입·출석·재실 통합 관리 시스템
                <span className="text-xs px-2 py-0.5 rounded-md bg-indigo-100 text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-300 font-medium">
                  Mockup v1.0
                </span>
              </h1>
              <p className="text-xs text-slate-500 dark:text-zinc-400 mt-0.5 font-medium">
                얼굴 인식 & 교실 카메라 ROI 판정 기반 IoT 스마트 제어 대시보드
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 self-end md:self-auto">
            <div
              className="text-xs font-mono font-semibold px-3 py-1.5 rounded-lg bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 text-slate-700 dark:text-zinc-300 shadow-2xs"
              suppressHydrationWarning
            >
              🕒 {currentTime || "00:00:00"}
            </div>
            <ConnectionBadge connected={connected} />
          </div>
        </header>

        {/* ==================================================================== */}
        {/* KPI 빠른 요약 카드 4종 */}
        {/* ==================================================================== */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-zinc-900 p-4 rounded-xl border border-slate-200 dark:border-zinc-800 shadow-xs">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="text-xs font-semibold">출석 현황</span>
              <Users className="w-4 h-4 text-indigo-500" />
            </div>
            <div className="text-2xl font-bold text-slate-900 dark:text-zinc-100">
              {presentCount} / {attendance.length}명
            </div>
            <div className="text-[11px] text-emerald-600 font-medium mt-1">
              출석률 {Math.round((presentCount / (attendance.length || 1)) * 100)}%
            </div>
          </div>

          <div className="bg-white dark:bg-zinc-900 p-4 rounded-xl border border-slate-200 dark:border-zinc-800 shadow-xs">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="text-xs font-semibold">교실 재실 & 조명</span>
              <Lightbulb className="w-4 h-4 text-amber-500" />
            </div>
            <div className="text-2xl font-bold text-slate-900 dark:text-zinc-100">
              착석 {occupiedSeatCount}석
            </div>
            <div className="text-[11px] text-slate-500 dark:text-zinc-400 mt-1 font-medium">
              조명: {lightDevice?.current_state === "ON" ? "점등 중 (ON)" : "소등 상태 (OFF)"}
            </div>
          </div>

          <div className="bg-white dark:bg-zinc-900 p-4 rounded-xl border border-slate-200 dark:border-zinc-800 shadow-xs">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="text-xs font-semibold">자동문 상태</span>
              <DoorOpen className="w-4 h-4 text-blue-500" />
            </div>
            <div className="text-2xl font-bold text-slate-900 dark:text-zinc-100">
              {doorDevice?.current_state === "OPEN" ? "문 열림" : "문 닫힘"}
            </div>
            <div className="text-[11px] text-slate-500 dark:text-zinc-400 mt-1 font-medium">
              MG90S 서보 / 리드스위치
            </div>
          </div>

          <div className="bg-white dark:bg-zinc-900 p-4 rounded-xl border border-slate-200 dark:border-zinc-800 shadow-xs">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="text-xs font-semibold">교실 온습도</span>
              <Thermometer className="w-4 h-4 text-sky-500" />
            </div>
            <div className="text-2xl font-bold text-slate-900 dark:text-zinc-100">
              {dhtDevice?.current_value?.temperature_c ?? 23.5}°C
            </div>
            <div className="text-[11px] text-slate-500 dark:text-zinc-400 mt-1 font-medium">
              습도 {dhtDevice?.current_value?.humidity_pct ?? 52.0}%
            </div>
          </div>
        </div>

        {/* ==================================================================== */}
        {/* 화재 안전 모니터링 경보 카드 (AlertCard) */}
        {/* ==================================================================== */}
        <AlertCard
          detected={flameAlert}
          onResetAlert={() => resetAlert("flame_sensor")}
        />

        {/* ==================================================================== */}
        {/* 6석 교실 배치도 (SeatMap) */}
        {/* ==================================================================== */}
        <SeatMap
          seats={seats}
          onReserveSeat={reserveSeat}
          onReleaseSeat={releaseSeat}
        />

        {/* ==================================================================== */}
        {/* 액추에이터 제어 패널 (서보모터, 조명, 부저, LED, 네오픽셀) */}
        {/* ==================================================================== */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-5 h-5 text-indigo-600" />
            <h2 className="text-base font-bold text-slate-900 dark:text-zinc-100">
              액추에이터 원격 제어 패널 (5종)
            </h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {actuators.map((dev) => (
              <ActuatorCard
                key={dev.id}
                id={dev.id}
                name={dev.name}
                state={dev.current_state || dev.desired_state || "OFF"}
                value={dev.current_value}
                onControl={controlDevice}
              />
            ))}
          </div>
        </div>

        {/* ==================================================================== */}
        {/* 센서 실시간 모니터링 카드 (온습도, 리드스위치, 카메라) */}
        {/* ==================================================================== */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <ShieldCheck className="w-5 h-5 text-indigo-600" />
            <h2 className="text-base font-bold text-slate-900 dark:text-zinc-100">
              센서 및 입력 장치 실시간 모니터링 (4종)
            </h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {sensors.map((dev) => (
              <SensorCard
                key={dev.id}
                id={dev.id}
                name={dev.name}
                state={dev.current_state || "ONLINE"}
                value={dev.current_value}
                updatedAt={dev.updated_at}
              />
            ))}
          </div>
        </div>

        {/* ==================================================================== */}
        {/* 하단: 출석부 현황 + 비전 실시간 로그 리스트 */}
        {/* ==================================================================== */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-2">
          <AttendanceTable attendance={attendance} />
          <VisionLogList logs={visionLogs} />
        </div>
      </div>
    </div>
  );
}
