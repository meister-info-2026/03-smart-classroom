export interface Device {
  id: string;
  name: string;
  kind: string;
  desired_state?: string | null;
  current_state?: string | null;
  desired_value?: any;
  current_value?: any;
  updated_at?: string | null;
}

export type SeatStatusType = "AVAILABLE" | "RESERVED" | "OCCUPIED" | "MISMATCH";

export interface Seat {
  seat_id: number;
  status: SeatStatusType;
  student_id?: string | null;
  student_name?: string | null;
  reserved_at?: string | null;
  occupied_at?: string | null;
}

export interface AttendanceRecord {
  student_id: string;
  student_name: string;
  status: string;
  seat_id?: number | null;
  check_in_time?: string | null;
}

export interface VisionEventLog {
  event_type: string;
  detected: boolean;
  count: number;
  confidence?: number | null;
  details?: Record<string, any> | null;
  timestamp: string;
  actions_taken?: string[];
}
