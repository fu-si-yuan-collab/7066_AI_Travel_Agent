"""Calendar export endpoint – generates .ics file from itinerary events.
日历导出接口 —— 从行程事件生成标准 iCalendar (.ics) 文件，
可导入 Apple 日历、Google 日历、Outlook 等任意日历 App。
无需额外 API Key，纯字符串生成。
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter()


class CalendarEvent(BaseModel):
    date: str         # "2024-06-15"
    time: str         # "09:00"
    title: str
    description: str = ""


def _build_ics(events: list[CalendarEvent]) -> str:
    """生成标准 iCalendar 格式字符串。"""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AI Travel Agent//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for e in events:
        # Parse start time
        try:
            h, m = int(e.time[:2]), int(e.time[3:5])
        except (ValueError, IndexError):
            h, m = 9, 0

        # End time = start + 90 minutes
        total_minutes = h * 60 + m + 90
        end_h = (total_minutes // 60) % 24
        end_m = total_minutes % 60

        date_str = e.date.replace("-", "")
        dt_start = f"{date_str}T{h:02d}{m:02d}00"
        dt_end = f"{date_str}T{end_h:02d}{end_m:02d}00"

        # Escape special characters for ICS
        summary = e.title.replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")[:75]
        desc = e.description.replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")[:200]

        lines += [
            "BEGIN:VEVENT",
            f"DTSTART:{dt_start}",
            f"DTEND:{dt_end}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{desc}",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


@router.post("/generate")
async def generate_ics(events: list[dict]):
    """接收事件列表，返回 .ics 文件供下载。"""
    parsed = [CalendarEvent(**e) for e in events if e.get("date") and e.get("title")]
    ics_content = _build_ics(parsed)
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=travel_plan.ics"},
    )
