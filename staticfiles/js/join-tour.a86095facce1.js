function joinAccessToken() {
    return localStorage.getItem("access_token");
}

function showJoinMessage(message, type) {
    const element = document.getElementById("joinMessage");
    element.textContent = message;
    element.className = `mb-5 rounded-xl px-4 py-3 text-sm ${type === "success" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`;
}

document.addEventListener("DOMContentLoaded", () => {
    if (!joinAccessToken()) {
        window.location.href = "/login/";
        return;
    }

    document.getElementById("joinTourForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        const button = document.getElementById("joinTourButton");
        const joinCode = document.getElementById("joinCode").value.trim();

        if (!joinCode) {
            showJoinMessage("Join code is required.", "error");
            return;
        }

        button.disabled = true;
        button.textContent = "Joining...";

        try {
            const response = await fetch("/api/tours/join/", {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${joinAccessToken()}`,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ join_code: joinCode }),
            });
            const data = await response.json().catch(() => ({}));

            if (response.status === 401) {
                window.location.href = "/login/";
                return;
            }

            if (!response.ok) {
                showJoinMessage(data.detail || "Unable to join this tour.", "error");
                return;
            }

            showJoinMessage("Tour joined successfully. Redirecting to your dashboard...", "success");
            window.setTimeout(() => { window.location.href = "/dashboard/"; }, 700);
        } catch (error) {
            showJoinMessage("Unable to connect to the server. Please try again.", "error");
        } finally {
            button.disabled = false;
            button.textContent = "Join tour";
        }
    });
});
