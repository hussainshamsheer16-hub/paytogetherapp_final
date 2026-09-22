const registerForm = document.getElementById("registerForm");
const messagebox = document.getElementById("messagebox");

if (registerForm && messagebox) {
    registerForm.addEventListener("submit", registerUser);
}

async function registerUser(event) {
    event.preventDefault();

    messagebox.innerHTML = "";

    const username = document.getElementById("id_username")?.value?.trim() || "";
    const fullName = document.getElementById("id_full_name")?.value?.trim() || "";
    const email = document.getElementById("id_email")?.value?.trim() || "";
    const phoneNumber = document.getElementById("id_phone_number")?.value?.trim() || "";
    const password = document.getElementById("id_password1")?.value || "";
    const confirmPassword = document.getElementById("id_password2")?.value || "";

    if (!fullName || !username || !email || !password || !confirmPassword) {
        showmessage("Please fill in all fields", "red");
        return;
    }

    if (password !== confirmPassword) {
        showmessage("Passwords do not match", "red");
        return;
    }

    try {
        const response = await fetch("/api/register/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                full_name: fullName,
                username,
                email,
                phone_number: phoneNumber,
                password,
                confirm_password: confirmPassword
            })
        });

        let data = {};
        try {
            data = await response.json();
        } catch (error) {
            data = {};
        }

        if (response.ok) {
            showmessage("Registration successful! Redirecting to login page...", "green");
            setTimeout(() => {
                window.location.href = "/login/";
            }, 1500);
        } else {
            const errorMessage = getErrorMessage(data);
            showmessage(errorMessage, "red");
        }
    } catch (error) {
        showmessage("Server error. Please try again later.", "red");
        console.error(error);
    }
}

function getErrorMessage(data) {
    if (data.errors && typeof data.errors === "object") {
        const [field, messages] = Object.entries(data.errors)[0] || [];
        if (field && messages) {
            const label = field.replace(/_/g, " ");
            const message = Array.isArray(messages) ? messages[0] : messages;
            return `${label.charAt(0).toUpperCase()}${label.slice(1)}: ${message}`;
        }
    }

    return data.detail || data.message || data.error || "Registration failed";
}

function showmessage(message, color) {
    const cls = color === "green"
        ? "rounded-xl border border-credit-500/30 bg-credit-50 px-4 py-3 text-sm font-medium text-credit-600"
        : "rounded-xl border border-debit-500/30 bg-debit-50 px-4 py-3 text-sm font-medium text-debit-600";
    messagebox.innerHTML = `<div class="${cls}">${message}</div>`;
}

function displayError(message) {
    messagebox.innerHTML = `<div style="color: red;">${message}</div>`;
}
