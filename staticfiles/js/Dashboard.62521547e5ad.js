function getAccessToken() {
    return localStorage.getItem('access_token');
}

function getRefreshToken() {
    return localStorage.getItem('refresh_token');
}

function saveAccessToken(token) {
    localStorage.setItem('access_token', token);
}

function isAuthenticated() {
    return getAccessToken() !== null;
}

document.addEventListener('DOMContentLoaded', () => {
    if (!isAuthenticated()) {
        window.location.href = '/login/';
        return;
    }
    loadUserProfile();
    loadTourLists();
    loadDashboardSummary();

    const logoutButton = document.querySelector('.logout-btn');
    if (logoutButton) {
        logoutButton.addEventListener('click', logout);
    }

    const profileForm = document.getElementById('profileForm');
    if (profileForm) {
        profileForm.addEventListener('submit', updateProfile);
    }

    const passwordForm = document.getElementById('passwordForm');
    if (passwordForm) {
        passwordForm.addEventListener('submit', changePassword);
    }
});

async function apiRequest(url, options = {}) {
    const token = getAccessToken();
    options.headers = {
        ...(options.headers ||= {}),
        "Authorization": `Bearer ${token}`,
        "content-type": "application/json",
    };
    return fetch(url, options);
}

async function loadTourLists() {
    try {
        const [createdResponse, joinedResponse] = await Promise.all([
            apiRequest('/api/tours/'),
            apiRequest('/api/tours/joined/'),
        ]);

        if (createdResponse.status === 401 || joinedResponse.status === 401) {
            const refreshed = await refreshToken();
            if (refreshed) {
                loadTourLists();
                return;
            }
            logout();
            return;
        }

        const createdData = await createdResponse.json();
        const joinedData = await joinedResponse.json();
        renderTourList('createdTours', createdData.results || createdData, true);
        renderTourList('joinedTours', joinedData.results || joinedData, false);
    } catch (error) {
        console.error('Error fetching tours:', error);
        renderTourList('createdTours', [], true);
        renderTourList('joinedTours', [], false);
    }
}

function renderTourList(elementId, tours, showJoinCode) {
    const element = document.getElementById(elementId);
    if (!element) return;
    if (!tours.length) {
        element.innerHTML = '<p class="text-sm text-slate-400">No tours found.</p>';
        return;
    }
    element.innerHTML = tours.map((tour) => `
        <a href="/tours/${encodeURIComponent(tour.id)}/" class="block rounded-xl border border-slate-200 bg-slate-50 p-4 transition hover:border-brand-300 hover:bg-brand-50/50">
            <div class="flex items-start justify-between gap-3">
                <div><p class="font-bold text-slate-900">${escapeHtml(tour.title)}</p><p class="mt-1 text-sm text-slate-500">${escapeHtml(tour.destination)}</p></div>
                <div class="flex items-center gap-2">
                    ${showJoinCode ? `<span class="rounded-lg bg-brand-100 px-2.5 py-1 text-xs font-bold tracking-wider text-brand-700">${escapeHtml(tour.join_code)}</span>` : ''}
                </div>
            </div>
        </a>
    `).join('');
}

function escapeHtml(value) {
    return String(value || '').replace(/[&<>'"]/g, (character) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[character]));
}

async function loadUserProfile() {
    const token = getAccessToken();
    if (!token) {
        window.location.href = '/login/';
        return;
    }

    const loadingElement = document.getElementById('loading');
    if (loadingElement) {
        loadingElement.textContent = 'Loading...';
    }

    try {
        const response = await apiRequest('/api/profile/');

        if (response.status === 401) {
            const refreshed = await refreshToken();
            if (refreshed) {
                loadUserProfile();
                return;
            }
            logout();
            return;
        }

        let data = {};
        try {
            data = await response.json();
        } catch (error) {
            data = {};
        }

        if (!response.ok) {
            throw new Error('Failed to fetch user profile');
        }

        const user = data.user || data || {};
        const displayName = user.full_name || user.username || user.email || 'User';

        const welcomeHeading = document.getElementById('welcomeHeading');
        if (welcomeHeading) {
            welcomeHeading.textContent = `Welcome back, ${displayName}`;
        }

        const usernameField = document.getElementById('profileUsername');
        const emailField = document.getElementById('profileEmail');
        if (emailField) emailField.value = user.email || '';
        if (usernameField) usernameField.value = user.username || '';
        const phoneField = document.getElementById('profilePhone');
        if (phoneField) phoneField.value = user.phone_number || '';

        if (loadingElement) {
            loadingElement.textContent = '';
        }
    } catch (error) {
        console.error('Error fetching user profile:', error);
    }
}

async function loadDashboardSummary() {
    try {
        const response = await apiRequest('/api/dashboard/summary/');
        if (response.status === 401) {
            const refreshed = await refreshToken();
            if (refreshed) {
                loadDashboardSummary();
                return;
            }
            logout();
            return;
        }

        if (!response.ok) return;

        const data = await response.json();
        setText('statTotalTours', data.total_tours ?? 0);
        setText('statTotalMembers', data.total_members ?? 0);
        setText('statTotalExpenses', `Rs ${formatAmount(data.total_expenses)}`);

        const balance = parseFloat(data.balance || '0');
        const balanceCard = document.getElementById('statBalanceCard');
        const balanceHint = document.getElementById('statBalanceHint');
        setText('statBalance', `Rs ${formatAmount(Math.abs(balance))}`);

        if (balanceCard && balanceHint) {
            if (balance > 0) {
                balanceHint.textContent = "You're owed money overall";
            } else if (balance < 0) {
                balanceHint.textContent = 'You owe money overall';
            } else {
                balanceHint.textContent = "You're all settled up";
            }
        }
    } catch (error) {
        console.error('Error loading dashboard summary:', error);
    }
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function formatAmount(value) {
    const number = parseFloat(value || 0);
    return number.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

async function updateProfile(event) {
    event.preventDefault();
    const messageBox = document.getElementById('profileMessage');
    const email = document.getElementById('profileEmail').value.trim();
    const username = document.getElementById('profileUsername').value.trim();
    const phone = document.getElementById('profilePhone').value.trim();

    try {
        const response = await apiRequest('/api/profile/update/', {
            method: 'PATCH',
            body: JSON.stringify({ email, username, phone_number: phone }),
        });
        const data = await response.json();

        if (response.ok && data.success) {
            showProfileMessage(messageBox, 'Profile updated successfully.', true);
            const updatedUser = data.data || {};
            const emailField = document.getElementById('profileEmail');
            if (emailField) emailField.value = updatedUser.email || email;
            const usernameField = document.getElementById('profileUsername');
            if (usernameField) usernameField.value = updatedUser.username || username;
            const phoneField = document.getElementById('profilePhone');
            if (phoneField) phoneField.value = updatedUser.phone_number || phone;
            loadUserProfile();
        } else {
            const errorText = flattenErrors(data.errors) || data.message || 'Unable to update profile.';
            showProfileMessage(messageBox, errorText, false);
        }
    } catch (error) {
        showProfileMessage(messageBox, 'Server error. Please try again later.', false);
    }
}

async function changePassword(event) {
    event.preventDefault();
    const messageBox = document.getElementById('profileMessage');
    const oldPassword = document.getElementById('oldPassword').value;
    const newPassword = document.getElementById('newPassword').value;

    try {
        const response = await apiRequest('/api/profile/change-password/', {
            method: 'POST',
            body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
        });
        const data = await response.json();

        if (response.ok && data.success) {
            showProfileMessage(messageBox, 'Password updated successfully.', true);
            document.getElementById('passwordForm').reset();
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user_id');
            window.setTimeout(() => { window.location.href = '/login/'; }, 700);
        } else {
            showProfileMessage(messageBox, data.message || 'Unable to change password.', false);
        }
    } catch (error) {
        showProfileMessage(messageBox, 'Server error. Please try again later.', false);
    }
}

function flattenErrors(errors) {
    if (!errors || typeof errors !== 'object') return null;
    const [field, messages] = Object.entries(errors)[0] || [];
    if (!field) return null;
    const message = Array.isArray(messages) ? messages[0] : messages;
    return `${field.replace(/_/g, ' ')}: ${message}`;
}

function showProfileMessage(el, message, success) {
    if (!el) return;
    el.textContent = message;
    el.classList.remove('hidden');
    el.className = `mb-4 rounded-xl px-4 py-3 text-sm ${
        success ? 'border border-credit-500/30 bg-credit-50 text-credit-600'
                : 'border border-debit-500/30 bg-debit-50 text-debit-600'
    }`;
}

async function logout() {
    try {
        await apiRequest('/api/logout/', { method: 'POST' });
    } catch (error) {
        console.error('Error logging out:', error);
    } finally {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_id');
        window.location.href = '/login/';
    }
}

async function refreshToken() {
    const refresh = getRefreshToken();
    if (!refresh) {
        return false;
    }

    try {
        const response = await fetch('/api/token/refresh/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh }),
        });

        if (!response.ok) {
            return false;
        }

        const data = await response.json();
        saveAccessToken(data.access);
        return true;
    } catch (error) {
        console.error('Error refreshing token:', error);
        return false;
    }
}
