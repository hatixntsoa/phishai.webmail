// ———————————————————————————————
// GLOBALS
// ———————————————————————————————
let currentEmails = [];
let emails = { inbox: [], sent: [], trash: [], phishing: [] };
let lastEmailCount = { inbox: 0, sent: 0 };

// ———————————————————————————————
// DOM IS READY
// ———————————————————————————————
document.addEventListener('DOMContentLoaded', function () {
    const emailList = document.querySelector('.email-list');
    const emailListBody = document.querySelector('.email-list-body');
    const emailListHeader = document.querySelector('.email-list-header');
    const folderNameEl = document.querySelector('.email-list-header .folder-name');
    const emailCountEl = document.querySelector('.email-list-header .email-count');

    const emailPreviewContainer = document.querySelector('.email-preview-container');
    const backButton = document.querySelector('.header .back-button');
    const sidebarLinks = document.querySelectorAll('.sidebar-menu a');
    const settingsBtn = document.getElementById('settings-btn');
    const settingsView = document.querySelector('.settings-view');
    const themeToggler = document.getElementById('theme-toggler');
    const newMessageBtn = document.querySelector('.new-message .btn');
    const composeBackdrop = document.querySelector('.compose-backdrop');
    const composeWindow = document.querySelector('.compose-window');
    const closeComposeBtn = document.querySelector('.close-compose-btn');
    const activeIndicator = document.querySelector('.active-indicator');

    // Compose inputs
    const toInput = composeWindow.querySelector('input[placeholder="To"]');
    const subjectInput = composeWindow.querySelector('input[placeholder="Subject"]');
    const bodyTextarea = composeWindow.querySelector('textarea');
    const sendBtn = composeWindow.querySelector('.btn-primary');

    // Load initial inbox
    currentEmails = Array.isArray(window.REAL_EMAILS) ? window.REAL_EMAILS : [];
    emails.inbox = currentEmails;
    lastEmailCount.inbox = currentEmails.length;

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    function formatSmartDate(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        if (isNaN(date)) return dateStr.split(',')[0] || '';
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        const msgDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());

        if (msgDate.getTime() === today.getTime()) {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
        if (msgDate.getTime() === yesterday.getTime()) return 'Yesterday';
        if (date.getFullYear() === now.getFullYear()) {
            return date.toLocaleDateString([], { day: 'numeric', month: 'short' });
        }
        return date.toLocaleDateString([], { day: '2-digit', month: '2-digit', year: 'numeric' });
    }

    // ———————————————————————————————
    // RENDER EMAIL LIST
    // ———————————————————————————————
    window.renderEmailList = function (folder = 'inbox') {
        const data = emails[folder] || [];

        // Update sticky header (never destroyed)
        folderNameEl.textContent = folder.charAt(0).toUpperCase() + folder.slice(1);
        emailCountEl.textContent = data.length;

        // Clear only the scrollable body
        emailListBody.innerHTML = '';

        if (data.length === 0) {
            emailListBody.innerHTML = `<p style="text-align:center;padding:60px;color:#888;">No messages in ${folder.charAt(0).toUpperCase() + folder.slice(1)}</p>`;
            return;
        }

        data.forEach(email => {
            const item = document.createElement('div');
            item.classList.add('email-item');
            if (!email.read) item.classList.add('unread');

            const initial = (email.sender || '?').charAt(0).toUpperCase();
            item.innerHTML = `
                <div class="email-sender-initial">${initial}</div>
                <div class="email-sender">${escapeHtml(email.sender || 'Unknown')}</div>
                <div class="email-subject">${escapeHtml(email.subject || '(no subject)')}</div>
                <div class="email-date">${formatSmartDate(email.date)}</div>
                <div class="email-actions">
                    <i class="material-icons-outlined">reply</i>
                    <i class="material-icons-outlined">archive</i>
                    <i class="material-icons-outlined">delete</i>
                </div>
            `;

            item.addEventListener('click', e => {
                const actionIcon = e.target.closest('.email-actions i');
                if (actionIcon) {
                    e.stopPropagation();
                    const iconName = actionIcon.textContent.trim();
                    const emailId = email.id;

                    if (iconName === 'delete') {
                        if (!confirm("Move this message to Trash?")) return;
                        fetch('/action', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ id: emailId, action: 'trash' })
                        }).then(() => {
                            item.style.transition = 'opacity 0.3s';
                            item.style.opacity = '0';
                            setTimeout(() => item.remove(), 300);
                            // Update count live
                            emailCountEl.textContent = --data.length;
                        });
                    }
                    if (iconName === 'archive') {
                        fetch('/action', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ id: emailId, action: 'archive' })
                        }).then(() => {
                            item.style.transition = 'opacity 0.3s';
                            item.style.opacity = '0';
                            setTimeout(() => item.remove(), 300);
                            emailCountEl.textContent = --data.length;
                        });
                    }
                    return;
                }
                showEmail(email);
            });

            emailListBody.appendChild(item);
        });
    };

    function showEmail(email) {
        email.read = true;
        const currentFolder = document.querySelector('.sidebar-menu li.active span')?.textContent.toLowerCase() || 'inbox';
        window.renderEmailList(currentFolder);

        emailList.style.display = 'none';
        emailPreviewContainer.style.display = 'flex';
        backButton.style.display = 'block';
        document.querySelector('.search-bar').style.display = 'none';

        document.querySelector('.email-preview-container .email-subject').textContent = email.subject || '(no subject)';
        document.querySelector('.email-preview-container .email-sender').textContent = `From: ${email.sender || 'Unknown'}`;
        document.querySelector('.email-content-body').textContent = email.body || '(No content)';
    }

    function goBack() {
        emailList.style.display = 'flex';
        emailPreviewContainer.style.display = 'none';
        settingsView.style.display = 'none';
        backButton.style.display = 'none';
        document.querySelector('.search-bar').style.display = 'flex';
    }

    function moveIndicator(li) {
        if (!li) return;
        activeIndicator.style.top = `${li.offsetTop}px`;
        activeIndicator.style.height = `${li.offsetHeight}px`;
    }

    // ———————————————————————————————
    // SEND EMAIL
    // ———————————————————————————————
    sendBtn.onclick = async function () {
        const to = toInput.value.trim();
        const subject = subjectInput.value.trim();
        const body = bodyTextarea.value.trim();
        if (!to || !subject || !body) {
            alert("Please fill in all fields");
            return;
        }
        sendBtn.disabled = true;
        sendBtn.textContent = "Sending...";
        try {
            const res = await fetch('/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({ to_addr: to, subject, body })
            });
            if (res.ok) {
                hideCompose();
                const sentLink = Array.from(sidebarLinks).find(l =>
                    l.querySelector('span')?.textContent.toLowerCase() === 'sent'
                );
                if (sentLink) sentLink.click();
            } else {
                alert("Failed to send");
            }
        } catch (err) {
            alert("Network error");
        } finally {
            sendBtn.disabled = false;
            sendBtn.textContent = "Send";
        }
    };

    const showCompose = () => {
        composeBackdrop.style.display = 'block';
        composeWindow.style.display = 'flex';
        toInput.focus();
    };
    const hideCompose = () => {
        composeBackdrop.style.display = 'none';
        composeWindow.style.display = 'none';
        toInput.value = subjectInput.value = bodyTextarea.value = '';
    };

    newMessageBtn.onclick = showCompose;
    closeComposeBtn.onclick = hideCompose;
    composeBackdrop.onclick = hideCompose;
    backButton.addEventListener('click', goBack);

    // ———————————————————————————————
    // SIDEBAR NAVIGATION
    // ———————————————————————————————
    sidebarLinks.forEach(link => {
        link.addEventListener('click', e => {
            e.preventDefault();
            document.querySelectorAll('.sidebar-menu li').forEach(l => l.classList.remove('active'));
            const li = link.parentElement;
            li.classList.add('active');
            moveIndicator(li);

            const folder = link.querySelector('span').textContent.toLowerCase();

            if (folder === 'inbox') {
                fetch('/api/emails?folder=inbox')
                    .then(r => r.json())
                    .then(data => {
                        emails.inbox = data;
                        window.renderEmailList('inbox');
                    });
            } else if (folder === 'sent') {
                fetch('/api/emails?folder=sent')
                    .then(r => r.json())
                    .then(data => {
                        emails.sent = data;
                        window.renderEmailList('sent');
                    });
            } else if (folder === 'trash') {
                fetch('/api/emails?folder=trash')
                    .then(r => r.json())
                    .then(data => {
                        emails.trash = data;
                        window.renderEmailList('trash');
                    });
            } else if (folder === 'phishing') {
                fetch('/api/emails?folder=phishing')
                    .then(r => r.json())
                    .then(data => {
                        emails.phishing = data;
                        window.renderEmailList('phishing');
                    });
            } else {
                emailListBody.innerHTML = `<p style="text-align:center;padding:60px;color:#888;">${folder.charAt(0).toUpperCase() + folder.slice(1)} coming soon...</p>`;
            }
            goBack();
        });
    });

    settingsBtn.onclick = () => {
        emailList.style.display = 'none';
        emailPreviewContainer.style.display = 'none';
        settingsView.style.display = 'block';
        backButton.style.display = 'block';
        document.querySelector('.search-bar').style.display = 'none';
    };

    themeToggler.onchange = () => document.body.classList.toggle('dark-mode');

    // Draggable compose window
    let dragging = false, ox, oy;
    document.querySelector('.compose-header').onmousedown = e => {
        dragging = true;
        ox = e.clientX - composeWindow.offsetLeft;
        oy = e.clientY - composeWindow.offsetTop;
    };
    document.onmousemove = e => {
        if (dragging) {
            composeWindow.style.left = (e.clientX - ox) + 'px';
            composeWindow.style.top = (e.clientY - oy) + 'px';
        }
    };
    document.onmouseup = () => dragging = false;

    // ———————————————————————————————
    // INITIAL RENDER + REAL-TIME UPDATES
    // ———————————————————————————————
    window.renderEmailList('inbox');
    moveIndicator(document.querySelector('.sidebar-menu li.active'));

    const evtSource = new EventSource("/stream");
    evtSource.addEventListener("inbox", e => {
        try {
            const data = JSON.parse(e.data);
            emails.inbox = data;
            if (document.querySelector('.sidebar-menu li.active span')?.textContent.toLowerCase() === 'inbox') {
                window.renderEmailList('inbox');
            }
        } catch (err) {}
    });
    evtSource.addEventListener("sent", e => {
        try {
            const data = JSON.parse(e.data);
            emails.sent = data;
            if (document.querySelector('.sidebar-menu li.active span')?.textContent.toLowerCase() === 'sent') {
                window.renderEmailList('sent');
            }
        } catch (err) {}
    });
    evtSource.addEventListener("trash", e => {
        try {
            const data = JSON.parse(e.data);
            emails.trash = data;
            if (document.querySelector('.sidebar-menu li.active span')?.textContent.toLowerCase() === 'trash') {
                window.renderEmailList('trash');
            }
        } catch (err) {}
    });
    evtSource.addEventListener("phishing", e => {
        try {
            const data = JSON.parse(e.data);
            emails.phishing = data;
            if (document.querySelector('.sidebar-menu li.active span')?.textContent.toLowerCase() === 'phishing') {
                window.renderEmailList('phishing');
            }
        } catch (err) {}
    });
    evtSource.addEventListener("switch_to_phishing", () => {
        const phishingLink = Array.from(sidebarLinks).find(l =>
            l.querySelector('span')?.textContent.toLowerCase() === 'phishing'
        );
        if (phishingLink) phishingLink.click();
    });

    evtSource.addEventListener("phishing_alert", e => {
        const a = JSON.parse(e.data);

        // Remove any existing banner
        document.getElementById("phish-banner")?.remove();

        const banner = document.createElement("div");
        banner.id = "phish-banner";

        // Build bullet points
        const reasonItems = a.reasons.map(r => 
            `<li style="margin: 6px 0; padding-left: 4px;">• ${escapeHtml(r)}</li>`
        ).join("");

        banner.innerHTML = `
            <div style="max-width: 700px; margin: 0 auto; text-align: left; line-height: 1.5;">
                <div style="display: flex; align-items: center; gap: 10px; font-size: 19px; font-weight: bold; margin-bottom: 8px;">
                    <span style="font-size: 28px;">Phishing Email Blocked</span>
                    <span style="background: #ff1744; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">
                        ${a.confidence} Confidence
                    </span>
                </div>
                <div style="opacity: 0.95; margin-bottom: 8px;">
                    From: <strong>${escapeHtml(a.sender)}</strong> &lt;${escapeHtml(a.sender_email)}&gt;
                </div>
                <div style="font-style: italic; opacity: 0.9; margin-bottom: 14px; color: #ffcccc;">
                    “${escapeHtml(a.subject)}”
                </div>
                <div style="background: rgba(255,255,255,0.12); border-left: 4px solid #ff1744; padding: 12px; border-radius: 0 6px 6px 0; font-size: 14px;">
                    <strong>Why PhishAI blocked this email:</strong>
                    <ul style="margin: 10px 0 0 0; padding-left: 22px; list-style: none;">
                        ${reasonItems}
                    </ul>
                </div>
            </div>
        `;

        Object.assign(banner.style, {
            position: "fixed",
            top: "0",
            left: "0",
            right: "0",
            background: "linear-gradient(135deg, #c62828 0%, #d32f2f 50%, #b71c1c 100%)",
            color: "white",
            padding: "20px 24px",
            fontFamily: "'Roboto', sans-serif",
            zIndex: "9999",
            boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
            borderBottom: "5px solid #ff1744",
            animation: "slideDown 0.5s cubic-bezier(0.22, 0.61, 0.36, 1)",
            backdropFilter: "blur(12px)",
            WebkitBackdropFilter: "blur(12px)"
        });

        document.body.appendChild(banner);

        setTimeout(() => {
            banner.style.animation = "slideUp 0.6s ease forwards";
            setTimeout(() => banner.remove(), 600);
        }, 9000);
    });

    evtSource.onerror = () => console.warn("SSE disconnected");
});
