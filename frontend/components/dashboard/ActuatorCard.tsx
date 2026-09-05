"use client";

import React, { useState } from "react";
import { getStatusBadgeClass } from "@/components/dashboard/statusColor";
import { DoorOpen, Lightbulb, Bell, Sparkles, Sliders } from "lucide-react";

interface ActuatorCardProps {
  id: string;
  name: string;
  state: string;
  value?: unknown;
  onControl: (deviceId: string, desiredState: string, desiredValue?: unknown) => Promise<void>;
}

export const ActuatorCard: React.FC<ActuatorCardProps> = ({
  id,
  name,
  state,
  onControl,
}) => {
  const [loading, setLoading] = useState(false);

  let icon = <Sliders className="w-5 h-5 text-indigo-500" />;
  if (id === "servo_door") icon = <DoorOpen className="w-5 h-5 text-blue-500" />;
  else if (id === "relay_light") icon = <Lightbulb className="w-5 h-5 text-amber-500" />;
  else if (id === "buzzer") icon = <Bell className="w-5 h-5 text-rose-500" />;
  else if (id.includes("led") || id.includes("neopixel")) icon = <Sparkles className="w-5 h-5 text-emerald-500" />;

  const isDoor = id === "servo_door";
  const isOpen = state === "OPEN" || state === "ON";

  const handleToggle = async () => {
    setLoading(true);
    try {
      if (isDoor) {
        const nextState = state === "OPEN" ? "CLOSED" : "OPEN";
        const angle = nextState === "OPEN" ? 90 : 0;
        await onControl(id, nextState, { angle });
      } else {
        const nextState = isOpen ? "OFF" : "ON";
        await onControl(id, nextState, { enabled: !isOpen });
      }
    } finally {
      setLoading(false);
    }
  };

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

      <div className="my-3 flex items-center justify-between">
        <div>
          <div className="text-2xl font-bold tracking-tight text-slate-900 dark:text-zinc-100">
            {isDoor ? (state === "OPEN" ? "문 열림 (90°)" : "문 닫힘 (0°)") : (isOpen ? "켜짐 (ON)" : "꺼짐 (OFF)")}
          </div>
          {isDoor && (
            <div className="text-xs text-slate-500 dark:text-zinc-400 mt-0.5 font-medium">
              열림 시 5초 후 자동 닫힘
            </div>
          )}
          {id === "relay_light" && (
            <div className="text-xs text-slate-500 dark:text-zinc-400 mt-0.5 font-medium">
              재실 인원 1명 이상 시 자동 점등
            </div>
          )}
        </div>

        <button
          onClick={handleToggle}
          disabled={loading}
          className={`cursor-pointer px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all shadow-xs ${
            isOpen
              ? "bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700"
              : "bg-indigo-600 hover:bg-indigo-700 text-white"
          } ${loading ? "opacity-50 cursor-not-allowed" : ""}`}
        >
          {loading ? "처리 중..." : (isDoor ? (state === "OPEN" ? "문 닫기" : "문 열기") : (isOpen ? "끄기" : "켜기"))}
        </button>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-100 dark:border-zinc-800 flex items-center justify-between text-[11px] text-slate-400">
        <span>액추에이터 ID: {id}</span>
        <span>제어 방식: PWM/GPIO</span>
      </div>
    </div>
  );
};

export default ActuatorCard;
