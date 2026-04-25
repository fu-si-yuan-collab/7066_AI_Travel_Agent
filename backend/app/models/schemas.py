"""Pydantic schemas for API request/response validation.
Pydantic 数据模型：用于 API 请求体和响应体的校验与序列化。
与 ORM 模型分离，遵循「输入/输出各一套 schema」的最佳实践。
"""

from datetime import date
from pydantic import BaseModel, EmailStr, Field


# ─── 认证相关 ────────────────────────────────────────────────
class UserRegister(BaseModel):
    """用户注册请求。"""
    email: EmailStr                         # 邮箱
    password: str = Field(min_length=6)     # 密码（至少6位）
    nickname: str = ""                      # 昵称（可选）


class UserLogin(BaseModel):
    """用户登录请求。"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """登录成功后返回的 JWT Token。"""
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    """用户信息响应（不包含密码）。"""
    id: str
    email: str
    nickname: str

    model_config = {"from_attributes": True}  # 支持从 ORM 对象自动转换


# ─── 行程相关 ────────────────────────────────────────────────
class TripCreate(BaseModel):
    """创建行程请求。"""
    destination: str                        # 目的地（必填）
    origin: str = ""                        # 出发地
    start_date: date | None = None          # 出发日期
    end_date: date | None = None            # 返回日期
    budget: float | None = None             # 总预算
    currency: str = "CNY"                   # 货币
    travel_style: str = "balanced"          # 旅行风格
    notes: str = ""                         # 备注


class TripOut(BaseModel):
    """行程信息响应。"""
    id: str
    title: str
    destination: str
    origin: str
    start_date: date | None
    end_date: date | None
    budget: float | None
    currency: str
    status: str
    travel_style: str

    model_config = {"from_attributes": True}


# ─── 偏好相关 ────────────────────────────────────────────────
class PreferenceUpdate(BaseModel):
    """更新偏好请求（所有字段可选，只更新传入的字段）。"""
    preferred_travel_style: str | None = None
    preferred_transport: str | None = None
    preferred_hotel_stars: float | None = None
    preferred_cuisine: str | None = None
    daily_budget_low: float | None = None
    daily_budget_high: float | None = None
    currency: str | None = None


class PreferenceOut(BaseModel):
    """用户偏好响应。"""
    preferred_travel_style: str
    preferred_transport: str
    preferred_hotel_stars: float
    preferred_cuisine: str
    daily_budget_low: float
    daily_budget_high: float
    currency: str
    learned_tags: dict | None               # ML 团队学习到的标签权重

    model_config = {"from_attributes": True}


# ─── 聊天相关 ────────────────────────────────────────────────
class ChatRequest(BaseModel):
    """对话请求。"""
    message: str                            # 用户消息
    thread_id: str | None = None            # 会话 ID（用于多轮对话）


class ChatResponse(BaseModel):
    """对话响应。"""
    reply: str                              # AI 回复
    thread_id: str                          # 会话 ID
    trip_plan: dict | None = None           # 结构化行程（如果已生成）


# ─── 酒店/机票搜索 ────────────────────────────────────────────
class HotelSearchRequest(BaseModel):
    """酒店搜索请求。"""
    destination: str
    checkin: date
    checkout: date
    guests: int = 2
    star_rating: float | None = None
    max_price: float | None = None


class FlightSearchRequest(BaseModel):
    """机票搜索请求。"""
    origin: str
    destination: str
    departure_date: date
    return_date: date | None = None
    passengers: int = 1
    cabin_class: str = "economy"


# ─── 行为日志 / 反馈 ─────────────────────────────────────────────
class InteractionEventIn(BaseModel):
    """前端埋点事件。"""

    session_id: str | None = None
    event_type: str
    item_type: str
    item_id: str
    item_title: str | None = None
    destination: str | None = None
    travel_style: str | None = None
    budget: float | None = None
    currency: str | None = None
    metadata_json: dict | None = None


class InteractionFeedbackIn(BaseModel):
    """显式反馈事件。"""

    session_id: str | None = None
    item_type: str
    item_id: str
    item_title: str | None = None
    destination: str | None = None
    feedback: str = Field(description="like | dislike | not_relevant")
    metadata_json: dict | None = None
