/* LOGOUT FUNCTION */
function logout(){
    localStorage.removeItem("loggedIn");
    window.location.href = "/";
}

/* HOW IT WORKS MODAL */
function openHow(){
    const modal = document.getElementById("howModal");
    if(modal) modal.classList.remove("hidden");
}

function closeHow(){
    const modal = document.getElementById("howModal");
    if(modal) modal.classList.add("hidden");
}

/* FORM VALIDATION */
function validateForm(){
    const location = document.querySelector("input[name='location']");
    if(location && location.value.trim() === ""){
        alert("Please enter location or use current location");
        return false;
    }
    return true;
}

/* ================= LOCATION FEATURE ================= */

/* Get user location */
function getLocation(){
    if(navigator.geolocation){
        navigator.geolocation.getCurrentPosition(sendLocation, showError);
    } else {
        alert("Geolocation not supported");
    }
}

/* Send location to backend */
function sendLocation(position){

    const lat = position.coords.latitude;
    const lon = position.coords.longitude;

    console.log("Latitude:", lat, "Longitude:", lon); // debug

    fetch("/nearby",{
        method:"POST",
        headers:{
            "Content-Type":"application/json"
        },
        body:JSON.stringify({
            latitude:lat,
            longitude:lon
        })
    })
    .then(response => response.json())
    .then(data => {
        if(data.status === "success"){
            window.location.href = "/results_from_location";
        } else {
            alert("Failed to fetch restaurants");
        }
    })
    .catch(error => {
        console.error("Error:", error);
        alert("Server error");
    });
}

/* Handle errors */
function showError(){
    alert("Please allow location access");
}