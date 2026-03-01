import express from "express"
import makeWASocket, { 
  useMultiFileAuthState, 
  DisconnectReason 
} from "@whiskeysockets/baileys"
import TelegramBot from "node-telegram-bot-api"
import fs from "fs"

const app = express()
const PORT = process.env.PORT || 3000
const bot = new TelegramBot(process.env.TG_TOKEN, { polling: true })

let sessions = {}
let intervalTime = 30000
let chatInterval = null

async function connectAccount(chatId, accountName, number) {

  const sessionPath = `./sessions/${chatId}_${accountName}`

  const { state, saveCreds } = await useMultiFileAuthState(sessionPath)

  const sock = makeWASocket({
    auth: state,
    printQRInTerminal: false
  })

  sessions[accountName] = sock

  sock.ev.on("creds.update", saveCreds)

  sock.ev.on("connection.update", async (update) => {

    const { connection, lastDisconnect } = update

    if (connection === "open") {
      bot.sendMessage(chatId, `✅ ${accountName} Connected Successfully`)
    }

    if (connection === "close") {
      if (lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut) {
        connectAccount(chatId, accountName, number)
      }
    }
  })

  if (!sock.authState?.creds?.registered) {
    const code = await sock.requestPairingCode(number)
    bot.sendMessage(chatId, `🔐 Pairing Code for ${accountName}:\n\n${code}\n\nEnter this inside WhatsApp > Linked Devices`)
  }
}

bot.onText(/\/connect1/, (msg) => {
  bot.sendMessage(msg.chat.id, "Send number for Account1 like:\n/number1 91XXXXXXXXXX")
})

bot.onText(/\/connect2/, (msg) => {
  bot.sendMessage(msg.chat.id, "Send number for Account2 like:\n/number2 91XXXXXXXXXX")
})

bot.onText(/\/number1 (.+)/, (msg, match) => {
  const number = match[1]
  connectAccount(msg.chat.id, "account1", number)
})

bot.onText(/\/number2 (.+)/, (msg, match) => {
  const number = match[1]
  connectAccount(msg.chat.id, "account2", number)
})

bot.onText(/\/settime (.+)/, (msg, match) => {
  const seconds = parseInt(match[1])
  if (isNaN(seconds)) return bot.sendMessage(msg.chat.id, "Invalid time")

  intervalTime = seconds * 1000
  bot.sendMessage(msg.chat.id, `⏱ Time set to ${seconds} seconds`)
})

bot.onText(/\/startchat/, async (msg) => {

  const sock1 = sessions["account1"]
  const sock2 = sessions["account2"]

  if (!sock1 || !sock2) {
    return bot.sendMessage(msg.chat.id, "Connect both accounts first")
  }

  if (chatInterval) clearInterval(chatInterval)

  chatInterval = setInterval(async () => {
    try {
      await sock1.sendMessage(sock2.user.id, { text: "Hello from Account 1" })
      await sock2.sendMessage(sock1.user.id, { text: "Reply from Account 2" })
    } catch (err) {
      console.log(err)
    }
  }, intervalTime)

  bot.sendMessage(msg.chat.id, "🔥 Auto Chat Started")
})

bot.onText(/\/stopchat/, (msg) => {
  if (chatInterval) {
    clearInterval(chatInterval)
    chatInterval = null
  }
  bot.sendMessage(msg.chat.id, "🛑 Auto Chat Stopped")
})

app.get("/", (req, res) => {
  res.send("Bot Running")
})

app.listen(PORT, () => console.log("Server Started"))
