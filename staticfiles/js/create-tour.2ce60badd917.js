const imageInput = document.getElementById("image");

const imagePreview = document.getElementById("imagePreview");
const imagePreviewContainer = document.getElementById("imagePreviewContainer");

imageInput.addEventListener("change", function () {
    const file = this.files[0];

    if (!file) {
        imagePreviewContainer.classList.add(
            "hidden"
        );
        imagePreview.src = "";
        return;
    }

    if (!file.type.startsWith("image/")) {

        alert("Please select an image file.");
        this.value = "";
        return;
    }

    const imageUrl = URL.createObjectURL(file);
    imagePreview.src = imageUrl;
    imagePreviewContainer.classList.remove("hidden");
});



document
    .getElementById("tourform")
    .addEventListener("submit",createtour);

async function createtour(e) {
    e.preventDefault();

    const token = localStorage.getItem("access_token");

    if(!token){
        window.location.href = "/login/";
        return;
    }

    const payload = {
        title: document.getElementById("title").value.trim(),

        destination: document.getElementById("destination").value.trim(),

        description: document.getElementById("description").value.trim(),

        budget: document.getElementById("budget").value,

        start_date: document.getElementById("startDate").value,

        end_date: document.getElementById("endDate").value,

        status: document.getElementById("status").value,

    };

const formData = new FormData();
formData.append(
    "title",
    payload.title
);

formData.append(
    "destination",
    payload.destination
);

formData.append(
    "description",
    payload.description
);

formData.append(
    "budget",
    payload.budget
);

formData.append(
    "start_date",
    payload.start_date
);
    
formData.append(
    "end_date",
    payload.end_date
);
formData.append(
    "status",
    payload.status
);


const imageFile = imageInput.files[0];
if (imageFile) {
    formData.append("image", imageFile);
} 



    const response = await fetch("/api/tours/create/",{
        method: "POST",

       headers: {
    "Authorization": `Bearer ${token}`,
    // "Content-Type": "application/json",
    },

        body: formData
    });
    const data =await response.json();
    const message= document.getElementById("message");

    if(response.ok){
        message.innerHTML=`<div class="bg-green-100 border-green-400 text-green-700 px-4 py-3 rounded">Tour created successfully.</div>`;
        setTimeout(() =>{
        window.location.href ="/tours/";
    },1200);
    } else{
        message.innerHTML=`<div class="bg-red-100 border-red-400 text-red-700 px-4 py-3 rounded">${JSON.stringify(data)}</div>`;
    }
}
