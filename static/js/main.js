function showForm(userType) {
    const formTitle = document.getElementById("form-title");
    if (userType === "candidate") {
        formTitle.innerHTML = "Candidate Options";
        document.getElementById("login-btn").href = "/login_signup?type=candidate";
        document.getElementById("signup-btn").href = "/signup?type=candidate";
    } else {
        formTitle.innerHTML = "Recruiter Options";
        document.getElementById("login-btn").href = "/login_signup?type=recruiter";
        document.getElementById("signup-btn").href = "/signup?type=recruiter";
    }
    document.getElementById("floating-form").style.display = "block";
}

function closeForm() {
    document.getElementById("floating-form").style.display = "none";
}
