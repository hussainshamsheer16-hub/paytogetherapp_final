let currentSearch = "";

let searchTimeout = null;

let currentPage = 1;

let totalTours = 0;

const toursPerPage = 5;

let selectedTourId = null;

let selectedTourTitle = "";


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


async function authenticatedFetch(url, options = {}) {
    const sendRequest = () => fetch(url, {
        ...options,
        headers: {
            ...(options.headers || {}),
            "Authorization": `Bearer ${localStorage.getItem("access_token") || ""}`,
        },
    });

    let response = await sendRequest();
    if (response.status === 401 && await refreshAccessToken()) {
        response = await sendRequest();
    }

    if (response.status === 401) {
        handleUnauthorized();
    }
    return response;
}


document.addEventListener("DOMContentLoaded", function () {

    checkAuthentication();

    setupSearch();

    setupPagination();

    setupTourActions();

    setupDeleteModal();


});



function setupDeleteModal() {

    const confirmDeleteBtn = document.getElementById(
        "confirmDeleteBtn"
    );


    const cancelDeleteBtn = document.getElementById(
        "cancelDeleteBtn"
    );


    const closeDeleteModalBtn = document.getElementById(
        "closeDeleteModalBtn"
    );


    const deleteModalOverlay = document.getElementById(
        "deleteModalOverlay"
    );


    // Confirm deletion

    confirmDeleteBtn.addEventListener(
        "click",
        function () {

            deleteTour();

        }
    );


    // Cancel deletion

    cancelDeleteBtn.addEventListener(
        "click",
        closeDeleteModal
    );


    // Close button

    closeDeleteModalBtn.addEventListener(
        "click",
        closeDeleteModal
    );


    // Click outside modal

    deleteModalOverlay.addEventListener(
        "click",
        closeDeleteModal
    );

}

function openDeleteModal(tourId, tourTitle) {

    selectedTourId = tourId;

    selectedTourTitle = tourTitle;


    const deleteModal = document.getElementById(
        "deleteModal"
    );


    const deleteModalMessage = document.getElementById(
        "deleteModalMessage"
    );


    deleteModalMessage.textContent =
        `Are you sure you want to delete "${tourTitle}"?`;


    deleteModal.classList.remove(
        "hidden"
    );


    document.body.classList.add(
        "overflow-hidden"
    );

}

function closeDeleteModal() {

    const deleteModal = document.getElementById(
        "deleteModal"
    );


    deleteModal.classList.add(
        "hidden"
    );


    document.body.classList.remove(
        "overflow-hidden"
    );


    selectedTourId = null;

    selectedTourTitle = "";

}

async function deleteTour() {

    if (!selectedTourId) {

        return;

    }

    const tourIdToDelete =
        selectedTourId;


    const tourTitleToDelete =
        selectedTourTitle;


    const confirmDeleteBtn = document.getElementById(
        "confirmDeleteBtn"
    );


    const originalButtonText =
        confirmDeleteBtn.textContent;


    confirmDeleteBtn.disabled = true;

    confirmDeleteBtn.textContent =
        "Deleting...";


    try {

        const response = await authenticatedFetch(
            `/api/tours/${selectedTourId}/`,
            {

                method: "DELETE",

            }
        );


        // Token expired or invalid

        if (response.status === 401) {

            handleUnauthorized();

            return;

        }


        // Tour does not exist or user does not own it

        if (response.status === 404) {

            closeDeleteModal();


            showMessage(
                "Tour not found or you do not have permission to delete it.",
                "error"
            );


            loadTours();

            return;

        }


        // Successful deletion

        if (response.status === 204) {

            closeDeleteModal();


            showMessage(
                `"${tourTitleToDelete}" deleted successfully.`,
                "success"
            );


            handlePageAfterDeletion();

            return;

        }


        // Other server errors

        let data = null;


        try {

            data = await response.json();

        }

        catch {

            // No JSON response

        }


        showMessage(
            getApiErrorMessage(data),
            "error"
        );

    }

    catch (error) {

        console.error(
            "Error deleting tour:",
            error
        );


        showMessage(
            "Unable to delete the tour. Please try again.",
            "error"
        );

    }

    finally {

        confirmDeleteBtn.disabled = false;

        confirmDeleteBtn.textContent =
            originalButtonText;

    }

}

function handlePageAfterDeletion() {

    const totalPagesBeforeDeletion =
        Math.ceil(
            totalTours / toursPerPage
        );


    const totalToursAfterDeletion =
        totalTours - 1;


    const totalPagesAfterDeletion =
        Math.ceil(
            totalToursAfterDeletion /
            toursPerPage
        );


    if (
        currentPage > totalPagesAfterDeletion &&
        currentPage > 1
    ) {

        currentPage--;

    }


    totalTours =
        totalToursAfterDeletion;


    loadTours();

}

function setupTourActions() {

    const tableBody = document.getElementById(
        "tourTableBody"
    );


    tableBody.addEventListener(
        "click",
        function (event) {

            // Edit button

            const editButton =
                event.target.closest(".editTourBtn");


            if (editButton) {

                const tourId =
                    editButton.dataset.tourId;


                window.location.href =
                    `/tours/edit/${tourId}/`;

                return;

            }


            // Delete button

            const deleteButton =
                event.target.closest(".deleteTourBtn");


            if (deleteButton) {

                const tourId =
                    deleteButton.dataset.tourId;


                const tourTitle =
                    deleteButton.dataset.tourTitle;


                openDeleteModal(
                    tourId,
                    tourTitle
                );

                return;

            }

            const copyButton = event.target.closest(".copyJoinCodeBtn");
            if (copyButton) {
                copyJoinCode(copyButton.dataset.joinCode);
                return;
            }

            const shareButton = event.target.closest(".shareTourBtn");
            if (shareButton) {
                shareTour(
                    shareButton.dataset.tourTitle,
                    shareButton.dataset.tourId,
                    shareButton.dataset.joinCode
                );

            }

        }
    );

}

function setupSearch() {

    const searchForm = document.getElementById(
        "searchForm"
    );

    const searchInput = document.getElementById(
        "searchInput"
    );

    const clearSearchBtn = document.getElementById(
        "clearSearchBtn"
    );


    // Search when form is submitted

    searchForm.addEventListener(
        "submit",
        function (event) {

            event.preventDefault();

            clearTimeout(searchTimeout);

            currentSearch = searchInput.value.trim();

            currentPage = 1;

            loadTours();

        }
    );


    // Clear Search Button

    clearSearchBtn.addEventListener(
        "click",
        function () {

            clearTimeout(searchTimeout);

            searchInput.value = "";

            currentSearch = "";


            currentPage = 1;

            loadTours();

        }
    );


    // Live Search with Debounce

    searchInput.addEventListener(
        "input",
        function () {

            clearTimeout(searchTimeout);


            searchTimeout = setTimeout(
                function () {

                    currentSearch = searchInput.value.trim();

                    currentPage = 1;

                    loadTours();

                },
                500
            );

        }
    );

}


function checkAuthentication() {

    const token = localStorage.getItem("access_token");

    if (!token) {

        window.location.href = "/login/";

        return;

    }

    loadTours();

}

function renderTours(tours) {

    const tableBody = document.getElementById(
        "tourTableBody"
    );

    tableBody.innerHTML = "";

    tours.forEach(function (tour) {

        const row = `

            <tr class="group border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors">

                <td class="w-20 px-2 py-3 lg:w-40 lg:px-5 lg:py-4">
                    ${tour.image
                        ? `<div class="h-14 w-16 overflow-hidden rounded-lg border-2 border-white bg-slate-100 shadow-md ring-1 ring-slate-200 lg:h-20 lg:w-32 lg:rounded-xl lg:border-4"><img src="${tour.image}" alt="${escapeHtml(tour.title)}" class="h-full w-full object-cover transition duration-300 group-hover:scale-105"></div>`
                        : `<div class="flex h-14 w-16 items-center justify-center rounded-lg border-2 border-white bg-gradient-to-br from-slate-100 to-slate-200 text-[10px] font-semibold text-slate-400 shadow-sm ring-1 ring-slate-200 lg:h-20 lg:w-32 lg:rounded-xl lg:border-4 lg:text-xs">No image</div>`
                    }
                </td>

                <td class="px-3 py-3 text-center lg:px-5 lg:py-4">

                    <div class="mx-auto min-w-0 max-w-[280px] lg:min-w-[220px]">

                        <div class="break-words font-semibold text-slate-900 lg:truncate">

                            ${escapeHtml(tour.title)}

                        </div>

                        <div class="mt-1 hidden text-xs font-semibold uppercase tracking-wide text-blue-600 lg:block">
                            Code: ${escapeHtml(tour.join_code || "-")}
                        </div>

                        <div class="mt-1 line-clamp-2 text-sm text-slate-500 lg:truncate">

                            ${escapeHtml(
                                tour.description || "No description"
                            )}

                        </div>
                    </div>

                </td>

                <td class="hidden px-3 py-4 text-sm text-slate-700 lg:table-cell">

                    ${escapeHtml(tour.destination)}

                </td>

                <td class="hidden px-3 py-4 font-semibold text-slate-900 lg:table-cell">

                    ${formatCurrency(tour.budget)}

                </td>

                <td class="hidden px-3 py-4 text-sm text-slate-600 lg:table-cell">

                    <div class="font-medium text-slate-700">

                        ${formatDate(tour.start_date)}

                    </div>

                    <div class="text-slate-400 text-xs my-1">

                        through

                    </div>

                    <div class="font-medium text-slate-700">

                        ${formatDate(tour.end_date)}

                    </div>

                </td>

                <td class="hidden px-6 py-4 lg:table-cell">

                    ${getStatusBadge(tour.status)}

                </td>

                <td class="hidden px-3 py-4 lg:table-cell">

                    <div class="flex flex-wrap items-center gap-1.5">
                        <code class="rounded-md bg-blue-50 px-2 py-1 text-xs font-bold tracking-widest text-blue-700">${escapeHtml(tour.join_code || "-")}</code>
                        <button type="button" class="copyJoinCodeBtn rounded-md border border-slate-200 px-2 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-100" data-join-code="${escapeHtml(tour.join_code || "")}" title="Copy join code">Copy</button>
                        <button type="button" class="shareTourBtn rounded-md border border-slate-200 px-2 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-100" data-tour-id="${tour.id}" data-tour-title="${escapeHtml(tour.title)}" data-join-code="${escapeHtml(tour.join_code || "")}" title="Share tour">Share</button>
                    </div>

                </td>

                <td class="whitespace-nowrap px-1.5 py-3 text-center lg:px-3 lg:py-4">

                    <div class="flex flex-nowrap justify-center gap-1">
                    <a  href="/tours/${tour.id}/"
                        class="inline-flex items-center rounded-lg border border-slate-200 bg-white px-1.5 py-1.5 text-[11px] font-semibold text-slate-700 shadow-sm transition hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 lg:gap-1 lg:px-2.5 lg:py-2 lg:text-xs">

                        View

                    </a>
                    
                    <button
                        type="button"
                        class="editTourBtn inline-flex items-center rounded-lg border border-blue-100 bg-blue-50 px-1.5 py-1.5 text-[11px] font-semibold text-blue-700 shadow-sm transition hover:border-blue-200 hover:bg-blue-100 lg:gap-1 lg:px-2.5 lg:py-2 lg:text-xs"
                        data-tour-id="${tour.id}">

                        Edit

                    </button>

                    <button
                        type="button"
                        class="deleteTourBtn inline-flex items-center rounded-lg border border-red-100 bg-red-50 px-1.5 py-1.5 text-[11px] font-semibold text-red-700 shadow-sm transition hover:border-red-200 hover:bg-red-100 lg:gap-1 lg:px-2.5 lg:py-2 lg:text-xs"
                        data-tour-id="${tour.id}"
                        data-tour-title="${escapeHtml(tour.title)}">

                        Delete

                    </button>
                    </div>

                </td>

            </tr>

        `;

        tableBody.insertAdjacentHTML(
            "beforeend",
            row
        );

    });

}

async function copyJoinCode(joinCode) {
    if (!joinCode) return;
    try {
        await copyText(joinCode);
        showMessage("Join code copied.", "success");
    } catch (error) {
        showMessage("Unable to copy the join code.", "error");
    }
}

async function shareTour(title, tourId, joinCode) {
    const shareText = `${title} - join this tour with join code ${joinCode}.`;
    try {
        if (navigator.share) {
            await navigator.share({ title, text: shareText });
        } else {
            await copyText(shareText);
            showMessage("Tour details copied. You can share them with your members.", "success");
        }
    } catch (error) {
        if (error.name !== "AbortError") {
            showMessage("Unable to share the tour details.", "error");
        }
    }
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

    if (!copied) {
        throw new Error("Copy failed");
    }
}


function formatCurrency(amount) {

    const number = Number(amount || 0);

    return new Intl.NumberFormat(
        "en-PK",
        {
            style: "currency",
            currency: "PKR",
            minimumFractionDigits: 2,
        }
    ).format(number);

}


function formatDate(dateString) {

    if (!dateString) {

        return "-";

    }

    const date = new Date(
        `${dateString}T00:00:00`
    );

    return new Intl.DateTimeFormat(
        "en-US",
        {
            year: "numeric",
            month: "short",
            day: "numeric",
        }
    ).format(date);

}


function getStatusBadge(status) {

    const statusMap = {

        planned: {
            label: "Planned",
            classes: "bg-blue-100 text-blue-700"
        },

        ongoing: {
            label: "Ongoing",
            classes: "bg-yellow-100 text-yellow-700"
        },

        completed: {
            label: "Completed",
            classes: "bg-green-100 text-green-700"
        },

        cancelled: {
            label: "Cancelled",
            classes: "bg-red-100 text-red-700"
        }

    };


    const statusData = statusMap[status] || {

        label: status || "Unknown",
        classes: "bg-gray-100 text-gray-700"

    };


    return `

        <span
            class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${statusData.classes}">

            ${escapeHtml(statusData.label)}

        </span>

    `;

}


function escapeHtml(value) {

    const text = String(value ?? "");

    const div = document.createElement("div");

    div.textContent = text;

    return div.innerHTML;

}


async function loadTours() {

    showLoading();

    const params = new URLSearchParams();

    params.set("page", currentPage);
    

    if (currentSearch.trim() !== "") {

        params.set(
            "search",
            currentSearch.trim()
        );

    }

    let apiUrl = `/api/tours/?${params.toString()}`;

    // if (currentSearch.trim() !== "") {

    //     apiUrl += `?search=${encodeURIComponent(
    //         currentSearch.trim()
    //     )}`;
        

    // }
    
    try {

        const response = await authenticatedFetch(apiUrl, {

            method: "GET",

        });


        if (response.status === 401) {

            handleUnauthorized();

            return;

        }


        if (!response.ok) {

            throw new Error(
                "Unable to load tours."
            );

        }


        const data = await response.json();

        console.log("Tour API Response:", data);

        totalTours = data.count;

        if (data.count === 0) {

            showEmptyState();

            updatePagination(null, null);

            return;

        }


        showTableContainer();


        renderTours(data.results);

        updatePagination(
            data.next,
            data.previous
        );

        

    }

    catch (error) {

        

        console.error(
            "Error loading tours:",
            error
        );

        showError(
            "Unable to load tours. Please try again."
        );

    }

}





function setupPagination() {

    const previousPageBtn = document.getElementById(
        "previousPageBtn"
    );

    const nextPageBtn = document.getElementById(
        "nextPageBtn"
    );


    previousPageBtn.addEventListener(
        "click",
        function () {

            if (currentPage > 1) {

                currentPage--;

                loadTours();

            }

        }
    );


    nextPageBtn.addEventListener(
        "click",
        function () {

            const totalPages = Math.ceil(
                totalTours / toursPerPage
            );


            if (currentPage < totalPages) {

                currentPage++;

                loadTours();

            }

        }
    );

}


function updatePagination(nextUrl, previousUrl) {

    const paginationContainer = document.getElementById(
        "paginationContainer"
    );

    const previousPageBtn = document.getElementById(
        "previousPageBtn"
    );

    const nextPageBtn = document.getElementById(
        "nextPageBtn"
    );

    const currentPageInfo = document.getElementById(
        "currentPageInfo"
    );

    const paginationInfo = document.getElementById(
        "paginationInfo"
    );


    if (totalTours === 0) {

        paginationContainer.classList.add("hidden");

        return;

    }


    paginationContainer.classList.remove("hidden");


    const totalPages = Math.ceil(
        totalTours / toursPerPage
    );


    const startItem =
        ((currentPage - 1) * toursPerPage) + 1;


    const endItem = Math.min(
        currentPage * toursPerPage,
        totalTours
    );


    paginationInfo.textContent =
        `Showing ${startItem}–${endItem} of ${totalTours} tours`;


    currentPageInfo.textContent =
        `Page ${currentPage} of ${totalPages}`;


    previousPageBtn.disabled = !previousUrl;

    nextPageBtn.disabled = !nextUrl;

}



function showLoading() {

    document
        .getElementById("loadingState")
        .classList
        .remove("hidden");


    document
        .getElementById("emptyState")
        .classList
        .add("hidden");


    document
        .getElementById("tableContainer")
        .classList
        .add("hidden");

    document
        .getElementById("paginationContainer")
        .classList
        .add("hidden");


    document
        .getElementById("messageArea")
        .innerHTML = "";

}


function showEmptyState() {

    document
        .getElementById("loadingState")
        .classList
        .add("hidden");


    document
        .getElementById("emptyState")
        .classList
        .remove("hidden");


    document
        .getElementById("tableContainer")
        .classList
        .add("hidden");

    document
    .getElementById("paginationContainer")
    .classList
    .add("hidden");


    const title = document.getElementById(
        "emptyStateTitle"
    );

    const message = document.getElementById(
        "emptyStateMessage"
    );

    const button = document.getElementById(
        "emptyStateButton"
    );


    if (currentSearch.trim() !== "") {

        title.textContent = "No Matching Tours";

        message.textContent =
            `We couldn't find any tours matching "${currentSearch}".`;

        button.classList.add("hidden");

    }

    else {

        title.textContent = "No Tours Found";

        message.textContent =
            "You haven't created any tours yet.";

        button.classList.remove("hidden");

    }

}

function showTableContainer() {

    document
        .getElementById("loadingState")
        .classList
        .add("hidden");


    document
        .getElementById("emptyState")
        .classList
        .add("hidden");


    document
        .getElementById("tableContainer")
        .classList
        .remove("hidden");

}


function showMessage(message, type) {

    const messageArea = document.getElementById(
        "messageArea"
    );


    const styles = {

        success:
            "bg-green-100 border border-green-300 text-green-700",

        error:
            "bg-red-100 border border-red-300 text-red-700"

    };


    messageArea.innerHTML = `

        <div class="${styles[type] || styles.error} px-5 py-4 rounded-lg">

            ${escapeHtml(message)}

        </div>

    `;

}


function handleUnauthorized() {

    localStorage.removeItem("access_token");

    localStorage.removeItem("refresh_token");


    window.location.href = "/login/";

}


function showError(message) {

    document
        .getElementById("loadingState")
        .classList
        .add("hidden");


    document
        .getElementById("emptyState")
        .classList
        .add("hidden");


    document
        .getElementById("tableContainer")
        .classList
        .add("hidden");


    document
        .getElementById("messageArea")
        .innerHTML = `

            <div class="bg-red-100 border border-red-300 text-red-700 px-5 py-4 rounded-lg">

                ${message}

            </div>

        `;

}
