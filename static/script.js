// ———————————————————————————————
// GLOBALS – exactly like your original working version
// ———————————————————————————————
let currentEmails = [];
let emails = { inbox: [], sent: [] };
let lastEmailCount = { inbox: 0, sent: 0 };

// ———————————————————————————————
// DOM IS READY
// ———————————————————————————————
document.addEventListener('DOMContentLoaded', function () {
    const emailList = document.querySelector('.email-list');
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

    // Compose
    const toInput = composeWindow.querySelector('input[placeholder="To"]');
    const subjectInput = composeWindow.querySelector('input[placeholder="Subject"]');
    const bodyTextarea = composeWindow.querySelector('textarea');
    const sendBtn = composeWindow.querySelector('.btn-primary');

    // Load initial inbox from Flask
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

    // YOUR ORIGINAL EMAIL ROW UI — 100% UNTOUCHED
    window.renderEmailList = function (folder = 'inbox') {
        const data = emails[folder] || [];
        emailList.innerHTML = '';

        if (data.length === 0) {
            emailList.innerHTML = `<p style="text-align:center;padding:60px;color:#888;">No messages in ${folder.charAt(0).toUpperCase() + folder.slice(1)}</p>`;
            return;
        }

        const header = document.createElement('div');
        header.classList.add('email-list-header');
        header.innerHTML = `<div class="folder-name">${folder.charAt(0).toUpperCase() + folder.slice(1)}</div><div class="email-count">${data.length}</div>`;
        emailList.appendChild(header);

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
                if (e.target.closest('.email-actions')) return;
                showEmail(email);
            });

            emailList.appendChild(item);
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
        emailList.style.display = 'block';
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

    // SEND EMAIL
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

    // SIDEBAR — loads correct folder every time
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
                        lastEmailCount.inbox = data.length;
                        window.renderEmailList('inbox');
                    });
            } else if (folder === 'sent') {
                fetch('/api/emails?folder=sent')
                    .then(r => r.json())
                    .then(data => {
                        emails.sent = data;
                        lastEmailCount.sent = data.length;
                        window.renderEmailList('sent');
                    });
            } else {
                emailList.innerHTML = `<p style="text-align:center;padding:60px;color:#888;">${folder.charAt(0).toUpperCase() + folder.slice(1)} coming soon...</p>`;
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

    // Draggable compose
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

    // Initial render
    window.renderEmailList('inbox');
    moveIndicator(document.querySelector('.sidebar-menu li.active'));

    // REAL-TIME — supports both Inbox & Sent
    const evtSource = new EventSource("/stream");

    evtSource.addEventListener("inbox", e => {
        try {
            const data = JSON.parse(e.data);
            emails.inbox = data;
            lastEmailCount.inbox = data.length;
            if (document.querySelector('.sidebar-menu li.active span')?.textContent.toLowerCase() === 'inbox') {
                window.renderEmailList('inbox');
            }
        } catch (err) {}
    });

    evtSource.addEventListener("sent", e => {
        try {
            const data = JSON.parse(e.data);
            emails.sent = data;
            lastEmailCount.sent = data.length;
            if (document.querySelector('.sidebar-menu li.active span')?.textContent.toLowerCase() === 'sent') {
                window.renderEmailList('sent');
            }
        } catch (err) {}
    });

    evtSource.onerror = () => console.warn("SSE disconnected");
});
