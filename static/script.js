// ———————————————————————————————
// GLOBALS – accessible everywhere
// ———————————————————————————————
let currentEmails = [];
let emails = { inbox: currentEmails };
let lastEmailCount = 0;

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

    // Load initial emails from Flask (first page load)
    currentEmails = Array.isArray(window.REAL_EMAILS) ? window.REAL_EMAILS : [];
    emails.inbox = currentEmails;
    lastEmailCount = currentEmails.length;

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
        if (msgDate.getTime() === yesterday.getTime()) {
            return 'Yesterday';
        }
        if (date.getFullYear() === now.getFullYear()) {
            return date.toLocaleDateString([], { day: 'numeric', month: 'short' });
        }
        return date.toLocaleDateString([], { day: '2-digit', month: '2-digit', year: 'numeric' });
    }

    // ———————————————————————————————
    // RENDER EMAIL LIST — IDENTICAL TO YOUR WORKING .BAK
    // ———————————————————————————————
    window.renderEmailList = function (folder = 'inbox') {
        if (folder !== 'inbox') {
            emailList.innerHTML = `<p style="text-align:center;padding:60px;color:#888;">${folder.charAt(0).toUpperCase() + folder.slice(1)} coming soon...</p>`;
            return;
        }

        if (currentEmails.length === 0) {
            emailList.innerHTML = `<p style="text-align:center;padding:60px;color:#888;">No messages in Inbox</p>`;
            return;
        }

        emailList.innerHTML = '';
        const header = document.createElement('div');
        header.classList.add('email-list-header');
        header.innerHTML = `<div class="folder-name">Inbox</div><div class="email-count">${currentEmails.length}</div>`;
        emailList.appendChild(header);

        currentEmails.forEach(email => {
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

            // EXACT SAME CLICK BEHAVIOR AS YOUR WORKING VERSION
            item.addEventListener('click', e => {
                if (e.target.closest('.email-actions')) return; // don't open if clicking icons
                showEmail(email);
            });

            emailList.appendChild(item);
        });
    };

    // EXACT SAME showEmail() AS YOUR WORKING VERSION
    function showEmail(email) {
        email.read = true;
        window.renderEmailList('inbox'); // re-render to update unread status

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

    // Event listeners (unchanged)
    backButton.addEventListener('click', goBack);
    sidebarLinks.forEach(link => {
        link.addEventListener('click', e => {
            e.preventDefault();
            document.querySelectorAll('.sidebar-menu li').forEach(l => l.classList.remove('active'));
            const li = link.parentElement;
            li.classList.add('active');
            const folder = link.querySelector('span').textContent.toLowerCase();
            window.renderEmailList(folder);
            goBack();
            moveIndicator(li);
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

    const showCompose = () => { composeBackdrop.style.display = 'block'; composeWindow.style.display = 'flex'; };
    const hideCompose = () => { composeBackdrop.style.display = 'none'; composeWindow.style.display = 'none'; };
    newMessageBtn.onclick = showCompose;
    closeComposeBtn.onclick = hideCompose;
    composeBackdrop.onclick = hideCompose;

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

    // First render
    window.renderEmailList('inbox');
    moveIndicator(document.querySelector('.sidebar-menu li.active'));

    // ———————————————————————————————
    // REAL-TIME: ONLY REFRESH WHEN EMAIL COUNT INCREASES (like your old logic)
    // ———————————————————————————————
    const evtSource = new EventSource("/stream");

    evtSource.onmessage = function(e) {
        if (e.data.trim() === "" || e.data.startsWith(":")) return; // heartbeat

        try {
            const newEmails = JSON.parse(e.data);

            // ONLY RE-RENDER IF MORE EMAILS ARRIVED (exactly like your old working version)
            if (newEmails.length > lastEmailCount) {
                console.log(`New email! ${lastEmailCount} → ${newEmails.length}`);
                lastEmailCount = newEmails.length;
                currentEmails = newEmails;
                emails.inbox = currentEmails;

                if (document.querySelector('.sidebar-menu li.active span')?.textContent.toLowerCase() === 'inbox') {
                    window.renderEmailList('inbox');
                }
            } else if (newEmails.length !== currentEmails.length) {
                // If count decreased (deleted/archived), always refresh
                currentEmails = newEmails;
                emails.inbox = currentEmails;
                if (document.querySelector('.sidebar-menu li.active span')?.textContent.toLowerCase() === 'inbox') {
                    window.renderEmailList('inbox');
                }
            }
            // If same count → do nothing (prevents flicker & delay)
        } catch (err) {
            console.warn("SSE parse error:", err);
        }
    };

    evtSource.onerror = function() {
        console.warn("SSE disconnected. Reconnecting...");
        evtSource.close();
        setTimeout(() => location.reload(), 3000);
    };
});
