import os
import json
import time
import asyncio
from supabase import create_client, Client
import httpx

from agent_manager import CabinetManager

# 1. 飞书发送函数的实现 (用于将卡片发给用户)
async def send_feishu_card(user_id: str, card_blocks: list, coach_message: str):
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    
    if not app_id or not app_secret:
        print("警告: 缺少 FEISHU_APP_ID 或 FEISHU_APP_SECRET，无法真正发送飞书消息。")
        return

    # a. 获取 tenant_access_token
    token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    req_body = {"app_id": app_id, "app_secret": app_secret}
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(token_url, json=req_body)
            resp.raise_for_status()
            access_token = resp.json().get("tenant_access_token")
        except Exception as e:
            print(f"获取飞书 Token 失败: {e}")
            return

        if not access_token:
            return

        # b. 组装卡片 JSON (简化)
        # 实际开发中可以根据 agent_manager 的 Button 构建互动卡片，或者是 markdown 文本
        card_content = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "内阁总管回复"}
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": coach_message
                }
            ]
        }
        
        # 将按钮追加为 Action
        if card_blocks:
            action_element = {
                "tag": "action",
                "actions": []
            }
            for btn in card_blocks:
                button_type = "primary" if btn.recommended else "default"
                action_element["actions"].append({
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": btn.text},
                    "type": button_type,
                    "value": {"payload": btn.action_payload}
                })
            card_content["elements"].append(action_element)

        # c. 发送消息
        send_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "receive_id": user_id,
            "msg_type": "interactive",
            "content": json.dumps(card_content)
        }
        
        try:
            send_resp = await client.post(send_url, headers=headers, json=payload)
            send_resp.raise_for_status()
            print(f"✅ 已成功回复飞书用户 {user_id}")
        except Exception as e:
            print(f"发送飞书失败: {e}")

# 2. Worker 轮询与处理逻辑
async def process_pending_messages():
    # 初始化 Supabase
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # 用 service role 以免受 RLS 限制
    
    if not supabase_url or not supabase_key:
        print("🔴 缺少 Supabase 环境变量 (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)")
        return
        
    supabase: Client = create_client(supabase_url, supabase_key)
    manager = CabinetManager()

    print("🚀 启动 Supabase Worker，正在轮询 feishu_messages...")
    
    while True:
        try:
            # 1. 查找待处理记录
            # 使用 limit(1) 保证一次处理一条，也可以用 in_ 代替
            response = supabase.table("feishu_messages").select("*").eq("status", "pending").order("created_at").limit(1).execute()
            data = response.data
            
            if data and len(data) > 0:
                record = data[0]
                record_id = record["id"]
                user_message = record["content"]
                user_id = record["sender_id"]
                
                print(f"\n🔔 检测到新消息 [{record_id}] 来自 {user_id}: {user_message}")
                
                # 2. 锁定记录为 processing
                supabase.table("feishu_messages").update({"status": "processing"}).eq("id", record_id).execute()
                
                # 3. 处理消息 (调用 CabinetManager)
                agent_response = await manager.process_message(user_message, user_id)
                
                if agent_response:
                    # 获取卡片所需数据
                    coach_message = agent_response.front_end.coach_message
                    buttons = agent_response.front_end.buttons
                    
                    # 打印日志
                    print("========== 拟返回飞书卡片 (Worker) ==========")
                    print(f"💬 教练留言: \n{coach_message}\n")
                    for btn in buttons:
                        icon = "🔴" if btn.recommended else "⚪"
                        print(f"  {icon} [{btn.text}] (Payload: {btn.action_payload})")
                    
                    # 4. 如果有 notion 动作，执行同步动作
                    await manager.execute_actions(agent_response.actions)
                    
                    # 5. 回复飞书用户
                    await send_feishu_card(user_id, buttons, coach_message)
                    
                    # 6. 更新状态为 completed
                    supabase.table("feishu_messages").update({"status": "completed"}).eq("id", record_id).execute()
                else:
                    print("❌ Router 返回为空，标记为 error")
                    supabase.table("feishu_messages").update({"status": "error"}).eq("id", record_id).execute()
            else:
                # 没消息时稍微休眠
                await asyncio.sleep(2)
                
        except Exception as e:
            print(f"Worker 轮询发生异常: {e}")
            await asyncio.sleep(5) # 出错后退让

if __name__ == "__main__":
    try:
        asyncio.run(process_pending_messages())
    except KeyboardInterrupt:
        print("Worker 已停止。")
