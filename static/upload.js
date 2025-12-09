// =============================
//   FILE UPLOAD HANDLER
// =============================

document.addEventListener("DOMContentLoaded", () => {
    const fileInput = document.getElementById("file-input");

    if (!fileInput) {
        console.error("File input not found in DOM");
        return;
    }

    fileInput.addEventListener("change", async () => {
        const file = fileInput.files[0];
        if (!file) return;

        // Display file name in chat window
        const messages = document.getElementById("messages");
        const msg = document.createElement("div");
        msg.classList.add("message", "msg-user");
        msg.innerHTML = `📎 <b>Uploaded:</b> ${file.name}`;
        messages.appendChild(msg);
        messages.scrollTop = messages.scrollHeight;

        // Upload to backend
        if (typeof currentChatId === "undefined" || !currentChatId) {
            alert("Open or start a chat before uploading!");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch(`/upload/${currentChatId}`, {
                method: "POST",
                body: formData
            });

            const data = await res.json();
            console.log("UPLOAD RESPONSE:", data);

        } catch (err) {
            console.error("UPLOAD FAILED:", err);
        }
    });
});
