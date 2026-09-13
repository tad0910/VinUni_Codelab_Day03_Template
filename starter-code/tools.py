import json
import os
from typing import List, Dict, Any, Callable

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "raw-data")

def get_flight_info(origin: str, destination: str, max_price: Any = 5000000) -> List[Dict[str, Any]]:
    """
    Search for flights matching origin, destination, and budget constraint.
    Hỗ trợ tự động ép kiểu max_price từ string/int.
    """
    flight_file = os.path.join(RAW_DATA_DIR, "flight_data.json")
    if not os.path.exists(flight_file):
        return []
    
    # Xử lý Trap: ép kiểu max_price an toàn nếu LLM truyền dạng chuỗi "2000000" hoặc "2.0"
    try:
        if isinstance(max_price, str):
            max_price = int(float(max_price.replace(".", "").replace(",", "").replace("VND", "").strip()))
        else:
            max_price = int(max_price)
    except (ValueError, TypeError):
        max_price = 5000000

    with open(flight_file, "r", encoding="utf-8") as f:
        flights = json.load(f)
    
    results = [
        fl for fl in flights
        if fl["origin"].strip().upper() == str(origin).strip().upper()
        and fl["destination"].strip().upper() == str(destination).strip().upper()
        and fl["price_vnd"] <= max_price
    ]
    return results

def get_weather_forecast(city_code: str) -> Dict[str, Any]:
    """
    Get weather forecast and outfit recommendation for a city code (e.g. SGN, HAN, DAD).
    """
    weather_file = os.path.join(RAW_DATA_DIR, "weather_data.json")
    if not os.path.exists(weather_file):
        return {"error": "Weather data file not found"}
    
    with open(weather_file, "r", encoding="utf-8") as f:
        weather_data = json.load(f)
    
    clean_code = str(city_code).strip().upper()
    return weather_data.get(clean_code, {"error": f"No weather data found for city code '{city_code}'"})

# Tool Registry for ReAct Agent
TOOL_DEFINITIONS = [
    {
        "name": "get_flight_info",
        "description": "Tìm chuyến bay theo điểm đi, điểm đến và giá tối đa.",
        "parameters": {
            "origin": "Mã sân bay đi (VD: HAN)",
            "destination": "Mã sân bay đến (VD: SGN)",
            "max_price": "Giá vé tối đa dạng số nguyên (VND)"
        }
    },
    {
        "name": "get_weather_forecast",
        "description": "Lấy thông tin thời tiết và gợi ý trang phục theo mã sân bay/thành phố (SGN, HAN, DAD).",
        "parameters": {
            "city_code": "Mã sân bay thành phố (VD: SGN)"
        }
    }
]

# Mapping tên tool với hàm thực thi (Milestone 2)
TOOL_MAP: Dict[str, Callable] = {
    "get_flight_info": get_flight_info,
    "get_weather_forecast": get_weather_forecast
}

def get_tool(tool_name: str) -> Callable:
    """
    Xử lý Trap 1: KeyError khi gọi Tool do viết hoa hoặc có khoảng trắng (VD: 'Get_Flight_Info ').
    """
    clean_name = str(tool_name).strip().lower()
    if clean_name in TOOL_MAP:
        return TOOL_MAP[clean_name]
    raise KeyError(f"Tool '{tool_name}' không tồn tại trong TOOL_MAP. Danh sách tool khả dụng: {list(TOOL_MAP.keys())}")

