"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Device, Seat, AttendanceRecord, VisionEventLog } from "@/types/classroom";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useSmartClassroomSocket() {
  const [connected, setConnected] = useState(false);
  const [devices, setDevices] = useState<Device[]>([]);
  const [seats, setSeats] = useState<Seat[]>([]);
  const [attendance, setAttendance] = useState<AttendanceRecord[]>([]);
  const [visionLogs, setVisionLogs] = useState<VisionEventLog[]>([]);
  const [flameAlert, setFlameAlert] = useState(false);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const connectFnRef = useRef<() => void>(() => {});

  // 초기 REST API 데이터 로드
  const fetchInitialData = useCallback(async () => {
    try {
      const [devRes, seatRes, attRes] = await Promise.all([
        fetch(`${API_BASE}/api/devices`),
        fetch(`${API_BASE}/api/seats`),
        fetch(`${API_BASE}/api/attendance`),
      ]);
      if (devRes.ok) {
        const d = await devRes.json();
        setDevices(d.data || []);
      }
      if (seatRes.ok) {
        const s = await seatRes.json();
        setSeats(s.data || []);
      }
      if (attRes.ok) {
        const a = await attRes.json();
        setAttendance(a.data || []);
      }
    } catch {
      // 서버 미구동 시 대기
    }
  }, []);

  const connectWebSocket = useCallback(() => {
    if (
      socketRef.current &&
      (socketRef.current.readyState === WebSocket.OPEN ||
        socketRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    try {
      const ws = new WebSocket(WS_URL);
      socketRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === "init_state") {
            if (msg.devices) setDevices(msg.devices);
            if (msg.seats) setSeats(msg.seats);
            if (msg.attendance) setAttendance(msg.attendance);
          } else if (msg.type === "device_update") {
            setDevices((prev) =>
              prev.map((d) =>
                d.id === msg.device_id
                  ? {
                      ...d,
                      desired_state:
                        msg.desired_state !== undefined ? msg.desired_state : d.desired_state,
                      current_state:
                        msg.current_state !== undefined ? msg.current_state : d.current_state,
                      current_value:
                        msg.current_value !== undefined ? msg.current_value : d.current_value,
                    }
                  : d
              )
            );
            if (msg.device_id === "flame_sensor") {
              setFlameAlert(msg.current_state === "DETECTED");
            }
          } else if (msg.type === "seat_update") {
            if (msg.seats) setSeats(msg.seats);
          } else if (msg.type === "vision_event") {
            if (msg.event) {
              setVisionLogs((prev) => [msg.event, ...prev].slice(0, 30));
              if (msg.event.event_type === "flame_detected" && msg.event.detected) {
                setFlameAlert(true);
              }
            }
            if (msg.seats) setSeats(msg.seats);
            if (msg.attendance) setAttendance(msg.attendance);
            if (msg.devices) {
              setDevices((prev) => {
                const map = new Map(msg.devices.map((d: Device) => [d.id, d]));
                return prev.map((d) => {
                  const updated = map.get(d.id);
                  return updated ? { ...d, ...updated } : d;
                });
              });
            }
          } else if (msg.type === "sensor_tick") {
            if (msg.sensors) {
              setDevices((prev) =>
                prev.map((d) => {
                  if (msg.sensors[d.id]) {
                    const s = msg.sensors[d.id];
                    return {
                      ...d,
                      current_state: s.state !== undefined ? s.state : d.current_state,
                      current_value: s.value !== undefined ? s.value : d.current_value,
                    };
                  }
                  return d;
                })
              );
              if (msg.sensors.flame_sensor?.state === "DETECTED") {
                setFlameAlert(true);
              }
            }
          }
        } catch {
          // JSON 파싱 방어
        }
      };

      ws.onclose = () => {
        setConnected(false);
        socketRef.current = null;
        reconnectTimeoutRef.current = setTimeout(() => {
          connectFnRef.current();
        }, 2000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      setConnected(false);
      reconnectTimeoutRef.current = setTimeout(() => {
        connectFnRef.current();
      }, 2000);
    }
  }, []);

  connectFnRef.current = connectWebSocket;

  useEffect(() => {
    let ignore = false;
    async function init() {
      if (!ignore) {
        await fetchInitialData();
        connectWebSocket();
      }
    }
    init();

    return () => {
      ignore = true;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) socketRef.current.close();
    };
  }, [connectWebSocket, fetchInitialData]);

  // 디바이스 제어 함수
  const controlDevice = async (deviceId: string, desiredState: string, desiredValue: unknown = null) => {
    try {
      await fetch(`${API_BASE}/api/devices/${deviceId}/control`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          desired_state: desiredState,
          desired_value: desiredValue,
          operator: "user",
        }),
      });
    } catch {
      // 제어 요청 실패 방어
    }
  };

  // 경보 해제 함수
  const resetAlert = async (deviceId: string) => {
    try {
      await fetch(`${API_BASE}/api/devices/${deviceId}/reset-alert`, {
        method: "POST",
      });
      if (deviceId === "flame_sensor") {
        setFlameAlert(false);
      }
    } catch {
      // 해제 실패 방어
    }
  };

  // 좌석 예약 함수
  const reserveSeat = async (seatId: number, studentId: string, studentName: string) => {
    try {
      await fetch(`${API_BASE}/api/seats/${seatId}/reserve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ student_id: studentId, student_name: studentName }),
      });
    } catch {
      // 예약 실패 방어
    }
  };

  // 좌석 퇴실/해제 함수
  const releaseSeat = async (seatId: number) => {
    try {
      await fetch(`${API_BASE}/api/seats/${seatId}/release`, {
        method: "POST",
      });
    } catch {
      // 해제 실패 방어
    }
  };

  return {
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
  };
}
