function stripeAuthHeaders() {
    const token = localStorage.getItem("access_token");
    return token ? { Authorization: `Bearer ${token}` } : {};
}

async function loadStripePaymentStatus() {
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get("session_id");
    const loading = document.getElementById("paymentLoading");
    const result = document.getElementById("paymentResult");

    if (!sessionId) {
        loading.textContent = "No payment session was provided.";
        return;
    }

    try {
        const response = await fetch(`/api/payments/status/?session_id=${encodeURIComponent(sessionId)}`, {
            headers: stripeAuthHeaders(),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.message || "Payment status unavailable.");

        const isPaid = data.status === "paid";
        document.getElementById("paymentIcon").textContent = isPaid ? "✓" : "!";
        document.getElementById("paymentTitle").textContent = isPaid ? "Payment successful" : "Payment received, awaiting verification";
        document.getElementById("paymentMessage").textContent = isPaid
            ? "Django verified this Stripe payment."
            : "Stripe returned you successfully, but Django has not confirmed the payment yet. Please refresh shortly.";
        document.getElementById("paymentAmount").textContent = `${data.currency.toUpperCase()} ${data.amount}`;
        document.getElementById("paymentStatus").textContent = data.status;
        document.getElementById("paymentReference").textContent = data.transaction_reference || "Pending webhook";
        loading.classList.add("hidden");
        result.classList.remove("hidden");
    } catch (error) {
        loading.textContent = error.message;
    }
}

document.addEventListener("DOMContentLoaded", loadStripePaymentStatus);
