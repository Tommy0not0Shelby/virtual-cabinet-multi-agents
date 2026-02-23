import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const supabaseUrl = Deno.env.get('SUPABASE_URL')!
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

const supabase = createClient(supabaseUrl, supabaseServiceKey)

serve(async (req) => {
    // Only accept POST requests
    if (req.method !== 'POST') {
        return new Response('Method Not Allowed', { status: 405 })
    }

    try {
        const payload = await req.json()

        // 1. 验证挑战码 (Challenge)
        if (payload.challenge && payload.type === 'url_verification') {
            return new Response(JSON.stringify({ challenge: payload.challenge }), {
                headers: { 'Content-Type': 'application/json' },
            })
        }

        // 2. 忽略不需要的事件或消息类型
        if (!payload.event) {
            return new Response(JSON.stringify({ status: 'ignored', msg: 'No event found' }), {
                headers: { 'Content-Type': 'application/json' },
            })
        }

        const event = payload.event
        const message = event.message || {}
        const sender = event.sender || {}

        // 我们在这个 Demo 里只处理文本消息
        if (message.message_type !== 'text') {
            return new Response(JSON.stringify({ status: 'ignored', msg: 'Not a text message' }), {
                headers: { 'Content-Type': 'application/json' },
            })
        }

        let user_message = ''
        try {
            // 提取文字内容
            const content = JSON.parse(message.content || '{}')
            user_message = content.text || ''
        } catch (e) {
            user_message = message.content || ''
        }

        const sender_id = sender.sender_id?.open_id || 'default_boss'
        const message_id = message.message_id || `msg_${Date.now()}`

        if (!user_message.trim()) {
            return new Response(JSON.stringify({ status: 'ignored', msg: 'Empty message' }), {
                headers: { 'Content-Type': 'application/json' },
            })
        }

        // 3. 将消息存入 Supabase feishu_messages 供 Worker 处理
        const { error } = await supabase
            .from('feishu_messages')
            .insert({
                message_id: message_id,
                content: user_message,
                sender_id: sender_id,
                status: 'pending'
            })

        if (error) {
            console.error('Error inserting into Supabase:', error)
            return new Response(JSON.stringify({ error: error.message }), { status: 500 })
        }

        return new Response(JSON.stringify({ status: 'success', msg: 'Message received and stored' }), {
            headers: { 'Content-Type': 'application/json' },
        })

    } catch (error) {
        console.error('Server error:', error.message)
        return new Response(JSON.stringify({ error: 'Invalid Request' }), { status: 400 })
    }
})
