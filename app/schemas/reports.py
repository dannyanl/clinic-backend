from datetime import date
from decimal import Decimal
from pydantic import BaseModel


class OccupancyReport(BaseModel):
    doctor_id: int
    doctor_name: str
    total_slots: int
    booked_slots: int
    occupancy_rate: float


class CancellationReport(BaseModel):
    period_start: date
    period_end: date
    total: int
    cancelled: int
    no_show: int
    cancellation_rate: float


class RevenueReport(BaseModel):
    period_start: date
    period_end: date
    total_revenue: Decimal
    by_doctor: dict[str, Decimal]


class DashboardMetrics(BaseModel):
    total_patients: int
    total_doctors: int
    appointments_today: int
    appointments_pending: int
    revenue_month: Decimal
