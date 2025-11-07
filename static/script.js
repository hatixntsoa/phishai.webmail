document.addEventListener('DOMContentLoaded', async function() { // Make function async
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

    let emails = {}; // To be populated from JSON

    // --- Fetch Email Data ---
    try {
        const response = await fetch('/static/emails.json'); // Corrected path
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        emails = await response.json();
    } catch (error) {
        console.error("Could not fetch emails:", error);
        // Optionally, display an error message to the user
        emailList.innerHTML = '<p style="text-align: center; padding: 20px;">Could not load emails.</p>';
        return; // Stop execution if emails can't be loaded
    }

    function renderEmailList(folder) {
        if (!emails[folder]) {
            console.error(`Folder "${folder}" does not exist in emails data.`);
            return;
        }
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
                <div class="email-date">${email.date}</div>
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
        emailPreviewContainer.style.display = 'flex';
        backButton.style.display = 'block';
        document.querySelector('.search-bar').style.display = 'none';

        document.querySelector('.email-preview-container .email-subject').textContent = email.subject;
        document.querySelector('.email-preview-container .email-sender').textContent = `From: ${email.sender}`;
        document.querySelector('.email-content-body').textContent = email.body;
    }

    function goBack() {
        emailList.style.display = 'block';
        emailPreviewContainer.style.display = 'none';
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
        emailPreviewContainer.style.display = 'none';
        settingsView.style.display = 'block';
        backButton.style.display = 'block';
        document.querySelector('.search-bar').style.display = 'none';
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