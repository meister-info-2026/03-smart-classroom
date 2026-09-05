"use client";

import React from "react";
import { AttendanceRecord } from "@/types/classroom";
import { Users, CheckCircle, Clock } from "lucide-react";

interface AttendanceTableProps {
  attendance: AttendanceRecord[];
}

export const AttendanceTable: React.FC<AttendanceTableProps> = ({ attendance }) => {
  const presentCount = attendance.filter((a) => a.status === "출석완료").length;

  return (
    <div className="bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-xl p-6 shadow-xs">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Users className="w-5 h-5 text-indigo-600" />
          <h3 className="text-base font-bold text-slate-900 dark:text-zinc-100">
            실시간 학생 출석 및 재실 현황
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2.5 py-1 rounded-md bg-indigo-50 text-indigo-700 font-semibold border border-indigo-200 dark:bg-indigo-950/40 dark:text-indigo-300">
            출석 {presentCount}명 / 총원 {attendance.length}명
          </span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-slate-200 dark:border-zinc-800 text-slate-400 font-semibold uppercase tracking-wider">
              <th className="py-2.5 px-3">학번</th>
              <th className="py-2.5 px-3">학생 이름</th>
              <th className="py-2.5 px-3">출석 상태</th>
              <th className="py-2.5 px-3">배정 좌석</th>
              <th className="py-2.5 px-3">최근 인증 시각</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-zinc-800/60 font-medium">
            {attendance.map((student) => {
              const isPresent = student.status === "출석완료";
              return (
                <tr key={student.student_id} className="hover:bg-slate-50/70 dark:hover:bg-zinc-800/30">
                  <td className="py-3 px-3 font-mono text-slate-500">{student.student_id}</td>
                  <td className="py-3 px-3 text-slate-900 dark:text-zinc-100 font-bold">{student.student_name}</td>
                  <td className="py-3 px-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                        isPresent
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300"
                          : student.status === "좌석선택완료"
                          ? "bg-sky-50 text-sky-700 border border-sky-200"
                          : "bg-slate-100 text-slate-500 border border-slate-200 dark:bg-zinc-800 dark:text-zinc-400"
                      }`}
                    >
                      {isPresent ? <CheckCircle className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
                      {student.status}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    {student.seat_id ? (
                      <span className="font-semibold text-indigo-600 dark:text-indigo-400">
                        좌석 #{student.seat_id}
                      </span>
                    ) : (
                      <span className="text-slate-400">-</span>
                    )}
                  </td>
                  <td className="py-3 px-3 text-slate-500 font-mono" suppressHydrationWarning>
                    {student.check_in_time || "-"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AttendanceTable;
