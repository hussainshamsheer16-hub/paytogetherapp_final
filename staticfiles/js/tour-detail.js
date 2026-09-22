let tourId = null;

let currentTour = null;
let currentUserId = null;
let tourMembers = [];

document.addEventListener(
    "DOMContentLoaded",
    function () {

        checkAuthentication();

        getTourIdFromUrl();

        setupButtons();

        loadTourDetails();

        loadCurrentUser();

        loadMembers();

        loadExpenses();

        loadReport();

        setupExpenseModal();

        setupSettlementPaymentModal();

    }
);


function getTourIdFromUrl() {

    const pathParts =
        window.location.pathname
            .split("/")
            .filter(Boolean);


    tourId =
        pathParts[pathParts.length - 1];


    if (!tourId) {

        showMessage(
            "Invalid tour ID.",
            "error"
        );

    }

}

async function loadTourDetails() {

    if (!tourId) {

        return;

    }


    const token =
        localStorage.getItem(
            "access_token"
        );


    try {

        const response =
            await fetch(
                `/api/tours/${tourId}/`,
                {

                    method: "GET",

                    headers: {

                        "Authorization":
                            `Bearer ${token}`

                    }

                }
            );


        if (response.status === 401) {

            handleUnauthorized();

            return;

        }


        if (response.status === 404) {

            showErrorState(
                "Tour not found or you do not have permission to view it."
            );

            return;

        }


        if (!response.ok) {

            showErrorState(
                "Unable to load tour details."
            );

            return;

        }


        const data =
            await response.json();


        currentTour = data;


        displayTourDetails(
            data
        );

    }

    catch (error) {

        console.error(
            "Error loading tour details:",
            error
        );


        showErrorState(
            "Unable to connect to the server."
        );

    }

}


function displayTourDetails(tour) {

    document.getElementById(
        "loadingState"
    ).classList.add(
        "hidden"
    );


    document.getElementById(
        "tourDetailsContainer"
    ).classList.remove(
        "hidden"
    );


    document.getElementById(
        "tourTitle"
    ).textContent =
        tour.title || "-";


    document.getElementById(
        "tourLocation"
    ).textContent =
        tour.destination || "Destination not set";


    document.getElementById(
        "tourDestination"
    ).textContent =
        tour.destination || "-";


    document.getElementById(
        "tourDuration"
    ).textContent =
        formatDuration(tour);


    document.getElementById(
        "tourPrice"
    ).textContent =
        formatPrice(tour.budget);


    document.getElementById(
        "tourStartDate"
    ).textContent =
        formatDate(tour.start_date);


    document.getElementById(
        "tourEndDate"
    ).textContent =
        formatDate(tour.end_date);


    document.getElementById(
        "tourDescription"
    ).textContent =
        tour.description ||
        "No description available.";


    displayTourStatus(
        tour.status
    );


    updateActionLinks(
        tour.id
    );

    document.getElementById("tourJoinCode").textContent = tour.join_code || "-";
    setupShareActions(tour);

    displayTourImage(tour);

}

function setupShareActions(tour) {
    document.getElementById("copyJoinCodeBtn").onclick = async function () {
        try {
            await copyText(tour.join_code || "");
            showMessage("Join code copied.", "success");
        } catch (error) {
            showMessage("Unable to copy the join code.", "error");
        }
    };

    document.getElementById("shareTourBtn").onclick = async function () {
        const text = `${tour.title} - join this tour with join code ${tour.join_code}.`;
        try {
            if (navigator.share) {
                await navigator.share({ title: tour.title, text });
            } else {
                await copyText(text);
                showMessage("Tour details copied. You can share them with your members.", "success");
            }
        } catch (error) {
            if (error.name !== "AbortError") {
                showMessage("Unable to share the tour details.", "error");
            }
        }
    };
}

async function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return;
    }

    const input = document.createElement("textarea");
    input.value = text;
    input.style.position = "fixed";
    input.style.opacity = "0";
    document.body.appendChild(input);
    input.focus();
    input.select();
    const copied = document.execCommand("copy");
    input.remove();
    if (!copied) throw new Error("Copy failed");
}

function displayTourImage(tour) {

    const container =
        document.getElementById(
            "tourImageContainer"
        );

    const image=document.getElementById(
        "tourImage"
    );

    if (tour.image) {

        image.src = tour.image;
        
        image.alt = tour.title || "Tour Image";

        container.classList.remove(
            "hidden"
        );

    } else {

        container.classList.add(
            "hidden"
        );

    }

}


function formatDuration(tour) {

    if (
        !tour.start_date ||
        !tour.end_date
    ) {

        return "-";

    }


    const startDate =
        new Date(tour.start_date);


    const endDate =
        new Date(tour.end_date);


    const difference =
        endDate - startDate;


    const days =
        Math.ceil(
            difference /
            (1000 * 60 * 60 * 24)
        ) + 1;


    return `${days} Days`;

}

function formatPrice(price) {

    if (
        price === null ||
        price === undefined ||
        price === ""
    ) {

        return "-";

    }


    return new Intl.NumberFormat(
        "en-PK",
        {

            style: "currency",

            currency: "PKR",

            maximumFractionDigits: 0

        }
    ).format(price);

}

function formatDate(dateValue) {

    if (!dateValue) {

        return "-";

    }


    const date =
        new Date(dateValue);


    return date.toLocaleDateString(
        "en-PK",
        {

            day: "numeric",

            month: "long",

            year: "numeric"

        }
    );

}

function displayTourStatus(status) {

    const statusElement =
        document.getElementById(
            "tourStatus"
        );


    statusElement.className =
        "inline-block mt-2 px-3 py-1 rounded-full text-sm font-semibold";


    const statusText =
        status
            ? status.charAt(0).toUpperCase() +
              status.slice(1)
            : "Unknown";


    statusElement.textContent =
        statusText;


    if (status === "upcoming") {

        statusElement.classList.add(
            "bg-blue-100",
            "text-blue-700"
        );

    }

    else if (status === "ongoing") {

        statusElement.classList.add(
            "bg-green-100",
            "text-green-700"
        );

    }

    else if (status === "completed") {

        statusElement.classList.add(
            "bg-gray-200",
            "text-gray-700"
        );

    }

    else if (status === "cancelled") {

        statusElement.classList.add(
            "bg-red-100",
            "text-red-700"
        );

    }

    else {

        statusElement.classList.add(
            "bg-yellow-100",
            "text-yellow-700"
        );

    }

}

function updateActionLinks(tourId) {

    const editUrl =
        `/tours/edit/${tourId}/`;


    document.getElementById(
        "editTourBtn"
    ).href =
        editUrl;


    document.getElementById(
        "bottomEditTourBtn"
    ).href =
        editUrl;

}

function setupButtons() {

    const deleteButton =
        document.getElementById(
            "deleteTourBtn"
        );


    deleteButton.addEventListener(
        "click",
        openDeleteModal
    );


    setupDeleteModal();

}

function setupDeleteModal() {

    document.getElementById(
        "confirmDeleteBtn"
    ).addEventListener(
        "click",
        deleteTour
    );


    document.getElementById(
        "cancelDeleteBtn"
    ).addEventListener(
        "click",
        closeDeleteModal
    );


    document.getElementById(
        "closeDeleteModalBtn"
    ).addEventListener(
        "click",
        closeDeleteModal
    );


    document.getElementById(
        "deleteModalOverlay"
    ).addEventListener(
        "click",
        closeDeleteModal
    );

}

function openDeleteModal() {

    const tourTitle =
        currentTour?.title ||
        "this tour";


    document.getElementById(
        "deleteModalMessage"
    ).textContent =
        `Are you sure you want to delete "${tourTitle}"?`;


    document.getElementById(
        "deleteModal"
    ).classList.remove(
        "hidden"
    );


    document.body.classList.add(
        "overflow-hidden"
    );

}

function closeDeleteModal() {

    document.getElementById(
        "deleteModal"
    ).classList.add(
        "hidden"
    );


    document.body.classList.remove(
        "overflow-hidden"
    );

}

async function deleteTour() {

    if (!tourId) {

        return;

    }


    const token =
        localStorage.getItem(
            "access_token"
        );


    const confirmButton =
        document.getElementById(
            "confirmDeleteBtn"
        );


    const originalText =
        confirmButton.textContent;


    confirmButton.disabled = true;

    confirmButton.textContent =
        "Deleting...";


    try {

        const response =
            await fetch(
                `/api/tours/${tourId}/`,
                {

                    method: "DELETE",

                    headers: {

                        "Authorization":
                            `Bearer ${token}`

                    }

                }
            );


        if (response.status === 401) {

            handleUnauthorized();

            return;

        }


        if (response.status === 404) {

            closeDeleteModal();


            showMessage(
                "Tour not found or you do not have permission to delete it.",
                "error"
            );

            return;

        }


        if (response.status === 204) {

            window.location.href =
                "/tours/";

            return;

        }


        showMessage(
            "Unable to delete the tour.",
            "error"
        );

    }

    catch (error) {

        console.error(
            "Error deleting tour:",
            error
        );


        showMessage(
            "Unable to connect to the server.",
            "error"
        );

    }

    finally {

        confirmButton.disabled = false;

        confirmButton.textContent =
            originalText;

    }

}

function showErrorState(message) {

    document.getElementById(
        "loadingState"
    ).classList.add(
        "hidden"
    );


    showMessage(
        message,
        "error"
    );

}

function showMessage(message, type) {

    const messageArea =
        document.getElementById(
            "messageArea"
        );


    const styles = {

        success:
            "bg-green-100 border border-green-300 text-green-700",

        error:
            "bg-red-100 border border-red-300 text-red-700"

    };


    messageArea.innerHTML = `

        <div
            class="${styles[type] || styles.error} px-5 py-4 rounded-lg">

            ${escapeHtml(message)}

        </div>

    `;


    window.scrollTo({

        top: 0,

        behavior: "smooth"

    });

}

function escapeHtml(value) {

    const div =
        document.createElement("div");


    div.textContent =
        String(value ?? "");


    return div.innerHTML;

}

function checkAuthentication() {

    const token =
        localStorage.getItem(
            "access_token"
        );


    if (!token) {

        window.location.href =
            "/login/";

    }

}

function handleUnauthorized() {

    localStorage.removeItem(
        "access_token"
    );


    localStorage.removeItem(
        "refresh_token"
    );


    window.location.href =
        "/login/";

}

/* =========================================================
   Members / Expenses / Report
========================================================= */

function authHeaders(extra) {
    const token = localStorage.getItem("access_token");
    return Object.assign(
        { "Authorization": `Bearer ${token}` },
        extra || {}
    );
}

async function refreshAccessToken() {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) return false;

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
}

async function fetchWithAuthRefresh(url, options) {
    let response = await fetch(url, options);
    if (response.status !== 401) return response;

    const refreshed = await refreshAccessToken();
    if (!refreshed) {
        handleUnauthorized();
        return response;
    }

    const retryHeaders = { ...(options.headers || {}) };
    delete retryHeaders.Authorization;
    const retryOptions = {
        ...options,
        headers: authHeaders(retryHeaders),
    };
    return fetch(url, retryOptions);
}

async function loadCurrentUser() {
    try {
        const response = await fetch("/api/profile/", {
            headers: authHeaders(),
        });
        if (response.status === 401) {
            handleUnauthorized();
            return;
        }
        const data = await response.json();
        currentUserId = data.id;
        const accountButton = document.getElementById("editTourBtn");
        if (accountButton) {
            const accountName = (data.full_name || data.username || data.email || "Account").trim();
            accountButton.textContent = accountName.split(/\s+/)[0] || "Account";
            accountButton.title = data.full_name || data.username || data.email || "Account";
        }
        renderExpenseActions();
    } catch (error) {
        console.error("Error loading current user:", error);
    }
}

async function loadMembers() {
    if (!tourId) return;
    const container = document.getElementById("membersList");

    try {
        const response = await fetch(`/api/tours/${tourId}/members/`, {
            headers: authHeaders(),
        });

        if (response.status === 401) {
            handleUnauthorized();
            return;
        }

        if (!response.ok) {
            container.innerHTML = `<p class="text-sm text-gray-400">Unable to load members.</p>`;
            return;
        }

        tourMembers = await response.json();
        renderMembers();
        populatePaidBySelect();
    } catch (error) {
        console.error("Error loading members:", error);
        container.innerHTML = `<p class="text-sm text-gray-400">Unable to load members.</p>`;
    }
}

function renderMembers() {
    const container = document.getElementById("membersList");
    if (!tourMembers.length) {
        container.innerHTML = `<p class="text-sm text-gray-400">No members yet.</p>`;
        return;
    }

    container.innerHTML = tourMembers.map((member) => {
        const name = escapeHtml(member.user.name || member.user.email);
        const initial = escapeHtml((member.user.name || member.user.email || "?").charAt(0).toUpperCase());
        const isCreator = member.role === "creator";
        return `
            <div class="flex items-center gap-2.5 rounded-full border border-gray-200 bg-white pl-1 pr-4 py-1 shadow-sm">
                <span class="flex h-8 w-8 items-center justify-center rounded-full ${isCreator ? "bg-brand-600" : "bg-gray-400"} text-sm font-bold text-white">${initial}</span>
                <span class="text-sm font-semibold text-gray-800">${name}</span>
                ${isCreator ? `<span class="rounded-full bg-brand-100 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide text-brand-700">Creator</span>` : ""}
            </div>
        `;
    }).join("");
}

function populatePaidBySelect() {
    const select = document.getElementById("expensePaidBy");
    if (!select) return;

    if (!tourMembers.length) {
        select.innerHTML = `<option value="">Loading members...</option>`;
        select.disabled = true;
        return;
    }

    select.innerHTML = tourMembers.map((member) => (
        `<option value="${member.user.id}">${escapeHtml(member.user.name || member.user.email)}</option>`
    )).join("");
    select.disabled = false;

    if (currentUserId) {
        select.value = String(currentUserId);
    }
}

async function loadExpenses() {
    if (!tourId) return;

    try {
        const response = await fetch(`/api/tours/${tourId}/expenses/`, {
            headers: authHeaders(),
        });

        if (response.status === 401) {
            handleUnauthorized();
            return;
        }

        if (!response.ok) return;

        const data = await response.json();
        const expenses = data.results || data;
        renderExpenses(expenses);
    } catch (error) {
        console.error("Error loading expenses:", error);
    }
}

const CATEGORY_STYLES = {
    food: "bg-amber-100 text-amber-700",
    travel: "bg-sky-100 text-sky-700",
    hotel: "bg-violet-100 text-violet-700",
    other: "bg-gray-100 text-gray-700",
};

function renderExpenses(expenses) {
    const emptyState = document.getElementById("expensesEmpty");
    const tableWrap = document.getElementById("expensesTableWrap");
    const tbody = document.getElementById("expensesTableBody");

    if (!expenses.length) {
        emptyState.classList.remove("hidden");
        tableWrap.classList.add("hidden");
        return;
    }

    emptyState.classList.add("hidden");
    tableWrap.classList.remove("hidden");

    tbody.innerHTML = expenses.map((expense) => {
        const canManage = currentUserId && (
            expense.added_by === currentUserId || (currentTour && currentTour.created_by === currentUserId)
        );
        const badgeClass = CATEGORY_STYLES[expense.category] || CATEGORY_STYLES.other;

        return `
            <tr data-expense-id="${expense.id}">
                <td class="px-4 py-3">
                    <span class="rounded-full px-2.5 py-1 text-xs font-bold ${badgeClass}">${escapeHtml(expense.category_display || expense.category)}</span>
                </td>
                <td class="px-4 py-3 text-gray-700">${escapeHtml(expense.description || "-")}</td>
                <td class="px-4 py-3 text-gray-700">${escapeHtml(expense.paid_by_name || "-")}</td>
                <td class="px-4 py-3 text-right font-semibold text-gray-900">Rs ${formatAmountValue(expense.amount)}</td>
                <td class="px-4 py-3 text-right">
                    ${canManage ? `
                        <button type="button" class="edit-expense-btn text-brand-600 hover:text-brand-800 font-semibold text-xs mr-3" data-id="${expense.id}">Edit</button>
                        <button type="button" class="delete-expense-btn text-red-600 hover:text-red-800 font-semibold text-xs" data-id="${expense.id}">Delete</button>
                    ` : `<span class="text-xs text-gray-300">&mdash;</span>`}
                </td>
            </tr>
        `;
    }).join("");

    tbody.querySelectorAll(".edit-expense-btn").forEach((btn) => {
        btn.addEventListener("click", () => openExpenseModal(
            expenses.find((expense) => String(expense.id) === btn.dataset.id)
        ));
    });

    tbody.querySelectorAll(".delete-expense-btn").forEach((btn) => {
        btn.addEventListener("click", () => deleteExpense(btn.dataset.id));
    });
}

function renderExpenseActions() {
    // Re-render the expenses table now that we know who "we" are, so
    // edit/delete controls show up for expenses the user is allowed to manage.
    loadExpenses();
}

function formatAmountValue(value) {
    const number = parseFloat(value || 0);
    return number.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

async function deleteExpense(expenseId) {
    if (!window.confirm("Delete this expense? This cannot be undone.")) {
        return;
    }

    try {
        const response = await fetch(`/api/tours/${tourId}/expenses/${expenseId}/`, {
            method: "DELETE",
            headers: authHeaders(),
        });

        if (response.status === 401) {
            handleUnauthorized();
            return;
        }

        if (response.status === 204 || response.ok) {
            showMessage("Expense deleted.", "success");
            loadExpenses();
            loadReport();
        } else {
            showMessage("Unable to delete this expense.", "error");
        }
    } catch (error) {
        console.error("Error deleting expense:", error);
        showMessage("Unable to connect to the server.", "error");
    }
}

/* ---------------- Expense modal ---------------- */

function setupExpenseModal() {
    document.getElementById("addExpenseBtn").addEventListener("click", () => openExpenseModal(null));
    document.getElementById("closeExpenseModalBtn").addEventListener("click", closeExpenseModal);
    document.getElementById("cancelExpenseBtn").addEventListener("click", closeExpenseModal);
    document.getElementById("expenseModalOverlay").addEventListener("click", closeExpenseModal);
    document.getElementById("expenseForm").addEventListener("submit", submitExpenseForm);
}

function openExpenseModal(expense) {
    const modal = document.getElementById("expenseModal");
    const title = document.getElementById("expenseModalTitle");
    const messageBox = document.getElementById("expenseModalMessage");

    messageBox.classList.add("hidden");
    document.getElementById("expenseForm").reset();

    if (expense) {
        title.textContent = "Edit Expense";
        document.getElementById("expenseId").value = expense.id;
        document.getElementById("expenseAmount").value = expense.amount;
        document.getElementById("expenseCategory").value = expense.category;
        document.getElementById("expenseDescription").value = expense.description || "";
        populatePaidBySelect();
        document.getElementById("expensePaidBy").value = String(expense.paid_by);
    } else {
        title.textContent = "Add Expense";
        document.getElementById("expenseId").value = "";
        populatePaidBySelect();
    }

    modal.classList.remove("hidden");
}

function closeExpenseModal() {
    document.getElementById("expenseModal").classList.add("hidden");
}

async function submitExpenseForm(event) {
    event.preventDefault();

    const expenseId = document.getElementById("expenseId").value;
    const paidById = Number.parseInt(document.getElementById("expensePaidBy").value, 10);

    if (!Number.isInteger(paidById)) {
        showExpenseModalError({ detail: "Please wait for the tour members to load before saving." });
        return;
    }

    const payload = {
        amount: document.getElementById("expenseAmount").value,
        category: document.getElementById("expenseCategory").value,
        paid_by: paidById,
        description: document.getElementById("expenseDescription").value.trim(),
    };

    const isEdit = Boolean(expenseId);
    const url = isEdit
        ? `/api/tours/${tourId}/expenses/${expenseId}/`
        : `/api/tours/${tourId}/expenses/`;

    const saveButton = document.getElementById("saveExpenseBtn");
    saveButton.disabled = true;
    saveButton.textContent = "Saving...";

    try {
        const response = await fetch(url, {
            method: isEdit ? "PATCH" : "POST",
            headers: authHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify(payload),
        });

        if (response.status === 401) {
            handleUnauthorized();
            return;
        }

        const data = await response.json().catch(() => ({}));

        if (response.ok) {
            closeExpenseModal();
            showMessage(isEdit ? "Expense updated." : "Expense added.", "success");
            loadExpenses();
            loadReport();
        } else {
            showExpenseModalError(data);
        }
    } catch (error) {
        console.error("Error saving expense:", error);
        showExpenseModalError({ detail: "Unable to connect to the server." });
    } finally {
        saveButton.disabled = false;
        saveButton.textContent = "Save expense";
    }
}

function showExpenseModalError(data) {
    const messageBox = document.getElementById("expenseModalMessage");
    let text = data.detail || data.message;

    if (!text && typeof data === "object") {
        const [field, messages] = Object.entries(data)[0] || [];
        if (field) {
            const message = Array.isArray(messages) ? messages[0] : messages;
            text = `${field.replace(/_/g, " ")}: ${message}`;
        }
    }

    messageBox.textContent = text || "Unable to save this expense.";
    messageBox.className = "mb-4 rounded-lg px-4 py-3 text-sm bg-red-50 border border-red-200 text-red-700";
    messageBox.classList.remove("hidden");
}

/* ---------------- Report ---------------- */

async function loadReport() {
    if (!tourId) return;

    try {
        const response = await fetch(`/api/tours/${tourId}/report/`, {
            headers: authHeaders(),
        });

        if (response.status === 401) {
            handleUnauthorized();
            return;
        }

        if (!response.ok) return;

        const report = await response.json();
        renderReport(report);
    } catch (error) {
        console.error("Error loading report:", error);
    }
}

function renderReport(report) {
    document.getElementById("reportTotal").textContent = `Rs ${formatAmountValue(report.total_expense)}`;
    document.getElementById("reportMemberCount").textContent = report.member_count;
    document.getElementById("reportSharePerMember").textContent = `Rs ${formatAmountValue(report.share_per_member)}`;

    const tbody = document.getElementById("reportMembersBody");
    tbody.innerHTML = report.members.map((member) => {
        const balance = parseFloat(member.balance);
        const balanceClass = balance > 0 ? "text-credit-600" : (balance < 0 ? "text-debit-600" : "text-gray-500");
        const balanceLabel = balance > 0
            ? `+Rs ${formatAmountValue(balance)} (gets back)`
            : balance < 0
                ? `-Rs ${formatAmountValue(Math.abs(balance))} (owes)`
                : "Settled";

        return `
            <tr>
                <td class="px-4 py-3 font-semibold text-gray-800">${escapeHtml(member.name)}</td>
                <td class="px-4 py-3 text-right text-gray-700">Rs ${formatAmountValue(member.paid)}</td>
                <td class="px-4 py-3 text-right text-gray-700">Rs ${formatAmountValue(member.share)}</td>
                <td class="px-4 py-3 text-right font-semibold ${balanceClass}">${balanceLabel}</td>
            </tr>
        `;
    }).join("");

    const settlementsList = document.getElementById("settlementsList");
    if (!report.settlements.length) {
        settlementsList.innerHTML = `<p class="text-sm text-gray-400">Everyone is settled up. Nothing to pay.</p>`;
        return;
    }

    settlementsList.innerHTML = report.settlements.map((settlement) => {
        const isPaid = settlement.status === "paid" || settlement.status === "received";
        const isPending = settlement.status === "pending";
        const isNotReceived = settlement.status === "not_received";
        const canPay = !isPaid && !isPending && Number(settlement.from_id) === Number(currentUserId);
        const canApprove = isPending && Number(settlement.to_id) === Number(currentUserId);
        const statusLabel = isPaid ? "Paid" : (isNotReceived ? "Unpaid" : (isPending ? "Awaiting confirmation" : "Unpaid"));
        const statusClass = isPaid
            ? "bg-green-100 text-green-700"
            : (isNotReceived ? "bg-red-100 text-red-700" : (isPending ? "bg-sky-100 text-sky-700" : "bg-amber-100 text-amber-700"));
        return `
            <div class="flex flex-col gap-3 rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                <p class="text-sm text-gray-700">
                    <span class="font-semibold text-gray-900">${escapeHtml(settlement.from)}</span>
                    pays
                    <span class="font-semibold text-gray-900">${escapeHtml(settlement.to)}</span>
                    ${canApprove ? `<span class="mt-1 block text-xs font-semibold text-sky-700">A payment was sent. Please confirm whether it was received.</span>` : ""}
                </p>
                <div class="flex items-center gap-3">
                    <p class="text-sm font-bold text-brand-700">Rs ${formatAmountValue(settlement.amount)}</p>
                    <span class="rounded-full px-2.5 py-1 text-xs font-bold ${statusClass}">${statusLabel}</span>
                    ${canPay && !isPending ? `<button type="button" class="pay-settlement-btn rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-brand-700" data-to-id="${settlement.to_id}" data-amount="${settlement.amount}">Pay</button>` : ""}
                    ${canApprove ? `
                        <div class="flex items-center gap-2">
                            <button type="button" class="approve-settlement-btn rounded-lg bg-green-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-green-700" data-payment-id="${settlement.payment_id}" data-decision="received">Received</button>
                            <button type="button" class="approve-settlement-btn rounded-lg bg-red-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-red-700" data-payment-id="${settlement.payment_id}" data-decision="not_confirmed">Not confirmed</button>
                        </div>
                    ` : ""}
                </div>
            </div>
        `;
    }).join("");

    settlementsList.querySelectorAll(".pay-settlement-btn").forEach((button) => {
        button.addEventListener("click", () => openSettlementPaymentModal(button.dataset));
    });
    settlementsList.querySelectorAll(".approve-settlement-btn").forEach((button) => {
        button.addEventListener("click", () => approveSettlementPayment(button));
    });
}

function setupSettlementPaymentModal() {
    document.getElementById("closeSettlementPaymentModalBtn").addEventListener("click", closeSettlementPaymentModal);
    document.getElementById("cancelSettlementPaymentBtn").addEventListener("click", closeSettlementPaymentModal);
    document.getElementById("settlementPaymentOverlay").addEventListener("click", closeSettlementPaymentModal);
    document.getElementById("settlementPaymentForm").addEventListener("submit", submitSettlementPayment);
    document.getElementById("settlementPaymentMethod").addEventListener("change", updateSettlementPaymentMethod);
}

function openSettlementPaymentModal(data) {
    document.getElementById("settlementPaymentToId").value = data.toId;
    document.getElementById("settlementPaymentAmount").value = data.amount;
    document.getElementById("settlementPaymentAmountLabel").textContent = `Rs ${formatAmountValue(data.amount)}`;
    document.getElementById("settlementPaymentMethod").value = "cod";
    updateSettlementPaymentMethod();
    document.getElementById("settlementPaymentModal").classList.remove("hidden");
}

function updateSettlementPaymentMethod() {
    const isCard = document.getElementById("settlementPaymentMethod").value === "card";
    document.getElementById("settlementPaymentMethodHint").textContent = isCard
        ? "You will continue to Stripe's secure checkout page to enter card details and confirm payment."
        : "The recipient will approve this cash payment.";
    document.getElementById("confirmSettlementPaymentBtn").textContent = isCard
        ? "Continue to secure card payment"
        : "Confirm cash payment";
}

function closeSettlementPaymentModal() {
    document.getElementById("settlementPaymentModal").classList.add("hidden");
}

async function submitSettlementPayment(event) {
    event.preventDefault();
    const button = document.getElementById("confirmSettlementPaymentBtn");
    const paymentMethod = document.getElementById("settlementPaymentMethod").value;
    button.disabled = true;
    button.textContent = paymentMethod === "card" ? "Creating secure checkout..." : "Processing...";

    try {
        if (paymentMethod === "card") {
            const stripeResponse = await fetchWithAuthRefresh("/api/payments/create-checkout-session/", {
                method: "POST",
                headers: authHeaders({ "Content-Type": "application/json" }),
                body: JSON.stringify({
                    tour_id: Number(tourId),
                    to_id: Number(document.getElementById("settlementPaymentToId").value),
                }),
            });
            const stripeData = await stripeResponse.json().catch(() => ({}));
            if (!stripeResponse.ok || !stripeData.checkout_url) {
                throw new Error(stripeData.message || "Unable to create secure checkout.");
            }
            window.location.href = stripeData.checkout_url;
            return;
        }

        const response = await fetch(`/api/tours/${tourId}/settlements/pay/`, {
            method: "POST",
            headers: authHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify({
                to_id: Number(document.getElementById("settlementPaymentToId").value),
                amount: document.getElementById("settlementPaymentAmount").value,
                payment_method: paymentMethod,
            }),
        });
        const data = await response.json().catch(() => ({}));
        if (response.ok) {
            closeSettlementPaymentModal();
            showMessage("Payment request sent. Waiting for recipient approval.", "success");
            loadReport();
        } else {
            showMessage(data.detail || "Unable to process payment.", "error");
        }
    } catch (error) {
        console.error("Error processing settlement payment:", error);
        showMessage(error.message || "Unable to connect to the server.", "error");
    } finally {
        button.disabled = false;
        button.textContent = "Confirm payment";
    }
}

async function approveSettlementPayment(button) {
    const decision = button.dataset.decision || "received";
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = decision === "received" ? "Confirming..." : "Updating...";

    try {
        const response = await fetch(
            `/api/tours/${tourId}/settlements/${button.dataset.paymentId}/approve/`,
            {
                method: "POST",
                headers: authHeaders({ "Content-Type": "application/json" }),
                body: JSON.stringify({ decision }),
            },
        );
        const data = await response.json().catch(() => ({}));
        if (response.ok) {
            showMessage(
                decision === "received"
                    ? "Payment marked as received."
                    : "Payment marked as not confirmed.",
                "success",
            );
            loadReport();
        } else {
            showMessage(data.detail || "Unable to update payment status.", "error");
            button.disabled = false;
            button.textContent = originalText;
        }
    } catch (error) {
        console.error("Error updating settlement payment status:", error);
        showMessage("Unable to connect to the server.", "error");
        button.disabled = false;
        button.textContent = originalText;
    }
}
