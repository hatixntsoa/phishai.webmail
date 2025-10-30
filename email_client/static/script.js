document.addEventListener('DOMContentLoaded', function() {
    const emailList = document.querySelector('.email-list');
    const emailContent = document.querySelector('.email-content');
    const backButton = document.querySelector('.back-button');
    const sidebarLinks = document.querySelectorAll('.sidebar-menu a');
    const settingsBtn = document.getElementById('settings-btn');
    const settingsView = document.querySelector('.settings-view');
    const themeToggler = document.getElementById('theme-toggler');
    const newMessageBtn = document.querySelector('.new-message .btn');
    const composeBackdrop = document.querySelector('.compose-backdrop');
    const composeWindow = document.querySelector('.compose-window');
    const closeComposeBtn = document.querySelector('.close-compose-btn');
    const activeIndicator = document.querySelector('.active-indicator');

    // --- Email Data Generation ---
    const SENDER_NAMES = ['Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Frank', 'Grace', 'Heidi', 'Ivan', 'Judy'];
    const SUBJECT_LINES = ['Project Update', 'Meeting Reminder', 'Weekly Report', 'Fwd: Important Document', 'Quick Question', 'Lunch Plans', 'Invoice Attached', 'Your Order Has Shipped'];
    const PREVIEW_TEXT = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.';
    let emailIdCounter = 1;

    function generateEmails(count) {
        const emails = [];
        for (let i = 0; i < count; i++) {
            const sender = SENDER_NAMES[Math.floor(Math.random() * SENDER_NAMES.length)];
            const subject = SUBJECT_LINES[Math.floor(Math.random() * SUBJECT_LINES.length)];
            emails.push({
                id: emailIdCounter++,
                sender: `${sender} ${String.fromCharCode(65 + i)}`, // Add a letter to make it unique
                subject: subject,
                preview: PREVIEW_TEXT.substring(0, Math.floor(Math.random() * 50) + 20),
                body: PREVIEW_TEXT,
                read: Math.random() > 0.5,
            });
        }
        return emails;
    }

    function getRandomCount(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }

    const emails = {
        inbox: generateEmails(getRandomCount(30, 50)),
        sent: generateEmails(getRandomCount(20, 40)),
        drafts: generateEmails(getRandomCount(5, 10)), // Fewer drafts
        archive: generateEmails(getRandomCount(20, 30)),
        spam: generateEmails(getRandomCount(25, 45)),
        phishing: generateEmails(getRandomCount(10, 20)),
        trash: generateEmails(getRandomCount(15, 25)),
    };

    function renderEmailList(folder) {
        emailList.innerHTML = '';

        const headerRow = document.createElement('div');
        headerRow.classList.add('email-list-header');
        const folderName = folder.charAt(0).toUpperCase() + folder.slice(1);
        headerRow.innerHTML = `
            <div class="folder-name">${folderName}</div>
            <div class="email-count">${emails[folder].length}</div>
        `;
        emailList.appendChild(headerRow);

        emails[folder].forEach(email => {
            const emailItem = document.createElement('div');
            emailItem.classList.add('email-item');
            if (!email.read) {
                emailItem.classList.add('unread');
            }
            emailItem.dataset.id = email.id;
            emailItem.innerHTML = `
                <div class="email-sender-initial">${email.sender.charAt(0)}</div>
                <div class="email-sender">${email.sender}</div>
                <div class="email-subject">${email.subject}</div>
                <div class="email-preview">${email.preview}</div>
                <div class="email-actions">
                    <i class="material-icons-outlined">reply</i>
                    <i class="material-icons-outlined">archive</i>
                    <i class="material-icons-outlined">delete</i>
                    <i class="material-icons-outlined">mark_as_unread</i>
                </div>
            `;
            emailItem.addEventListener('click', () => showEmail(email, folder));
            emailList.appendChild(emailItem);
        });
    }

    function showEmail(email, folder) {
        email.read = true;
        renderEmailList(folder);
        emailList.style.display = 'none';
        settingsView.style.display = 'none';
        emailContent.style.display = 'block';
        backButton.style.display = 'block';
        document.querySelector('.search-bar').style.display = 'none';

        document.querySelector('.email-content-subject').textContent = email.subject;
        document.querySelector('.email-content-sender').textContent = `From: ${email.sender}`;
        document.querySelector('.email-content-body').textContent = email.body;
    }

    function goBack() {
        emailList.style.display = 'block';
        emailContent.style.display = 'none';
        settingsView.style.display = 'none';
        backButton.style.display = 'none';
        document.querySelector('.search-bar').style.display = 'flex';
    }

    function moveIndicator(targetLi) {
        if (!targetLi) return;
        const top = targetLi.offsetTop;
        const height = targetLi.offsetHeight;
        activeIndicator.style.top = `${top}px`;
        activeIndicator.style.height = `${height}px`;
    }

    backButton.addEventListener('click', goBack);

    sidebarLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            sidebarLinks.forEach(l => l.parentElement.classList.remove('active'));
            const targetLi = link.parentElement;
            targetLi.classList.add('active');
            const folder = link.querySelector('span').textContent.toLowerCase();
            renderEmailList(folder);
            goBack();
            moveIndicator(targetLi);
        });
    });

    settingsBtn.addEventListener('click', (e) => {
        e.preventDefault();
        emailList.style.display = 'none';
        emailContent.style.display = 'none';
        backButton.style.display = 'block';
        settingsView.style.display = 'block';
    });

    themeToggler.addEventListener('change', () => {
        document.body.classList.toggle('dark-mode');
    });

    function showComposeWindow() {
        composeBackdrop.style.display = 'block';
        composeWindow.style.display = 'flex';
    }

    function hideComposeWindow() {
        composeBackdrop.style.display = 'none';
        composeWindow.style.display = 'none';
    }

    newMessageBtn.addEventListener('click', showComposeWindow);
    closeComposeBtn.addEventListener('click', hideComposeWindow);
    composeBackdrop.addEventListener('click', hideComposeWindow);

    // Dragging logic for compose window
    const composeHeader = document.querySelector('.compose-header');
    let isDragging = false;
    let offsetX, offsetY;

    composeHeader.addEventListener('mousedown', (e) => {
        isDragging = true;
        offsetX = e.clientX - composeWindow.offsetLeft;
        offsetY = e.clientY - composeWindow.offsetTop;
        composeWindow.style.transform = ''; // Remove transform to use top/left for positioning
    });

    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        
        let newX = e.clientX - offsetX;
        let newY = e.clientY - offsetY;

        composeWindow.style.left = `${newX}px`;
        composeWindow.style.top = `${newY}px`;
    });

    document.addEventListener('mouseup', () => {
        isDragging = false;
    });

    // Initial render
    renderEmailList('inbox');
    const initialActiveLi = document.querySelector('.sidebar-menu li.active');
    moveIndicator(initialActiveLi);
});