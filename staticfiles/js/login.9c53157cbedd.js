const loginForm = document.getElementById('loginform');
const messageBox = document.getElementById('error-message');
const loginButton = document.getElementById('login-button');
const passwordInput = document.getElementById('id_password');
const togglePassword = document.getElementById('togglePassword');
const showPasswordIcon = document.getElementById('showPasswordIcon');
const hidePasswordIcon = document.getElementById('hidePasswordIcon');

togglePassword?.addEventListener('click', () => {
    const isHidden = passwordInput.type === 'password';
    passwordInput.type = isHidden ? 'text' : 'password';
    togglePassword.setAttribute('aria-label', isHidden ? 'Hide password' : 'Show password');
    togglePassword.title = isHidden ? 'Hide password' : 'Show password';
    showPasswordIcon.classList.toggle('hidden', isHidden);
    hidePasswordIcon.classList.toggle('hidden', !isHidden);
});

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

loginForm.addEventListener('submit', async function loginUser(event) {
    event.preventDefault();
    const email = document.getElementById('id_username').value;
    const password = document.getElementById('id_password').value;

    messageBox.innerHTML = ''; // Clear previous error messages

    loginButton.disabled = true; // Disable the button to prevent multiple submissions
    loginButton.textContent = 'Logging in...'; // Change button text to indicate loading

    try {
        const response = await fetch('/api/login/', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ email, password }),
        });

        let data = {};
        try {
            data = await response.json();
        } catch (error) {
            data = {};
        }

        if (response.ok) {
            localStorage.setItem('access_token', data.tokens.access);
            localStorage.setItem('refresh_token', data.tokens.refresh);
            localStorage.setItem('user_id', data.user.id);

            showErrorMessage('Login successful! Redirecting...', 'success');
            setTimeout(() => {
                window.location.href = '/dashboard/';
            }, 1200);
        } else {
            const errorMessage = data.detail || data.message || 'Login failed. Please try again.';
            showErrorMessage(errorMessage, 'error');
        }
    } catch (error) {
        console.error('Error occurred while logging in:', error);
        showErrorMessage('An unexpected error occurred. Please try again.', 'error');
    } finally {
        loginButton.disabled = false; // Re-enable the button
        loginButton.textContent = 'Login'; // Reset button text
    }
});

function showErrorMessage(message,type) {
    const cls = type === 'success'
        ? 'rounded-xl border border-credit-500/30 bg-credit-50 px-4 py-3 text-sm font-medium text-credit-600'
        : 'rounded-xl border border-debit-500/30 bg-debit-50 px-4 py-3 text-sm font-medium text-debit-600';
    messageBox.innerHTML = `<div class="${cls}">${message}</div>`;
}
