"use client";

import React from "react";
import { getStatusBadgeClass } from "@/components/dashboard/statusColor";
import { Thermometer, Magnet, Video, Activity } from "lucide-react";

interface SensorCardProps {
  id: string;
  name: string;
  state: string;
  value: unknown;
  updatedAt?: string | null;
}

export const SensorCard: React.FC<SensorCardProps> = ({
  id,
  name,
  state,
  value,
  updatedAt,
}) => {
  let icon = <Activity className="w-5 h-5 text-slate-500" />;
  let mainDisplay = state;
  let subDisplay = "";

  const valObj = (typeof value === "object" && value !== null ? value : {}) as Record<string, unknown>;

  if (id === "dht_sensor") {
    icon = <Thermometer className="w-5 h-5 text-sky-500" />;
    const temp = typeof valObj.temperature_c === "number" ? valObj.temperature_c : 23.5;
    const hum = typeof valObj.humidity_pct === "number" ? valObj.humidity_pct : 52.0;
    mainDisplay = `${temp}°C`;
    subDisplay = `습도 ${hum}%`;
  } else if (id === "reed_switch") {
    icon = <Magnet className="w-5 h-5 text-amber-500" />;
    mainDisplay = state === "CLOSED" ? "닫힘" : "열림";
    subDisplay = state === "CLOSED" ? "접촉 감지 (정상)" : "문 열림 감지";
  } else if (id.startsWith("cam_")) {
    icon = <Video className="w-5 h-5 text-indigo-500" />;
    mainDisplay = state;
    subDisplay = valObj.fps ? `${valObj.fps} FPS / 1080p` : "실시간 감시 중";
  }

  return (
    <div className="bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-xl p-5 shadow-xs transition-all hover:shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-slate-50 dark:bg-zinc-800">{icon}</div>
          <span className="text-xs font-semibold text-slate-500 dark:text-zinc-400 tracking-wide">
            {name}
          </span>
        </div>
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${getStatusBadgeClass(state)}`}>
          {state}
        </span>
      </div>

      <div className="my-2">
        <div className="text-3xl font-bold tracking-tight text-slate-900 dark:text-zinc-100">
          {mainDisplay}
        </div>
        {subDisplay && (
          <div className="text-xs text-slate-500 dark:text-zinc-400 mt-1 font-medium">
            {subDisplay}
          </div>
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-slate-100 dark:border-zinc-800 flex items-center justify-between text-[11px] text-slate-400">
        <span>센서 ID: {id}</span>
        <span suppressHydrationWarning>
          {updatedAt ? new Date(updatedAt).toLocaleTimeString() : "실시간 동기화"}
        </span>
      </div>
    </div>
  );
};

export default SensorCard;
