import { defineStore } from 'pinia'
import { chatApi } from '@/api/chat'

export const useChatStore = defineStore('chat', {
  state: () => ({
    rooms: [],
    activeRoom: null,
    messages: {},
    unreadCounts: {},
    ws: null,
    connected: false,
    reconnectTimer: null,
    shouldReconnect: false,
    localEchoMessageIds: {},
  }),
  actions: {
    async fetchRooms() {
      const res = await chatApi.rooms()
      this.rooms = res.data || []
      for (const room of this.rooms) {
        this.unreadCounts[room.id] = room.unread_count || 0
      }
    },
    async fetchMessages(roomId, page = 1) {
      const res = await chatApi.messages(roomId, page)
      const results = (res.data?.results || []).slice().reverse()
      if (page === 1) {
        this.messages[roomId] = results
      } else {
        const existing = this.messages[roomId] || []
        this.messages[roomId] = [...results, ...existing]
      }
      return res.data
    },
    async sendMessage(roomId, content) {
      const res = await chatApi.sendMessage(roomId, content)
      if (!this.messages[roomId]) this.messages[roomId] = []
      if (this.messages[roomId].some((msg) => msg.id === res.data.id)) return
      this.messages[roomId].push(res.data)
      if (res.data?.id) {
        this.localEchoMessageIds[res.data.id] = true
      }
      this.updateRoomFromMessage(res.data)
    },
    updateRoomFromMessage(message) {
      const room = this.rooms.find((item) => Number(item.id) === Number(message.room_id))
      if (!room) return
      room.last_message = message.content
      room.last_message_at = message.created_at
      this.unreadCounts[room.id] = (this.unreadCounts[room.id] || 0) + 1
      this.rooms.sort((a, b) => {
        if (!a.last_message_at) return 1
        if (!b.last_message_at) return -1
        return new Date(b.last_message_at) - new Date(a.last_message_at)
      })
    },
    connectWs() {
      if (this.ws && [WebSocket.OPEN, WebSocket.CONNECTING].includes(this.ws.readyState)) return
      this.shouldReconnect = true
      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
      const url = `${protocol}//${location.host}/ws/chat/`
      this.ws = new WebSocket(url)
      this.ws.onopen = () => { this.connected = true }
      this.ws.onclose = () => {
        this.connected = false
        if (this.shouldReconnect) {
          this.reconnectTimer = setTimeout(() => this.connectWs(), 3000)
        }
      }
      this.ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          if (payload.type === 'new_message' && payload.data?.room_id) {
            const message = {
              ...payload.data,
              id: payload.data.id,
            }
            const rid = String(message.room_id)
            if (message.id && this.localEchoMessageIds[message.id]) {
              delete this.localEchoMessageIds[message.id]
              return
            }
            if (!this.messages[rid]) this.messages[rid] = []
            if (this.messages[rid].some((msg) => msg.id === message.id)) return
            this.messages[rid].push(message)
            this.updateRoomFromMessage(message)
          }
        } catch { /* ignore */ }
      }
    },
    disconnectWs() {
      this.shouldReconnect = false
      if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
      if (this.ws) { this.ws.close(); this.ws = null }
      this.connected = false
    },
  },
})
