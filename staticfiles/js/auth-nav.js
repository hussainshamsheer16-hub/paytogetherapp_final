(function setupAuthNavigation() {
    const notificationState = { lastUnreadCount: 0 };

    function isAuthenticated() {
        return Boolean(localStorage.getItem("access_token"));
    }

    function playNotificationSound() {
        const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
        if (!AudioContextCtor) return;

        try {
            const audioContext = new AudioContextCtor();
            const now = audioContext.currentTime;

            const oscillatorA = audioContext.createOscillator();
            const oscillatorB = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillatorA.type = "triangle";
            oscillatorA.frequency.setValueAtTime(880, now);
            oscillatorA.frequency.exponentialRampToValueAtTime(620, now + 0.22);

            oscillatorB.type = "sine";
            oscillatorB.frequency.setValueAtTime(1320, now + 0.04);
            oscillatorB.frequency.exponentialRampToValueAtTime(980, now + 0.26);

            gainNode.gain.setValueAtTime(0.0001, now);
            gainNode.gain.exponentialRampToValueAtTime(0.14, now + 0.03);
            gainNode.gain.exponentialRampToValueAtTime(0.0001, now + 0.42);

            oscillatorA.connect(gainNode);
            oscillatorB.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillatorA.start(now);
            oscillatorB.start(now + 0.04);
            oscillatorA.stop(now + 0.42);
            oscillatorB.stop(now + 0.42);

            setTimeout(() => audioContext.close(), 500);
        } catch (error) {
            console.warn("Unable to play notification sound:", error);
        }
    }

    function getAuthHeaders(extra = {}) {
        const token = localStorage.getItem("access_token");
        return {
            ...extra,
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        };
    }

    function accessTokenExpiresSoon() {
        const token = localStorage.getItem("access_token");
        if (!token) return true;

        try {
            const encodedPayload = token.split(".")[1]
                .replace(/-/g, "+")
                .replace(/_/g, "/");
            const paddedPayload = encodedPayload.padEnd(
                encodedPayload.length + (4 - encodedPayload.length % 4) % 4,
                "=",
            );
            const payload = JSON.parse(atob(paddedPayload));
            // Refresh 30 seconds early so the polling request is not sent with
            // a token that is about to expire.
            return !payload.exp || Date.now() >= (payload.exp - 30) * 1000;
        } catch (_error) {
            return true;
        }
    }

    async function refreshAccessToken() {
        const refreshToken = localStorage.getItem("refresh_token");
        if (!refreshToken) return false;

        try {
            const response = await fetch("/api/token/refresh/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ refresh: refreshToken }),
            });
            if (!response.ok) return false;

            const data = await response.json();
            if (!data.access) return false;
            localStorage.setItem("access_token", data.access);
            return true;
        } catch (error) {
            console.error("Unable to refresh the access token:", error);
            return false;
        }
    }

    async function ensureValidAccessToken() {
        if (!isAuthenticated()) return false;
        if (!accessTokenExpiresSoon()) return true;

        const refreshed = await refreshAccessToken();
        if (!refreshed) logout();
        return refreshed;
    }

    async function authenticatedFetch(url, options = {}) {
        if (!(await ensureValidAccessToken())) return null;

        const requestOptions = {
            ...options,
            headers: getAuthHeaders(options.headers || {}),
        };
        let response = await fetch(url, requestOptions);

        // A server-side expiry or a client clock difference can still produce
        // one 401. Refresh and retry that request once before logging out.
        if (response.status === 401 && await refreshAccessToken()) {
            response = await fetch(url, {
                ...options,
                headers: getAuthHeaders(options.headers || {}),
            });
        }
        if (response.status === 401) logout();
        return response;
    }

    function escapeHtml(value) {
        const element = document.createElement("div");
        element.textContent = String(value ?? "");
        return element.innerHTML;
    }

    function logout() {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user_id");
        window.location.href = "/login/";
    }

    async function markNotificationRead(notificationId) {
        if (!notificationId) return;
        try {
            await authenticatedFetch(`/api/notifications/${notificationId}/read/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
            });
        } catch (error) {
            console.error("Unable to mark notification as read:", error);
        }
    }

    async function approveNotificationPayment(notification, decision, actionButton) {
        actionButton.disabled = true;
        actionButton.textContent = decision === "received" ? "Saving..." : "Checking...";

        try {
            const response = await authenticatedFetch(
                `/api/tours/${notification.dataset.tourId}/settlements/${notification.dataset.paymentId}/approve/`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ decision }),
                },
            );
            if (!response) return;
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.detail || "Unable to update this payment.");
            }

            await markNotificationRead(notification.dataset.notificationId);
            await loadNotifications();
        } catch (error) {
            console.error("Unable to approve notification payment:", error);
            actionButton.disabled = false;
            actionButton.textContent = decision === "received" ? "Yes, received" : "No, check again";
            window.alert(error.message || "Unable to update this payment.");
        }
    }

    async function loadNotifications() {
        if (!isAuthenticated()) return;

        const notificationTargets = [
            {
                button: document.getElementById("notificationButton"),
                menu: document.getElementById("notificationMenu"),
                badge: document.getElementById("notificationBadge"),
            },
            {
                button: document.getElementById("dashboardNotificationButton"),
                menu: document.getElementById("dashboardNotificationMenu"),
                badge: document.getElementById("dashboardNotificationBadge"),
            },
        ].filter((target) => target.button && target.menu);

        if (!notificationTargets.length) return;

        try {
            const response = await authenticatedFetch("/api/notifications/");
            if (!response) return;
            if (!response.ok) return;
            const data = await response.json();
            const unreadCount = Number(data.count || 0);
            notificationTargets.forEach(({ badge }) => {
                if (!badge) return;
                badge.textContent = unreadCount > 0 ? unreadCount : "";
                badge.classList.toggle("hidden", unreadCount <= 0);
                badge.classList.toggle("animate-pulse", unreadCount > 0);
                badge.dataset.count = String(unreadCount);
            });

            if (unreadCount > notificationState.lastUnreadCount) {
                playNotificationSound();
            }

            notificationState.lastUnreadCount = unreadCount;

            const items = data.notifications || [];
            const content = items.length
                ? items.map((item) => `
                    <div data-notification-id="${item.id}" data-payment-id="${item.payment_id}" data-tour-id="${item.tour_id}" class="notification-item block w-full rounded-2xl border ${item.is_read ? 'border-slate-200 bg-white' : 'border-brand-200 bg-brand-50/60'} px-3 py-2.5 text-left transition hover:-translate-y-0.5 hover:border-brand-300 hover:bg-brand-50">
                        <div class="flex items-center justify-between gap-2">
                            <span class="text-sm font-semibold text-slate-900">${escapeHtml(item.title)}</span>
                            ${item.is_read ? '<span class="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">Read</span>' : '<span class="inline-flex h-2.5 w-2.5 rounded-full bg-brand-600 shadow-[0_0_0_4px_rgba(37,112,245,0.12)]"></span>'}
                        </div>
                        <p class="mt-1.5 text-xs leading-relaxed text-slate-600">${escapeHtml(item.message)}</p>
                        ${item.can_approve ? `<div class="mt-3 flex gap-2 border-t border-brand-100 pt-2.5">
                            <button type="button" data-notification-decision="received" class="notification-action flex-1 rounded-lg bg-emerald-600 px-2 py-1.5 text-xs font-bold text-white transition hover:bg-emerald-700">Yes, received</button>
                            <button type="button" data-notification-decision="not_confirmed" class="notification-action flex-1 rounded-lg border border-amber-200 bg-amber-50 px-2 py-1.5 text-xs font-bold text-amber-700 transition hover:bg-amber-100">No, check again</button>
                        </div>` : ""}
                    </div>
                `).join("")
                : `<div class="flex flex-col items-center justify-center px-3 py-6 text-center">
                    <div class="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-400">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a6 6 0 00-6 6v3.586l-1.707 3.414A1 1 0 005.234 16h13.532a1 1 0 00.941-1.333L18 11.586V8a6 6 0 00-6-6zm0 20a2.5 2.5 0 002.45-2h-4.9A2.5 2.5 0 0012 22z"/></svg>
                    </div>
                    <p class="text-sm font-medium text-slate-500">No notifications yet.</p>
                </div>`;
            notificationTargets.forEach(({ menu }) => {
                menu.innerHTML = content;
                menu.querySelectorAll(".notification-item").forEach((item) => {
                    item.addEventListener("click", async (event) => {
                        if (event.target.closest(".notification-action")) return;
                        await markNotificationRead(item.dataset.notificationId);
                        await loadNotifications();
                    });

                    item.querySelectorAll(".notification-action").forEach((actionButton) => {
                        actionButton.addEventListener("click", () => {
                            approveNotificationPayment(item, actionButton.dataset.notificationDecision, actionButton);
                        });
                    });
                });
            });
        } catch (error) {
            console.error("Error loading notifications:", error);
        }
    }

    function setupNotificationButton(buttonId, menuId) {
        const button = document.getElementById(buttonId);
        const menu = document.getElementById(menuId);
        if (!button || !menu || button.dataset.notificationsReady === "true") return;

        button.dataset.notificationsReady = "true";
        button.addEventListener("click", () => {
            const isHidden = menu.classList.toggle("hidden");
            button.setAttribute("aria-expanded", String(!isHidden));
        });

        document.addEventListener("click", (event) => {
            if (!button.contains(event.target) && !menu.contains(event.target)) {
                menu.classList.add("hidden");
                button.setAttribute("aria-expanded", "false");
            }
        });
    }

    function renderNavigation() {
        const authenticated = isAuthenticated();
        const authNav = document.getElementById("authNav");
        const primaryNav = document.getElementById("primaryNav");
        const mobileNav = document.getElementById("mobileNav");

        if (authNav) {
            authNav.innerHTML = authenticated
                ? `<div class="relative flex items-center gap-2">
                    <button type="button" id="notificationButton" class="group relative rounded-xl border border-slate-200 bg-gradient-to-br from-white to-slate-50 p-2.5 text-slate-700 shadow-sm transition hover:-translate-y-0.5 hover:border-brand-200 hover:text-brand-600 hover:shadow-md" aria-label="Notifications">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 2a6 6 0 00-6 6v3.586l-1.707 3.414A1 1 0 005.234 16h13.532a1 1 0 00.941-1.333L18 11.586V8a6 6 0 00-6-6zm0 20a2.5 2.5 0 002.45-2h-4.9A2.5 2.5 0 0012 22z"/>
                        </svg>
                        <span id="notificationBadge" class="absolute -right-1.5 -top-1.5 hidden min-h-5 min-w-5 rounded-full bg-gradient-to-r from-red-500 to-rose-500 px-1 text-[10px] font-bold text-white shadow-lg shadow-red-500/30"></span>
                    </button>
                    <div id="notificationMenu" class="absolute right-0 top-12 z-50 hidden w-[22rem] max-h-[24rem] overflow-y-auto rounded-2xl border border-slate-200 bg-white p-2 shadow-[0_18px_40px_-16px_rgba(15,23,42,0.28)] ring-1 ring-slate-100"></div>
                    <button type="button" id="logoutButton" class="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-600">Logout</button>
                </div>`
                : `<a href="/login/" class="rounded-lg px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100">Login</a>
                   <a href="/register/" class="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-soft transition hover:bg-brand-700">Get started</a>`;

            const logoutButton = document.getElementById("logoutButton");
            if (logoutButton) logoutButton.addEventListener("click", logout);

            setupNotificationButton("notificationButton", "notificationMenu");
        }

        setupNotificationButton("dashboardNotificationButton", "dashboardNotificationMenu");

        if (primaryNav && authenticated) {
            primaryNav.innerHTML = `<a href="/" class="rounded-lg px-3 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-100 hover:text-slate-900">Home</a>
                <a href="/dashboard/" class="rounded-lg px-3 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-100 hover:text-slate-900">Dashboard</a>
                <a href="/tours/" class="rounded-lg px-3 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-100 hover:text-slate-900">My Tours</a>
                <a href="/tours/join/" class="rounded-lg px-3 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-100 hover:text-slate-900">Join Tour</a>`;
        }

        if (mobileNav && authenticated) {
            mobileNav.innerHTML = `<a href="/" class="rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">Home</a>
                <a href="/dashboard/" class="rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">Dashboard</a>
                <a href="/tours/" class="rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">My Tours</a>
                <a href="/tours/join/" class="rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">Join Tour</a>
                <button type="button" id="mobileLogoutButton" class="rounded-lg px-3 py-2 text-left text-sm font-semibold text-red-600 hover:bg-red-50">Logout</button>`;
            const mobileLogoutButton = document.getElementById("mobileLogoutButton");
            if (mobileLogoutButton) mobileLogoutButton.addEventListener("click", logout);
        }

        if (authenticated) {
            loadNotifications();
            if (!window.payTogetherNotificationPolling) {
                window.payTogetherNotificationPolling = window.setInterval(loadNotifications, 20000);
            }
        }
    }

    document.addEventListener("DOMContentLoaded", renderNavigation);
})();
