"""All Pydantic models for the Text2trade API."""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional, Literal


class HealthResponse(BaseModel):
    status: str
    mongodb: bool

class RootResponse(BaseModel):
    message: str
    app_name: str


# --- Strategy models ---

class IndicatorCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=50)
    params: dict = Field(default_factory=dict)
    operator: str = Field(max_length=30)
    value: Optional[float] = None

    @field_validator("name", "operator", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("value")
    @classmethod
    def validate_value(cls, v):
        if isinstance(v, (int, float)) and (v < -10000 or v > 10000):
            raise ValueError("Value must be between -10000 and 10000")
        return v

class Metadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    tags: List[str] = Field(default_factory=list, max_length=10)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @field_validator("name", "description", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return v.strip() if isinstance(v, str) else v

class Market(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str = Field(max_length=50)
    exchange: Optional[str] = Field(default=None, max_length=50)

    @field_validator("type", "exchange", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return v.strip() if isinstance(v, str) else v

class Instrument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str = Field(min_length=1, max_length=20)
    base: Optional[str] = Field(default=None, max_length=10)
    quote: Optional[str] = Field(default=None, max_length=10)

    @field_validator("symbol", "base", "quote", mode="before")
    @classmethod
    def strip_and_upper(cls, v):
        return v.strip().upper() if isinstance(v, str) else v

class Timeframe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    interval: str = Field(max_length=10)
    candle_count: Optional[int] = Field(default=None, ge=1, le=1000)

    @field_validator("interval", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return v.strip() if isinstance(v, str) else v

class StopLoss(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["percentage", "points", "atr_multiple"] = "percentage"
    value: float = Field(ge=0.1, le=50)

class TrailingStopLoss(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    type: Literal["percentage", "points"] = "percentage"
    value: float = Field(ge=0.1, le=20, default=1.0)
    activation_profit: float = Field(ge=0, le=50, default=0)

class TargetProfit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["percentage", "points"] = "percentage"
    value: float = Field(ge=0.1, le=100)

class TimeBasedExit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    exit_time: str = Field(default="15:10", pattern=r"^\d{2}:\d{2}$")

class DailyLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_loss_per_day: float = Field(ge=0, le=100, default=5.0)
    max_trades_per_day: int = Field(ge=1, le=50, default=10)

class PositionSizing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: Literal["fixed_quantity", "percent_capital", "risk_per_trade"] = "fixed_quantity"
    value: float = Field(ge=0.1, le=100, default=1)

class RiskManagement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stop_loss: Optional[StopLoss] = None
    trailing_stop_loss: TrailingStopLoss = Field(default_factory=TrailingStopLoss)
    target_profit: Optional[TargetProfit] = None
    time_based_exit: TimeBasedExit = Field(default_factory=TimeBasedExit)
    daily_limits: DailyLimits = Field(default_factory=DailyLimits)
    position_sizing: PositionSizing = Field(default_factory=lambda: PositionSizing(method="fixed_quantity", value=1))

class Strategy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Optional[str] = Field(default=None, max_length=50)
    version: str = Field(default="1.0", max_length=10)
    user_id: Optional[str] = Field(default=None, max_length=50)
    is_demo: Optional[bool] = Field(default=False)
    demo_tag: Optional[str] = Field(default=None, max_length=50)
    metadata: Metadata
    market: Market
    instrument: Instrument
    timeframe: Timeframe
    entry_conditions: List[IndicatorCondition] = Field(default_factory=list, max_length=10)
    exit_conditions: List[IndicatorCondition] = Field(default_factory=list, max_length=10)
    filters: List[IndicatorCondition] = Field(default_factory=list, max_length=5)
    risk_management: RiskManagement

class StrategyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: bool
    strategy: Strategy

class StrategiesListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: bool
    strategies: List[Strategy]
    count: int
