import json
import asyncio
from fastapi import FastAPI, Request
from agent_manager import CabinetManager

app = FastAPI(title="Cabinet Agent Feishu Webhook", description="多智能体虚拟内阁飞书消息接收端 (支持 Async/Memory/Tools)")
manager = CabinetManager()

@app.post("/webhook/feishu")
async def feishu_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception as e:
        return {"error": "Invalid JSON format"}
        
    if "challenge" in payload and payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}
        
    # 提取 User ID (飞书 open_id)
    user_id = "default_boss"
    user_message = ""
    
    # -------------------------------------------------------------------
    # 解析飞书消息逻辑
    # -------------------------------------------------------------------
    # 飞书事件会包在 event.message.content 里，且 content 里是个序列化的 JSON
    if "event" in payload:
        event = payload.get("event", {})
        
        # 尝试提取飞书实际用户发送者 ID 作为 Memory 隔离依据
        sender = event.get("sender", {}).get("sender_id", {})
        user_id = sender.get("open_id", "default_boss")
        
        msg_type = event.get("message", {}).get("message_type")
        if msg_type == "text":
            content_str = event.get("message", {}).get("content", "{}")
            try:
                content_dict = json.loads(content_str)
                user_message = content_dict.get("text", "")
            except:
                user_message = content_str
    elif "message" in payload: 
        # 兼容简化的 CURL 测试结构：{"message": {"text": "..."}}
        user_message = payload.get("message", {}).get("text", "")
        # 支持从 curl 中传 user_id 用于测试内存隔离
        if "user_id" in payload:
            user_id = payload.get("user_id")
        
    if not user_message:
        return {"status": "success", "msg": "No text message found or ignored."}
        
    print(f"\n[陛下密诏 ({user_id})]: {user_message}")
    
    # 因为 process_message 已改为 async，所以必须 await
    agent_response = await manager.process_message(user_message, user_id)
    if not agent_response:
        return {"status": "error", "msg": "Router returned nothing."}
        
    # 执行同步动作（未来也可将 Notion 库重构为 aiohttp 异步）
    await manager.execute_actions(agent_response.actions)
    
    print("\n========== 拟返回飞书卡片 ==========")
    print(f"💬 教练留言: \n{agent_response.front_end.coach_message}\n")
    print("🔘 交互按钮:")
    for btn in agent_response.front_end.buttons:
        icon = "🔴" if btn.recommended else "⚪"
        print(f"  {icon} [{btn.text}] (Payload: {btn.action_payload})")
    print("===================================\n")
    
    return {"status": "success", "msg": "Processed completely."}

if __name__ == "__main__":
    import uvicorn
    # 测试命令: curl -X POST http://127.0.0.1:8000/webhook/feishu -H "Content-Type: application/json" -d '{"message": {"text": "请查一下今年的最新科技新闻"}, "user_id": "test_user_01"}'
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
