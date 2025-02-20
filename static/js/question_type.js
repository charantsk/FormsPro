  document.addEventListener("DOMContentLoaded", function() {
  const questionTypeButtons = document.querySelectorAll(".question-type-btn");

  questionTypeButtons.forEach(button => {
    button.addEventListener("click", function() {
      // Remove active class from all buttons
      questionTypeButtons.forEach(btn => btn.classList.remove("active"));
      
      // Add active class to the selected button
      this.classList.add("active");
      
      // Set selected type to hidden input
      document.getElementById("question-type").value = this.dataset.type;
    });
  });
});
