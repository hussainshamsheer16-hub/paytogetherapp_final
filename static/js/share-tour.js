function getShareTourId() {
    const value = document.getElementById("share-tour-id");
    return value ? JSON.parse(value.textContent) : null;
}

function setShareMessage(message, type = "success") {
    const element = document.getElementById("shareMessage");
    element.textContent = message;
    element.className = `mt-5 rounded-xl px-4 py-3 text-center text-sm font-medium ${
        type === "success" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"
    }`;
}

async function copyShareText(text) {
    if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return;
    }

    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    const copied = document.execCommand("copy");
    textarea.remove();
    if (!copied) throw new Error("Copy failed");
}

function showShareError(message) {
    document.getElementById("shareLoading").classList.add("hidden");
    const error = document.getElementById("shareError");
    error.textContent = message;
    error.classList.remove("hidden");
}

document.addEventListener("DOMContentLoaded", async () => {
    const tourId = getShareTourId();
    const token = localStorage.getItem("access_token");
    if (!tourId || !token) {
        window.location.href = "/login/";
        return;
    }

    try {
        const response = await fetch(`/api/tours/${tourId}/`, {
            headers: { Authorization: `Bearer ${token}` },
        });
        if (response.status === 401) {
            window.location.href = "/login/";
            return;
        }
        if (!response.ok) throw new Error("This tour is unavailable.");

        const tour = await response.json();
        const code = tour.join_code || "";
        const inviteText = `Join my tour “${tour.title}” with this code: ${code}`;
        const currentUrl = `${window.location.origin}/tours/join/`;
        const message = `${inviteText}\n${currentUrl}`;
        const encodedMessage = encodeURIComponent(message);

        document.getElementById("shareSubtitle").textContent = `Invite people to ${tour.title}. They can use this code to join.`;
        document.getElementById("shareJoinCode").textContent = code || "No join code";
        document.getElementById("whatsappShare").href = `https://wa.me/?text=${encodedMessage}`;
        document.getElementById("telegramShare").href = `https://t.me/share/url?url=${encodeURIComponent(currentUrl)}&text=${encodeURIComponent(inviteText)}`;
        document.getElementById("emailShare").href = `mailto:?subject=${encodeURIComponent(`Join ${tour.title}`)}&body=${encodedMessage}`;
        document.getElementById("smsShare").href = `sms:?body=${encodedMessage}`;

        document.getElementById("copyShareBtn").addEventListener("click", async () => {
            try {
                await copyShareText(message);
                setShareMessage("Invite copied. Paste it into any app.");
            } catch (_error) {
                setShareMessage("Unable to copy the invite.", "error");
            }
        });

        const moreAppsButton = document.getElementById("moreAppsBtn");
        const moreAppsPanel = document.getElementById("moreAppsPanel");
        const setMoreAppsOpen = (isOpen) => {
            moreAppsPanel.classList.toggle("hidden", !isOpen);
            moreAppsButton.setAttribute("aria-expanded", String(isOpen));
            document.body.classList.toggle("overflow-hidden", isOpen);
            if (isOpen) {
                document.getElementById("closeMoreAppsBtn").focus();
            } else {
                moreAppsButton.focus();
            }
        };

        moreAppsButton.addEventListener("click", () => {
            setMoreAppsOpen(moreAppsPanel.classList.contains("hidden"));
        });

        document.getElementById("closeMoreAppsBtn").addEventListener("click", () => {
            setMoreAppsOpen(false);
        });

        document.getElementById("moreAppsBackdrop").addEventListener("click", () => {
            setMoreAppsOpen(false);
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && !moreAppsPanel.classList.contains("hidden")) {
                setMoreAppsOpen(false);
            }
        });

        document.querySelectorAll(".shareAppBtn").forEach((button) => {
            button.addEventListener("click", async () => {
                const appName = button.dataset.shareApp;
                window.open(button.dataset.targetUrl, "_blank", "noopener,noreferrer");
                setMoreAppsOpen(false);
                try {
                    await copyShareText(message);
                    setShareMessage(`Invite copied. Paste it into ${appName} to share it.`);
                } catch (_error) {
                    setShareMessage(`Open ${appName} and share the join code shown above.`, "error");
                }
            });
        });

        document.getElementById("nativeShareBtn").addEventListener("click", async () => {
            if (!navigator.share) {
                try {
                    await copyShareText(message);
                    setShareMessage("Your browser does not support device sharing, so the invite was copied.");
                } catch (_error) {
                    setShareMessage("Unable to copy the invite.", "error");
                }
                setMoreAppsOpen(false);
                return;
            }
            try {
                await navigator.share({ title: `Join ${tour.title}`, text: message });
            } catch (error) {
                if (error.name !== "AbortError") setShareMessage("Unable to open the share menu.", "error");
            }
            setMoreAppsOpen(false);
        });

        document.getElementById("shareLoading").classList.add("hidden");
        document.getElementById("shareContent").classList.remove("hidden");
    } catch (error) {
        showShareError(error.message || "Unable to load share options.");
    }
});
