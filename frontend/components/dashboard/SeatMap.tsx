"use client";

import React, { useState } from "react";
import { Seat } from "@/types/classroom";
import { UserCheck, UserX, AlertTriangle, Armchair } from "lucide-react";

interface SeatMapProps {
  seats: Seat[];
  onReserveSeat: (seatId: number, studentId: string, studentName: string) => Promise<void>;
  onReleaseSeat: (seatId: number) => Promise<void>;
}

export const SeatMap: React.FC<SeatMapProps> = ({
  seats,
  onReserveSeat,
  onReleaseSeat,
}) => {
  const [studentId] = useState("202601");
  const [studentName] = useState("김재민");

  const handleQuickReserve = async (seatId: number) => {
    await onReserveSeat(seatId, studentId, studentName);
  };

  const getSeatBadge = (status: string) => {
    switch (status) {
      case "OCCUPIED":
        return {
          bg: "bg-emerald-50 border-emerald-300 dark:bg-emerald-950/40 dark:border-emerald-700",
          text: "text-emerald-700 dark:text-emerald-300",
          label: "정상 착석",
          icon: <UserCheck className="w-4 h-4 text-emerald-600" />,
        };
      case "RESERVED":
        return {
          bg: "bg-sky-50 border-sky-300 dark:bg-sky-950/40 dark:border-sky-700",
          text: "text-sky-700 dark:text-sky-300",
          label: "좌석 예약됨",
          icon: <Armchair className="w-4 h-4 text-sky-600" />,
        };
      case "MISMATCH":
        return {
          bg: "bg-rose-50 border-rose-400 dark:bg-rose-950/40 dark:border-rose-700 animate-pulse",
          text: "text-rose-700 dark:text-rose-300",
          label: "좌석 불일치 경고",
          icon: <AlertTriangle className="w-4 h-4 text-rose-600" />,
        };
      default:
        return {
          bg: "bg-slate-50 border-slate-200 dark:bg-zinc-800/50 dark:border-zinc-700",
          text: "text-slate-500 dark:text-zinc-400",
          label: "빈 좌석",
          icon: <UserX className="w-4 h-4 text-slate-400" />,
        };
    }
  };

  return (
    <div className="bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-xl p-6 shadow-xs">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 mb-6">
        <div>
          <h3 className="text-base font-bold text-slate-900 dark:text-zinc-100 flex items-center gap-2">
            <Armchair className="w-5 h-5 text-indigo-600" />
            6석 교실 배치도 및 좌석 실시간 판정 모니터
          </h3>
          <p className="text-xs text-slate-500 dark:text-zinc-400 mt-1">
            카메라 ROI 착석 검출 및 Neopixel 연동 상태 (초록: 정상 / 파랑: 예약 / 빨강: 불일치)
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1.5 text-slate-500">
            <span className="w-2.5 h-2.5 rounded-full bg-slate-300" /> 빈좌석
          </span>
          <span className="flex items-center gap-1.5 text-sky-600 font-medium">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-500" /> 예약됨
          </span>
          <span className="flex items-center gap-1.5 text-emerald-600 font-medium">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> 착석
          </span>
          <span className="flex items-center gap-1.5 text-rose-600 font-medium">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse" /> 불일치
          </span>
        </div>
      </div>

      {/* 교탁 / 칠판 표시 */}
      <div className="w-full py-1.5 mb-6 text-center text-xs font-semibold tracking-wider text-slate-400 bg-slate-100 dark:bg-zinc-800 rounded-lg border border-dashed border-slate-300 dark:border-zinc-700">
        [ 전 면 ] 교 탁 및 스 크 린
      </div>

      {/* 6석 그리드 (3열 x 2행) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        {seats.map((seat) => {
          const badge = getSeatBadge(seat.status);
          const isOccupiedOrReserved = seat.status !== "AVAILABLE";

          return (
            <div
              key={seat.seat_id}
              className={`border-2 rounded-xl p-4 transition-all duration-200 ${badge.bg}`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-slate-700 dark:text-zinc-300">
                  좌석 #{seat.seat_id}
                </span>
                <div className="flex items-center gap-1.5">
                  {badge.icon}
                  <span className={`text-[11px] font-bold ${badge.text}`}>
                    {badge.label}
                  </span>
                </div>
              </div>

              <div className="min-h-[50px] flex flex-col justify-center">
                {seat.student_name ? (
                  <div>
                    <div className="text-sm font-bold text-slate-900 dark:text-zinc-100">
                      {seat.student_name}{" "}
                      <span className="text-xs font-normal text-slate-500">
                        ({seat.student_id})
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5" suppressHydrationWarning>
                      {seat.occupied_at
                        ? `착석 확인: ${seat.occupied_at}`
                        : seat.reserved_at
                        ? `예약 완료: ${seat.reserved_at}`
                        : ""}
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-slate-400 font-medium">
                    지정된 학생 없음
                  </div>
                )}
              </div>

              <div className="mt-3 pt-2.5 border-t border-slate-200/60 dark:border-zinc-700/60 flex items-center justify-end gap-2">
                {isOccupiedOrReserved ? (
                  <button
                    onClick={() => onReleaseSeat(seat.seat_id)}
                    className="cursor-pointer px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:text-slate-800 bg-white dark:bg-zinc-800 border border-slate-300 dark:border-zinc-700 rounded-md shadow-2xs hover:bg-slate-50"
                  >
                    퇴실/해제
                  </button>
                ) : (
                  <button
                    onClick={() => handleQuickReserve(seat.seat_id)}
                    className="cursor-pointer px-2.5 py-1 text-[11px] font-semibold text-indigo-600 hover:text-indigo-700 bg-white dark:bg-zinc-800 border border-indigo-200 dark:border-indigo-900/60 rounded-md shadow-2xs hover:bg-indigo-50"
                  >
                    좌석 배정
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default SeatMap;
