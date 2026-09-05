"use client";

import React from "react";
import { VisionEventLog } from "@/types/classroom";
import { Eye, CheckCircle, AlertCircle, Clock } from "lucide-react";

interface VisionLogListProps {
  logs: VisionEventLog[];
}

export const VisionLogList: React.FC<VisionLogListProps> = ({ logs }) => {
  return (
    <div className="bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-xl p-6 shadow-xs">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Eye className="w-5 h-5 text-indigo-600" />
          <h3 className="text-base font-bold text-slate-900 dark:text-zinc-100">
            영상인식 실시간 감지 및 트리거 로그
          </h3>
        </div>
        <span className="text-xs text-slate-400 font-medium">최근 {logs.length}건</span>
      </div>

      <div className="space-y-2.5 max-h-[360px] overflow-y-auto pr-1">
        {logs.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-400">
            수신된 비전 감지 이벤트가 없습니다. (비전 클라이언트 실행 대기)
          </div>
        ) : (
          logs.map((log, idx) => {
            const isAlert = log.event_type.includes("flame") || log.event_type.includes("unrecognized");
            return (
              <div
                key={idx}
                className={`p-3 rounded-lg border text-xs flex items-start justify-between transition-all ${
                  isAlert
                    ? "bg-rose-50/70 border-rose-200 text-rose-800 dark:bg-rose-950/20 dark:border-rose-900"
                    : "bg-slate-50 border-slate-200/80 text-slate-700 dark:bg-zinc-800/40 dark:border-zinc-700"
                }`}
              >
                <div className="flex items-start gap-2.5">
                  <div className="mt-0.5">
                    {isAlert ? (
                      <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
                    ) : (
                      <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0" />
                    )}
                  </div>
                  <div>
                    <div className="font-bold text-slate-900 dark:text-zinc-100 flex items-center gap-2">
                      <span>{log.event_type}</span>
                      {log.confidence && (
                        <span className="text-[10px] font-normal text-slate-400">
                          (신뢰도: {(log.confidence * 100).toFixed(1)}%)
                        </span>
                      )}
                    </div>
                    {log.details && Object.keys(log.details).length > 0 && (
                      <div className="text-[11px] text-slate-500 dark:text-zinc-400 mt-0.5">
                        {JSON.stringify(log.details)}
                      </div>
                    )}
                    {log.actions_taken && log.actions_taken.length > 0 && (
                      <div className="text-[10px] text-indigo-600 dark:text-indigo-400 mt-1 font-semibold">
                        ▶ 실행된 트리거: {log.actions_taken.join(", ")}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-1 text-[11px] text-slate-400 font-mono shrink-0 ml-2" suppressHydrationWarning>
                  <Clock className="w-3 h-3" />
                  {log.timestamp}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default VisionLogList;
