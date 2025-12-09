// Elements
const chatsEl = document.getElementById("chat-list");
const newChatBtn = document.getElementById("new-chat-btn");
const messagesEl = document.getElementById("messages");
const titleEl = document.getElementById("current-title");
const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const themeSelect = document.getElementById("theme-select");

let currentChatId = null;
let sse = null;

// helpers
function appendUser(text){
  const div = document.createElement("div");
  div.className = "message msg-user";
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}
function appendBotMarkdown(md){
  const div = document.createElement("div");
  div.className = "message msg-bot";
  div.innerHTML = marked.parse(md || "");
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}
function appendTyping(){
  removeTyping();
  const el = document.createElement("div");
  el.className = "message msg-bot typing";
  el.id = "typing";
  el.innerHTML = "<em>▮▮▮ thinking…</em>";
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}
function removeTyping(){
  const t = document.getElementById("typing");
  if (t) t.remove();
}

// open a chat and load messages
async function openChat(id){
  if (sse) { sse.close(); sse = null; }
  currentChatId = id;
  const res = await fetch(`/chats/${id}/messages`);
  if (!res.ok) return;
  const j = await res.json();
  titleEl.textContent = j.title || "Chat";
  messagesEl.innerHTML = "";
  for (const m of j.messages){
    if (m.role === "user") appendUser(m.content);
    else appendBotMarkdown(m.content);
  }
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// create new chat
newChatBtn?.addEventListener("click", async ()=>{
  const res = await fetch("/chats", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({title:"New Chat"})});
  const j = await res.json();
  if (j.ok) location.reload();
});

// sidebar actions (open/rename/delete)
document.addEventListener("click", async (ev)=>{
  const chatItem = ev.target.closest(".chat-item");
  if (chatItem){
    openChat(chatItem.dataset.id);
    return;
  }
  if (ev.target.matches(".rename-btn")){
    ev.stopPropagation();
    const id = ev.target.dataset.id;
    const t = prompt("Rename chat:");
    if (t !== null) {
      await fetch(`/chats/${id}/rename`, {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({title:t})});
      location.reload();
    }
    return;
  }
  if (ev.target.matches(".delete-btn")){
    ev.stopPropagation();
    const id = ev.target.dataset.id;
    if (!confirm("Delete this chat?")) return;
    await fetch(`/chats/${id}`, {method:"DELETE"});
    location.reload();
    return;
  }
});

// theme toggle - POST to profile on change (quick local save)
themeSelect?.addEventListener("change", async ()=>{
  const val = themeSelect.value;
  document.body.className = val;
  try {
    await fetch("/profile", {method:"POST", body: new URLSearchParams({display_name: document.querySelector(".greet strong")?.textContent || "", theme: val})});
  } catch(e){ console.warn("theme save failed", e) }
});

// auto-resize textarea
input?.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = (input.scrollHeight) + "px";
});

// send message and stream
form?.addEventListener("submit", async (e)=>{
  e.preventDefault();
  const text = input.value.trim();
  if (!text || !currentChatId) return;
  appendUser(text);
  input.value = "";
  appendTyping();

  // open SSE to stream
  if (sse) { sse.close(); sse = null; }
  sse = new EventSource(`/chats/${currentChatId}/send`);

  let acc = "";
  let partialDiv = null;
  let streamFailed = false;

  sse.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data);
      if (data.chunk) {
        acc += data.chunk;
        removeTyping();
        if (!partialDiv) {
          partialDiv = document.createElement("div");
          partialDiv.className = "message msg-bot partial";
          messagesEl.appendChild(partialDiv);
        }
        partialDiv.innerHTML = marked.parse(acc);
        messagesEl.scrollTop = messagesEl.scrollHeight;
      } else if (data.done) {
        removeTyping();
        if (partialDiv) {
          partialDiv.classList.remove("partial");
          partialDiv.innerHTML = marked.parse(data.full || acc);
        } else {
          appendBotMarkdown(data.full || acc);
        }
        sse.close();
      }
    } catch (err) {
      console.error("sse parse", err);
    }
  };

  sse.addEventListener("stream_error", async (ev) => {
    // backend signaled streaming failure -> close and fallback to static
    streamFailed = true;
    sse.close();
    removeTyping();
    if (partialDiv) partialDiv.remove();
    // fallback to static endpoint
    try {
      const r = await fetch(`/chats/${currentChatId}/chat`, {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({message:text})});
      if (r.ok) {
        const j = await r.json();
        appendBotMarkdown(j.reply || "No reply");
      } else {
        appendBotMarkdown("**Error**: static fallback failed");
      }
    } catch (e) {
      appendBotMarkdown("**Error**: network/static fallback failed");
    }
  });

  sse.onerror = (err) => {
    // network error - close and fallback silently
    if (!streamFailed) {
      removeTyping();
      if (partialDiv) partialDiv.remove();
      // do static fallback
      (async () => {
        try {
          const r = await fetch(`/chats/${currentChatId}/chat`, {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({message:text})});
          if (r.ok) {
            const j = await r.json();
            appendBotMarkdown(j.reply || "No reply");
          } else {
            appendBotMarkdown("**Error**: static fallback failed");
          }
        } catch (e) {
          appendBotMarkdown("**Error**: network/static fallback failed");
        }
      })();
    }
    if (sse) { sse.close(); sse = null; }
  };
});

// -------- FILE UPLOAD HANDLER -------- //
const fileInput = document.getElementById("file-input");

if (fileInput) {
    fileInput.addEventListener("change", async () => {
        const file = fileInput.files[0];
        if (!file) return;

        // Show file in chat UI
        const messages = document.getElementById("messages");
        const div = document.createElement("div");
        div.classList.add("message", "msg-user");
        div.innerHTML = `📎 <b>Uploaded:</b> ${file.name}`;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;

        // Upload to backend
        const formData = new FormData();
        formData.append("file", file);

        if (!currentChatId) {
            alert("Open or create a chat first!");
            return;
        }

        const res = await fetch(`/upload/${currentChatId}`, {
            method: "POST",
            body: formData
        });

        const data = await res.json();
        console.log("UPLOAD RESPONSE:", data);
    });
}

// load initial chat if available
window.addEventListener("DOMContentLoaded", () => {
  const first = document.querySelector(".chat-item");
  if (first) {
    openChat(first.dataset.id);
  }
});
