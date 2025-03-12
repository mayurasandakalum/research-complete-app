// Initialize datepickers
$(function () {
  $(".datepicker").datepicker({
    dateFormat: "yy-mm-dd",
    changeMonth: true,
    changeYear: true,
    yearRange: "-20:+0", // Allow selecting dates from 20 years ago to today
  });
});

// Fetch and display app status
function updateStatus() {
  fetch("/api/status")
    .then((response) => response.json())
    .then((data) => {
      let statusHtml = "<ul>";
      for (const [app, status] of Object.entries(data)) {
        statusHtml += `<li>${app}: <span style="color: ${
          status === "running" ? "green" : "red"
        }">${status}</span></li>`;
      }
      statusHtml += "</ul>";
      document.getElementById("status").innerHTML = statusHtml;
    })
    .catch((error) => {
      document.getElementById("status").innerHTML =
        "Error checking system status";
    });
}

// Check status on page load and every 10 seconds
updateStatus();
setInterval(updateStatus, 10000);

// Navigation functionality
document.addEventListener("DOMContentLoaded", function () {
  const navLinks = document.querySelectorAll(".nav-link");
  const sections = document.querySelectorAll(".dashboard-section");

  navLinks.forEach((link) => {
    link.addEventListener("click", function (e) {
      // Don't prevent default for external links (those with href starting with http or containing url_for)
      if (!this.getAttribute("href").startsWith("#")) {
        return; // Let the browser handle the navigation
      }

      e.preventDefault();

      // Remove active class from all links and sections
      navLinks.forEach((l) => l.classList.remove("active"));
      sections.forEach((s) => s.classList.remove("active"));

      // Add active class to clicked link
      this.classList.add("active");

      // Show the corresponding section
      const targetId = this.getAttribute("href").substring(1);
      document.getElementById(targetId).classList.add("active");
    });
  });

  // Modal functionality
  const modal = document.getElementById("editStudentModal");
  const closeBtn = document.querySelector(".close-btn");
  const editForm = document.getElementById("editStudentForm");

  // Close the modal when clicking the close button
  closeBtn.addEventListener("click", function () {
    modal.style.display = "none";
  });

  // Close the modal when clicking outside of it
  window.addEventListener("click", function (event) {
    if (event.target === modal) {
      modal.style.display = "none";
    }
  });

  // Handle the edit form submission
  editForm.addEventListener("submit", function (e) {
    e.preventDefault();

    const studentId = document.getElementById("edit_student_id").value;
    const studentName = document.getElementById("edit_student_name").value;
    const studentEmail = document.getElementById("edit_student_email").value;
    const studentGender = document.getElementById("edit_student_gender").value;
    const studentBirthday = document.getElementById(
      "edit_student_birthday"
    ).value;
    const studentGrade = document.getElementById("edit_student_grade").value;

    // Create FormData object and append all fields, even if empty
    const formData = new FormData();
    formData.append("student_name", studentName);
    formData.append("student_email", studentEmail);
    formData.append("student_gender", studentGender);
    formData.append("student_birthday", studentBirthday);
    formData.append("student_grade", studentGrade);

    // Debug - optional, remove in production
    console.log("Updating student with:");
    console.log("Gender:", studentGender);
    console.log("Birthday:", studentBirthday);
    console.log("Grade:", studentGrade);

    fetch(`/edit_student/${studentId}`, {
      method: "POST",
      body: formData,
    })
      .then((response) => {
        if (response.ok) {
          // Reload the page to show updated data
          window.location.reload();
        } else {
          return response.json().then((data) => {
            throw new Error(data.error || "Failed to update student");
          });
        }
      })
      .catch((error) => {
        alert("Error: " + error.message);
        console.error("Error:", error);
      });
  });
});

// Function to open the edit modal
function openEditModal(id, name, email, gender, birthday, grade) {
  const modal = document.getElementById("editStudentModal");
  document.getElementById("edit_student_id").value = id;
  document.getElementById("edit_student_name").value = name;
  document.getElementById("edit_student_email").value = email;

  // Fix handling of gender, birthday and grade fields
  const genderField = document.getElementById("edit_student_gender");
  genderField.value = gender || ""; // Set empty string if undefined

  const birthdayField = document.getElementById("edit_student_birthday");
  birthdayField.value = birthday || ""; // Set empty string if undefined

  const gradeField = document.getElementById("edit_student_grade");
  gradeField.value = grade || ""; // Set empty string if undefined

  // Refresh/initialize the datepicker
  if ($(birthdayField).hasClass("hasDatepicker")) {
    $(birthdayField).datepicker("setDate", birthday);
  }

  modal.style.display = "block";
}
