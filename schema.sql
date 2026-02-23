-- schema.sql
-- Create the feishu_messages table to store incoming webhook events

CREATE TABLE IF NOT EXISTS public.feishu_messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    message_id TEXT UNIQUE NOT NULL,    -- 飞书消息唯一 ID, 防止重复处理
    content TEXT NOT NULL,              -- 解析后的用户文本内容
    sender_id TEXT NOT NULL,            -- 发送方用户 ID (open_id)
    status TEXT DEFAULT 'pending' NOT NULL, -- 状态: pending, processing, completed, error
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Setup an index on status for faster polling
CREATE INDEX IF NOT EXISTS idx_feishu_messages_status ON public.feishu_messages(status);
