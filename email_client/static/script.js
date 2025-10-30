document.addEventListener('DOMContentLoaded', function() {
    const emailList = document.querySelector('.email-list');
    const emailContent = document.querySelector('.email-content');
    const backButton = document.querySelector('.back-button');
    const sidebarLinks = document.querySelectorAll('.sidebar-menu a');
    const settingsBtn = document.getElementById('settings-btn');
    const settingsView = document.querySelector('.settings-view');
    const themeToggler = document.getElementById('theme-toggler');

    const emails = {
        inbox: [
            { id: 1, sender: 'John Doe', subject: 'Meeting Tomorrow', preview: 'Hey, just wanted to confirm our meeting for tomorrow at 10am.', body: 'Hey, just wanted to confirm our meeting for tomorrow at 10am. Let me know if that still works for you.', read: false },
            { id: 2, sender: 'Jane Smith', subject: 'Project Proposal', preview: 'Here is the project proposal we discussed.', body: 'Here is the project proposal we discussed. Please review it and let me know your thoughts.', read: true },
        ],
        sent: [
            { id: 3, sender: 'You', subject: 'Re: Project Proposal', preview: 'Thanks for sending this over. I will take a look and get back to you.', body: 'Thanks for sending this over. I will take a look and get back to you.', read: true },
        ],
        drafts: [],
        archive: [],
        spam: [
            { id: 4, sender: 'Spammy McSpamface', subject: 'You have won a prize!', preview: 'Click here to claim your prize!', body: 'This is a spam email.', read: false },
        ],
        phishing: [
            { id: 5, sender: 'Bank of Nowhere', subject: 'Action Required: Your account has been suspended', preview: 'Please click here to verify your account details.', body: 'This is a phishing email.', read: false },
        ],
        trash: [],
    };

    function renderEmailList(folder) {
        emailList.innerHTML = '';
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
                    <i class="material-icons">reply</i>
                    <i class="material-icons">archive</i>
                    <i class="material-icons">delete</i>
                    <i class="material-icons">mark_as_unread</i>
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

        document.querySelector('.email-content-subject').textContent = email.subject;
        document.querySelector('.email-content-sender').textContent = `From: ${email.sender}`;
        document.querySelector('.email-content-body').textContent = email.body;
    }

    function goBack() {
        emailList.style.display = 'block';
        emailContent.style.display = 'none';
        settingsView.style.display = 'none';
        backButton.style.display = 'none';
    }

    backButton.addEventListener('click', goBack);

    sidebarLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            sidebarLinks.forEach(l => l.parentElement.classList.remove('active'));
            link.parentElement.classList.add('active');
            const folder = link.querySelector('span').textContent.toLowerCase();
            renderEmailList(folder);
            goBack();
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

    // Initial render
    renderEmailList('inbox');
});