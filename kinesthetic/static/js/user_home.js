document.addEventListener("DOMContentLoaded", function () {
  // Add highlighting effects for second quiz section
  const quizButton = document.querySelector(
    '.btn-warning[href*="weakest_subject_quiz"]'
  );
  if (quizButton) {
    quizButton.addEventListener("mouseenter", function () {
      this.innerHTML =
        '<i class="fa fa-graduation-cap"></i> ප්‍රශ්න 5 සමඟ ආරම්භ කරන්න';
    });

    quizButton.addEventListener("mouseleave", function () {
      this.innerHTML =
        '<i class="fa fa-graduation-cap"></i> ප්‍රශ්නාවලිය ආරම්භ කරන්න';
    });
  }

  // Add badge showing '5 questions' in the comparison card if it exists
  const comparisonCard = document.querySelector(".comparison-stats");
  if (comparisonCard) {
    const secondQuizTitle = comparisonCard.querySelector(
      ".col-md-6:last-child .card-body h5"
    );
    if (secondQuizTitle) {
      secondQuizTitle.innerHTML +=
        ' <span class="badge badge-pill badge-info">ප්‍රශ්න 5</span>';
    }
  }
});
