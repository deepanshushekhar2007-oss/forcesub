import express from "express"
import makeWASocket, {
  useMultiFileAuthState,
  DisconnectReason
} from "@whiskeysockets/baileys"
import TelegramBot from "node-telegram-bot-api"
import path from "path"
import fs from "fs"

const app = express()
const PORT = process.env.PORT || 3000
const bot = new TelegramBot(process.env.TG_TOKEN, { polling: true })

let sessions = {}
let intervalTime = 30000
let chatInterval = null

// ✅ Number Cleaner (Supports All Countries)
function cleanNumber(number) {
  return number.replace(/[^0-9]/g, "")
}

async function connectAccount(chatId, accountName, rawNumber) {

  const number = cleanNumber(rawNumber)

  if (number.length < 8) {
    return bot.sendMessage(chatId, "❌ Invalid Number Format")
  }

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

    if (connection === "connecting") {
      try {
        const code = await sock.requestPairingCode(number)
        bot.sendMessage(chatId,
          `🔐 Pairing Code for ${accountName}:\n\n${code}\n\nGo to WhatsApp → Linked Devices → Link with phone number instead`
        )
      } catch (err) {
        bot.sendMessage(chatId, "❌ Failed to generate pairing code")
        console.log("Pairing Error:", err)
      }
    }

    if (connection === "open") {
      bot.sendMessage(chatId, `✅ ${accountName} Connected Successfully`)
    }

    if (connection === "close") {
      if (lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut) {
        connectAccount(chatId, accountName, number)
      } else {
        bot.sendMessage(chatId, `⚠ ${accountName} Logged Out`)
      }
    }
  })
}

//
// ✅ START COMMAND (Full Guide)
//
bot.onText(/\/start/, (msg) => {

  bot.sendMessage(msg.chat.id, `
🤖 *WhatsApp Auto Chat Bot*

📌 How To Use:

1️⃣ Connect First Account
/connect1
Then:
/number1 1234567890

2️⃣ Connect Second Account
/connect2
Then:
/number2 1234567890

🌍 Works For All Countries
(With Country Code – No + needed)

3️⃣ Set Time Interval
/settime 30

4️⃣ Start Auto Chat
/startchat

5️⃣ Stop Chat
/stopchat

⚠ Keep interval 20+ seconds for safety.
`, { parse_mode: "Markdown" })

})

//
// CONNECT COMMANDS
//
bot.onText(/\/connect1/, (msg) => {
  bot.sendMessage(msg.chat.id, "Send number like:\n/number1 1234567890")
})

bot.onText(/\/connect2/, (msg) => {
  bot.sendMessage(msg.chat.id, "Send number like:\n/number2 1234567890")
})

bot.onText(/\/number1 (.+)/, (msg, match) => {
  connectAccount(msg.chat.id, "account1", match[1])
})

bot.onText(/\/number2 (.+)/, (msg, match) => {
  connectAccount(msg.chat.id, "account2", match[1])
})

//
// SET TIME
//
bot.onText(/\/settime (.+)/, (msg, match) => {
  const seconds = parseInt(match[1])
  if (isNaN(seconds) || seconds < 10)
    return bot.sendMessage(msg.chat.id, "❌ Minimum 10 seconds required")

  intervalTime = seconds * 1000
  bot.sendMessage(msg.chat.id, `⏱ Time set to ${seconds} seconds`)
})

//
// AUTO CHAT
//
bot.onText(/\/startchat/, async (msg) => {

  const sock1 = sessions["account1"]
  const sock2 = sessions["account2"]

  if (!sock1 || !sock2) {
    return bot.sendMessage(msg.chat.id, "❌ Connect both accounts first")
  }

  if (chatInterval) clearInterval(chatInterval)

  chatInterval = setInterval(async () => {
    try {
      await sock1.sendMessage(sock2.user.id, { text: "Hello 👋" })
      await sock2.sendMessage(sock1.user.id, { text: "Hi there 😎" })
    } catch (err) {
      console.log("Chat Error:", err)
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

//
// SERVER
//
app.get("/", (req, res) => {
  res.send("Bot Running")
})

app.listen(PORT, () => console.log("Server Started"))
