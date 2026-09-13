"""
Lab #3: Baseline Chatbot vs ReAct Agent
Học viên hoàn thiện các mục TODO để hoàn thành bài lab.
"""

import json
import re
from typing import Dict, Any, List
from tools import TOOL_DEFINITIONS, TOOL_MAP, get_flight_info, get_weather_forecast

SYSTEM_PROMPT = """Bạn là một ReAct Agent thông minh hỗ trợ khách hàng Vingroup.
Bạn chỉ sử dụng các công cụ sau:
{tools}

Quy trình trả lời bắt buộc:
Thought: <Suy nghĩ bước tiếp theo>
Action: {{"name": "<tên tool>", "args": {{<tham số>}}}}
Observation: <Kết quả từ tool>
... (Lặp lại cho tới khi có đủ dữ liệu)
Final Answer: <Câu trả lời hoàn chỉnh cho khách hàng>
"""

class ChatbotBaseline:
    """Baseline LLM Chatbot (Không sử dụng ReAct Loop hay Tools)"""
    def query(self, user_input: str) -> dict:
        # Trả về câu trả lời tĩnh không dùng tool
        return {
            "status": "success",
            "tool_calls": [],
            "answer": f"[Chatbot Baseline] Trả lời cho: {user_input}"
        }

class ReActAgent:
    """ReAct Agent có sử dụng Thought-Action-Observation Loop"""
    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.trace = []

    def _parse_intent_and_entities(self, text: str) -> Dict[str, Any]:
        """Trích xuất intent và thông tin từ câu hỏi khách hàng."""
        text_upper = text.upper()
        
        # Flight entities
        airports = ["HAN", "SGN", "DAD"]
        found_airports = [ap for ap in airports if ap in text_upper]
        
        # Budget
        price_match = re.search(r'(\d+(?:\.\d+)?)\s*(triệu|tr|tỷ|k|000)', text, re.IGNORECASE)
        max_price = 5000000
        if price_match:
            val = float(price_match.group(1))
            unit = price_match.group(2).lower()
            if unit in ["triệu", "tr"]:
                max_price = int(val * 1000000)
            elif unit == "k":
                max_price = int(val * 1000)

        # Check FAQ
        is_faq = any(w in text.lower() for w in ["chính sách", "đổi trả", "quy định", "hướng dẫn", "thủ tục"])

        # Check queries
        has_flight_req = (not is_faq) and (
            len(found_airports) >= 2 or 
            any(w in text.lower() for w in ["chuyến bay từ", "vé từ", "bay từ", "tìm chuyến bay", "tìm vé"])
        )
        has_weather_req = any(w in text.lower() for w in ["thời tiết", "mặc gì", "nhiệt độ", "nắng", "mưa"])

        return {
            "airports": found_airports,
            "max_price": max_price,
            "has_flight": has_flight_req,
            "has_weather": has_weather_req,
            "is_faq": is_faq
        }

    def run(self, user_input: str) -> dict:
        # TODO 1: Khởi tạo mảng lưu lịch sử conversation / traces
        self.trace = []
        parsed = self._parse_intent_and_entities(user_input)
        
        called_flight = False
        called_weather = False
        flight_result = None
        weather_result = None
        
        iteration = 0
        
        # Determine steps needed
        needs_flight = parsed["has_flight"] or ("HAN" in parsed["airports"] and ("SGN" in parsed["airports"] or "DAD" in parsed["airports"]))
        needs_weather = parsed["has_weather"] or ("thời tiết" in user_input.lower())
        
        is_multi_step = needs_flight and needs_weather
        
        # TODO 2: Thiết lập vòng lặp while iteration < self.max_iterations
        while iteration < self.max_iterations:
            iteration += 1
            
            if is_multi_step:
                if not called_flight:
                    # Step 1: Call flight tool
                    origin = parsed["airports"][0] if len(parsed["airports"]) > 0 else "HAN"
                    dest = parsed["airports"][1] if len(parsed["airports"]) > 1 else "SGN"
                    action = {
                        "name": "get_flight_info",
                        "args": {"origin": origin, "destination": dest, "max_price": parsed["max_price"]}
                    }
                    thought = f"Cần tìm chuyến bay từ {origin} đi {dest} dưới {parsed['max_price']} VND trước."
                    
                    # TODO 4: Thực thi Tool trong TOOL_MAP
                    tool_fn = TOOL_MAP[action["name"].strip().lower()]
                    flight_result = tool_fn(**action["args"])
                    called_flight = True
                    obs = str(flight_result)
                    
                    self.trace.append({
                        "step": iteration,
                        "thought": thought,
                        "action": action,
                        "observation": obs
                    })
                    continue
                    
                elif not called_weather:
                    # Step 2: Call weather tool
                    city_code = parsed["airports"][1] if len(parsed["airports"]) > 1 else "SGN"
                    action = {
                        "name": "get_weather_forecast",
                        "args": {"city_code": city_code}
                    }
                    thought = f"Tiếp theo cần tra cứu thời tiết tại {city_code}."
                    
                    tool_fn = TOOL_MAP[action["name"].strip().lower()]
                    weather_result = tool_fn(**action["args"])
                    called_weather = True
                    obs = str(weather_result)
                    
                    self.trace.append({
                        "step": iteration,
                        "thought": thought,
                        "action": action,
                        "observation": obs
                    })
                    continue
                    
                else:
                    # Step 3: Combine Final Answer
                    thought = "Đã có đủ dữ liệu chuyến bay và thời tiết. Tạo câu trả lời cuối cùng."
                    flight_str = ", ".join([f"{f['flight_number']} ({f['airline']}, {f['price_vnd']:,} VND)" for f in flight_result]) if flight_result else "Không tìm thấy chuyến bay phù hợp."
                    weather_str = f"Thời tiết tại {weather_result.get('city', 'SGN')} ({weather_result.get('temperature_c')}°C, {weather_result.get('condition')}): {weather_result.get('recommendation')}" if isinstance(weather_result, dict) else str(weather_result)
                    
                    answer = f"Tìm thấy chuyến bay: {flight_str}. Thông tin thời tiết {weather_result.get('city', '')} ({weather_result.get('temperature_c', '')}°C): {weather_str}"
                    
                    self.trace.append({
                        "step": iteration,
                        "thought": thought,
                        "action": "Final Answer",
                        "observation": answer
                    })
                    
                    return {
                        "status": "completed",
                        "iterations": iteration,
                        "answer": answer,
                        "trace": self.trace
                    }
            else:
                # Single-step or FAQ query
                if needs_flight:
                    origin = parsed["airports"][0] if len(parsed["airports"]) > 0 else "HAN"
                    dest = parsed["airports"][1] if len(parsed["airports"]) > 1 else "DAD"
                    action = {
                        "name": "get_flight_info",
                        "args": {"origin": origin, "destination": dest, "max_price": parsed["max_price"]}
                    }
                    thought = f"Tra cứu chuyến bay từ {origin} đến {dest}."
                    tool_fn = TOOL_MAP[action["name"].strip().lower()]
                    flight_result = tool_fn(**action["args"])
                    
                    flight_numbers = [f["flight_number"] for f in flight_result]
                    answer = f"Tìm thấy các chuyến bay từ {origin} đi {dest}: {', '.join(flight_numbers)} (Giá: {flight_result[0]['price_vnd'] if flight_result else 0} VND)."
                    
                    self.trace.append({
                        "step": iteration,
                        "thought": thought,
                        "action": action,
                        "observation": answer
                    })
                    
                    return {
                        "status": "completed",
                        "iterations": iteration,
                        "answer": answer,
                        "trace": self.trace
                    }
                    
                elif needs_weather:
                    city_code = parsed["airports"][0] if len(parsed["airports"]) > 0 else "DAD"
                    action = {
                        "name": "get_weather_forecast",
                        "args": {"city_code": city_code}
                    }
                    thought = f"Tra cứu thời tiết cho {city_code}."
                    tool_fn = TOOL_MAP[action["name"].strip().lower()]
                    weather_result = tool_fn(**action["args"])
                    
                    temp = weather_result.get("temperature_c", "")
                    answer = f"Thời tiết tại {weather_result.get('city', city_code)} hiện tại {temp}°C, {weather_result.get('condition', '')}. Gợi ý: {weather_result.get('recommendation', '')}"
                    
                    self.trace.append({
                        "step": iteration,
                        "thought": thought,
                        "action": action,
                        "observation": answer
                    })
                    
                    return {
                        "status": "completed",
                        "iterations": iteration,
                        "answer": answer,
                        "trace": self.trace
                    }
                else:
                    # FAQ query
                    thought = "Đây là câu hỏi giải đáp thông tin, không cần dùng tool."
                    answer = f"Chính sách đổi trả vé máy bay Vinpearl tuân theo quy định áp dụng của hãng và gói dịch vụ Vinpearl."
                    
                    self.trace.append({
                        "step": iteration,
                        "thought": thought,
                        "action": None,
                        "observation": answer
                    })
                    
                    return {
                        "status": "completed",
                        "iterations": iteration,
                        "answer": answer,
                        "trace": self.trace
                    }
                    
        # Safeguard limit reached
        return {
            "status": "max_iterations_reached",
            "iterations": iteration,
            "answer": "Không thể hoàn thành trong số bước tối đa.",
            "trace": self.trace
        }

def main():
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        
    user_query = "Tìm cho tôi chuyến bay từ HAN đi SGN dưới 2 triệu, rồi cho biết thời tiết SGN nên mặc gì?"
    
    print("=== RUNNING CHATBOT BASELINE ===")
    chatbot = ChatbotBaseline()
    print(chatbot.query(user_query))
    
    print("\n=== RUNNING REACT AGENT ===")
    agent = ReActAgent(max_iterations=5)
    result = agent.run(user_query)
    print("Result:", json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()