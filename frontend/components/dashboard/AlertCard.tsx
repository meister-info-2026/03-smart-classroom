"use client";

import React, { useState } from "react";
import { Flame, CheckCircle2 } from "lucide-react";

interface AlertCardProps {
  detected: boolean;
  onResetAlert: () => Promise<void>;
}

export const AlertCard: React.FC<AlertCardProps> = ({ detected, onResetAlert }) => {
  const [resetting, setResetting] = useState(false);

  const handleReset = async () => {
    setResetting(true);
    try {
      await onResetAlert();
    } finally {
      setResetting(false);
    }
  };

  return (
    <div
      className={`col-span-1 md:col-span-2 rounded-xl p-5 border transition-all duration-300 ${
        detected
          ? "bg-rose-50 border-rose-300 dark:bg-rose-950/30 dark:border-rose-800 shadow-md animate-pulse"
          : "bg-white border-slate-200 dark:bg-zinc-900 dark:border-zinc-800 shadow-xs"
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div
            className={`p-3 rounded-xl ${
              detected
                ? "bg-rose-600 text-white"
                : "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400"
            }`}
          >
            {detected ? <Flame className="w-6 h-6 animate-bounce" /> : <CheckCircle2 className="w-6 h-6" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-slate-900 dark:text-zinc-100">
                교실 화재 안전 모니터링 (불꽃 센서 S-04)
              </h3>
              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                  detected
                    ? "bg-rose-600 text-white animate-pulse"
                    : "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300"
                }`}
              >
                {detected ? "위험! 화재 감지됨" : "정상 안전 상태"}
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-zinc-400 mt-1">
              {detected
                ? "교실 내 불꽃이 감지되어 부저 경보 및 비상 프로토콜이 가동되었습니다. 현장을 확인하고 수동으로 경보를 해제하십시오."
                : "미니어처 교실 주변 화재·불꽃 센서 감시 중. 이상 신호가 없습니다."}
            </p>
          </div>
        </div>

        {detected && (
          <button
            onClick={handleReset}
            disabled={resetting}
            className="cursor-pointer shrink-0 ml-4 px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-lg shadow-sm transition-all"
          >
            {resetting ? "해제 중..." : "경보 수동 해제"}
          </button>
        )}
      </div>
    </div>
  );
};

export default AlertCard;
